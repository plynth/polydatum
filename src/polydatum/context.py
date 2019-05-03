from __future__ import absolute_import
import json
from werkzeug.local import LocalStack
import sys
from .errors import MiddlewareSetupException, ResourceSetupException
import six

# Deprecated (0.8.4) in preference of accessing stack on DataManager
_ctx_stack = LocalStack()

# Deprecated (0.8.4).
# The current DataAccessContext for the active thread/context
_ctx = _ctx_stack()

# Deprecated (0.8.4) in preference of only accessing the context
# through DAL/Services
current_context = _ctx


def get_active_context():
    """
    Safely checks if there's a context active
    and returns it

    Deprecated 0.8.4 in favor of
    DataManager.get_active_context()
    """
    if _ctx_stack.top:
        return _ctx_stack.top


class Meta(object):
    """
    Read only meta data. Keys are accessible as attributes.
    Keys can not be changed once initialized.
    """
    _values = None

    def __init__(self, opts=None):
        object.__setattr__(self, '_values', {})
        if opts:
            for k, v in opts.items():
                self._values[k] = v

    def __setattr__(self, key, value):
        raise AttributeError('Meta values can not be changed.')

    def __getattr__(self, key):
        """
        Returns meta value for key. Returns ``None`` if the
        key has not been set.
        """
        return self.get(key)

    def get(self, key, default=None):
        return self._values.get(key, default)

    def require(self, key):
        """
        Raises an exception if value for ``key`` is empty.
        """
        value = self.get(key)
        if not value:
            raise ValueError('"{}" is empty.'.format(key))
        return value

    def items(self):
        for k, v in self._values.items():
            yield k, v

    def __str__(self):
        return json.dumps(dict(list(self.items())), indent=2)

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self)


