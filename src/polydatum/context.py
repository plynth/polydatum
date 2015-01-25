import json
from werkzeug.local import LocalStack
import sys

# context locals
from .errors import MiddlewareSetupException, ErrorsOnClose

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
        return json.dumps(dict(self.items()), indent=2)

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
        self._middleware = {}
        self._middleware_generators = None

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
                generator.next()
            except StopIteration:
                # Middleware didn't want to setup, but did not
                # raise an exception. Why not?
                raise MiddlewareSetupException('Middleware %s did not yield on setup.' % middleware)

    def __enter__(self):
        """
        Open the context and put it on the stack
        """
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

        return self

    def __exit__(self, exc_type=None, exc_value=None, traceback=None):
        """
        Close all open resources, middleware and
        remove context from stack

        If a Resource raises an exception, it is collected and all
        other Resource will still close. The exceptions then will be
        raised as an ``ErrorsOnClose``.

        TODO Should Middleware propagate exceptions or ignore?
        """
        if exc_type is not None and exc_value is None:
            # Need to force instantiation so we can reliably
            # tell if we get the same exception back
            exc_value = exc_type()

        try:
            self._teardown_hook(exc_value)
        finally:
            try:
                exc_infos = []
                # Tear down all the middleware
                for __, generator in reversed(self._middleware_generators):
                    try:
                        self._exit_resource(generator, exc_type, exc_value, traceback)
                    except:
                        exc_type, exc, tb = sys.exc_info()
                        exc_infos.append((exc_type, exc, tb))

                # Tear down all the resources
                for resource_generator in self._resource_generators.values():
                    try:
                        self._exit_resource(resource_generator, exc_type, exc_value, traceback)
                    except:
                        exc_type, exc, tb = sys.exc_info()
                        exc_infos.append((exc_type, exc, tb))

                if exc_infos:
                    raise ErrorsOnClose('Got multiple errors while closing resources', exc_infos)
            finally:
                try:
                    self._final_hook(exc_value)
                finally:
                    self.data_manager.ctx_stack.pop()

    def _exit_resource(self, resource, type, value, traceback):
        """
        Teardown a Resource or Middleware.
        """
        if type is None:
            try:
                resource.next()
            except StopIteration:
                # Resource closed as expected
                return
            else:
                raise RuntimeError('Resource generator yielded more than once.')
        else:
            try:
                resource.throw(type, value, traceback)
                raise RuntimeError('Resource generator did not close after throw()')
            except StopIteration as exc:
                # Suppress the exception *unless* it's the same exception that
                # was passed to throw().  This prevents a StopIteration
                # raised inside the "with" statement from being suppressed
                return exc is not value
            except Exception as e:
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
        if name not in self._resources:
            resource = self.data_manager.get_resource(name)
            if resource:
                # Call the resource to get a resource generator
                self._resource_generators[name] = resource(self)

                # Iterate the generator to open the resource
                self._resources[name] = self._resource_generators[name].next()
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