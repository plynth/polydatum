from functools import partial
from werkzeug.local import LocalStack, LocalProxy
import sys

# context locals
_ctx_stack = LocalStack()

#: The current DataAccessContext for the active thread/context
current_context = _ctx_stack()

class ErrorsOnClose(Exception):
    def __init__(self, message, exceptions):
        super(Exception, self).__init__(message)
        self.exceptions = exceptions    


class DataAccessContext(object):
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self._resources = {}
        self._resource_generators = {}

    def __enter__(self):        
        """
        Open the context and put it on the stack
        """
        _ctx_stack.push(self)
        return self

    def __exit__(self, exc_type=None, exc_value=None, traceback=None):
        """
        Close all open resources and 
        remove context from stack
        """

        if exc_type is not None and exc_value is None:
            # Need to force instantiation so we can reliably
            # tell if we get the same exception back
            exc_value = type()        
        
        try:
            exc_infos = []
            for resource_generator in self._resource_generators.values():
                try:
                    self._exit_resource(resource_generator, exc_type, exc_value, traceback)
                except:
                    exc_type, exc, tb = sys.exc_info()
                    exc_infos.append((exc_type, exc, tb))

            if exc_infos:
                if len(exc_infos) == 1:
                    raise exc_infos[0][0], exc_infos[0][1], exc_infos[0][2]

                raise ErrorsOnClose('Got multiple errors while closing resources', exc_infos)
        finally:
            _ctx_stack.pop()

    def _exit_resource(self, resource, type, value, traceback):
        if type is None:
            try:
                resource.next()
            except StopIteration:
                return
            else:
                raise RuntimeError('Resource generator did not close')
        else:
            try:
                resource.throw(type, value, traceback)
                raise RuntimeError('Resource generator did not close after throw()')
            except StopIteration as exc:
                # Suppress the exception *unless* it's the same exception that
                # was passed to throw().  This prevents a StopIteration
                # raised inside the "with" statement from being suppressed
                return exc is not value
            except:
                # only re-raise if it's *not* the exception that was
                # passed to throw(), because __exit__() must not raise
                # an exception unless __exit__() itself failed.  But throw()
                # has to raise the exception to signal propagation, so this
                # fixes the impedance mismatch between the throw() protocol
                # and the __exit__() protocol.
                #
                if sys.exc_info()[1] is not value:
                    raise

    def __getattr__(self, name):
        """
        Gets a Resource from the DataManager and initializes
        it for the request.
        """
        if name not in self._resources:
            resource = self.data_manager.get_resource(name)
            # Call the resource to get a resource generator
            self._resource_generators[name] = resource(self)

            # Iterate the generator to open the resource
            self._resources[name] = self._resource_generators[name].next()

        return self._resources[name]        