class DataAccessContext(object):
    """
    Lifecycle:

    - Add to context stack
    - Setup Middleware in order
    - Process requests, Resources are created on demand
    - Tear down Middleware in reverse order
    - Tear down created Resources in random order
    - Remove from context stack
    """
    def __init__(self, data_manager, meta=None):
        """
        :param data_manager: DataManager for the context
        :param meta: dict-like Read only meta data
        """
        self.data_manager = data_manager
        self.dal = self.data_manager.get_dal()
        self.meta = meta if isinstance(meta, Meta) else Meta(meta)
        self._resources = {}
        self._resource_generators = {}
        self._middleware_generators = None
        self._resource_exit_errors = []
        self._state = 'created'

    def get_resource_exit_errors(self):
        """
        Returns a list of errors that occurred during resource exit. In
        general, Resources should handler their own errors and raise none,
        however nothing prevents them from doing so. Errors are collected
        and available here for handling/logging.

        :returns: List of ``sys.exc_info()`` for each exception:
            [(exc_type, exc_value, traceback)]
        """
        return self._resource_exit_errors

    def _setup(self):
        """
        Setup the context. Should only be called by
        __enter__'ing the context.
        """
        self.data_manager.ctx_stack.push(self)
        self._setup_hook()

        middleware = self.data_manager.get_middleware(self)

        # Create each middleware generator
        # This just calls each middleware and passes it the current context.
        # The middleware should then yield once.
        self._middleware_generators = [
            (m, m(self)) for m in middleware
        ]

        for middleware, generator in self._middleware_generators:
            try:
                next(generator)
            except StopIteration:
                # Middleware didn't want to setup, but did not
                # raise an exception. Why not?
                raise MiddlewareSetupException('Middleware %s did not yield on setup.' % middleware)

    def __enter__(self):
        """
        Open the context and put it on the stack
        """
        if self._state != 'created':
            raise RuntimeError('Context may only be used once')

        self._state = 'setup'
        try:
            self._setup()
        except:
            # We still need to run __exit__ on setup exception
            # so that resources can clean up
            if self.__exit__(*sys.exc_info()):
                # Swallow exception if __exit__ returns a True value
                pass
            else:
                raise

        self._state = 'active'

        return self

    def __exit__(self, exc_type=None, exc_value=None, traceback=None):
        """
        Close all open resources, middleware and
        remove context from stack

        In-context exceptions (exceptions raised between ``__enter__``
        and ``__exit__``) are propagated to Middleware, Resources, and
        eventually raised outside the ``DataAccessContext``. Resources
        are created in-context so if a Resource raises an exception
        during setup, it treated the same as all in-context exceptions.

        Middleware may suppress or replace the in-context exception. If
        there is an unhandled exception raised in-context or by middleware
        it is guaranteed to be raised outside the ``DataAccessContext``.

        If a Resource raises an exception, it is collected and all
        other Resource will still close. Resource exit exceptions do not
        propagate. The Resource will only see the in-context/middleware
        exception. To access Resource exit exceptions, use
        ``DataAccessContext.get_resource_exit_errors()``.
        """
        assert self._state in ('active', 'setup'), 'Context must be active to exit it'
        self._state = 'exiting'

        if exc_type is not None and exc_value is None:
            # Need to force instantiation so we can reliably
            # tell if we get the same exception back
            exc_value = exc_type()

        # Tear down all the middleware. The original in-context exception is
        # first passed to the middleware, but if middleware raises a
        # different exception it is passed up the middleware chain and
        # replaces the current exception
        generators, self._middleware_generators = self._middleware_generators, None
        while generators:
            __, generator = generators.pop()
            try:
                if self._exit(generator, exc_type, exc_value, traceback):
                    # Exception was suppressed
                    exc_type, exc_value, traceback = (None, None, None)
            except:
                # New exception raised, use it instead
                exc_type, exc_value, traceback = sys.exc_info()
                exc_value = exc_value or exc_type()

        try:
            self._teardown_hook(exc_value)
        except:
            # Teardown hook exceptions are trapped and
            # stored as a resource exit error.
            self._resource_exit_errors.append(sys.exc_info())
        finally:
            # Tear down all the resources and don't
            # propagate resource exceptions to other resources.
            # Resource exit exceptions are not raised, instead they
            # are collected and available with ``get_resource_exit_errors()``.
            resources, self._resource_generators = self._resource_generators, None
            while resources:
                __, resource_generator = resources.popitem()

                try:
                    self._exit(resource_generator, exc_type, exc_value, traceback)
                except:
                    self._resource_exit_errors.append(sys.exc_info())

            try:
                if exc_type:
                    # An in-context or middleware exception
                    # occurred and will be raised outside the context
                    six.reraise(exc_type, exc_value, traceback)

            finally:
                try:
                    self._final_hook(exc_value)
                finally:
                    self.data_manager.ctx_stack.pop()
                    self._state = 'exited'

    def _exit(self, obj, type, value, traceback):
        """
        Teardown a Resource or Middleware.
        """
        if type is None:
            # No in-context exception occurred
            try:
                next(obj)
            except StopIteration:
                # Resource closed as expected
                return
            else:
                raise RuntimeError('{} yielded more than once.'.format(obj))
        else:
            # In-context exception occurred
            try:
                obj.throw(type, value, traceback)
                raise RuntimeError('{} did not close after throw()'.format(obj))
            except StopIteration as exc:
                # Suppress the exception *unless* it's the same exception that
                # was passed to throw().  This prevents a StopIteration
                # raised inside the "with" statement from being suppressed
                return exc is not value
            except:
                # only re-raise if it's *not* the exception that was
                # passed to throw(), because __exit__() must not raise
                # an exception unless __exit__() itself failed.  But
                # resource.throw() will raise the exception to signal propagation,
                # so this fixes the impedance mismatch between the throw() protocol
                # and the __exit__() protocol.
                #
                # Middleware or Resources that throw exceptions before yielding
                # will just rethrow the same exception here which is expected. They
                # won't have a chance to do anything about the exception though which
                # seems OK since they never got to the point of being ready anyway.
                if sys.exc_info()[1] is not value:
                    raise

    def __getattr__(self, name):
        """
        Gets a Resource from the DataManager and initializes
        it for the request.
        """
        if self._state not in ('active', 'setup', 'exiting'):
            raise RuntimeError('Resources can only be used during an active context')

        if name not in self._resources:
            if self._state not in ('active', 'setup'):
                raise RuntimeError('Resources can only be created during an active context')

            resource = self.data_manager.get_resource(name)
            if resource:
                # Call the resource to get a resource generator
                self._resource_generators[name] = resource(self)

                # Iterate the generator to open the resource
                try:
                    self._resources[name] = next(self._resource_generators[name])
                except StopIteration:
                    # Resource didn't want to setup, but did not
                    # raise an exception. Why not?
                    raise ResourceSetupException('Resource {} did not yield on setup.'.format(resource))
            else:
                raise AttributeError('No resource named "{}" for context.'.format(name))

        return self._resources[name]

    def __contains__(self, name):
        """
        Returns true if the ``name`` Resource has been initialized.
        """
        return name in self._resources

    def _teardown_hook(self, exception):
        """
        Handle any thing that needs to happen before teardown
        of the context

        :param exception: An exception if there was an uncaught one during the
            context lifetime.
        """
        pass

    def _setup_hook(self):
        """
        Handle any thing that needs to happen before start of the context.
        """
        pass

    def _final_hook(self, exception):
        """
        Handle any thing that needs to happen at the end of the context.
        """
        pass