from typing import Any, Callable, Dict, Optional, Tuple

from polydatum.context import DataAccessContext
from polydatum.services import Service


class PathSegment:
    """
    This structure represents a segment of an attribute path.

    For example, in this code:

        dal.my_service.sub_service.other_service.method()

    For the `dal` object, the entire attribute path would be:

        my_service.sub_service.other_service.method

    Which may be made up of PathSegments like:

        PathSegment(name="my_service"), PathSegment(name="sub_service"), etc.
    """

    name = None

    # A collection of meta properties.
    # Example:
    #   meta = {
    #       "enabled": True
    #   }
    meta = None

    def __init__(self, name: str, **meta):
        self.name = name
        self.meta = meta

    def __eq__(self, other):
        return (
            isinstance(other, PathSegment)
            and self.name == other.name
            and self.meta == other.meta
        )


class DalCommandRequest:
    """
    Mutable request state. Middleware can modify this.
    """

    def __init__(
        self,
        ctx: DataAccessContext,
        path: Tuple[PathSegment, ...],
        args: Tuple[Any, ...],
        kwargs: Dict,
    ):
        self.ctx = ctx
        self.path = path
        self.args = args
        self.kwargs = kwargs
        self.dal_method = None  # Not resolved yet


class DalMethodError(Exception):
    """
    This class defines a DalMethodError that is raised
    when a service/method cannot be resolved by the
    DalMethodResolverMiddleware
    """

    def __init__(self, path: Optional[Tuple[PathSegment]] = None):
        self.path = path
        super().__init__(f'Invalid dal method: {".".join([p.name for p in self.path])}')


class DalCommand:
    """
    Expresses a request for an operation to be performed.

    It does not directly execute the operation. It passes the requested command path
    and parameters to the `DataAccessLayer` (DAL). The DAL turns the command into
    a `DalCommandRequest` and binds it to the current `DataAccessContext`. The
    DAL runs the `DalCommandRequest` through middleware which will resolve the
    command to the specific `Service` that can perform the operation described by the
    command. It then executes the operation on the `Service` within the bound context.

    A simplified illustration of the call chain:

    DalCommand ->
        DataAccessLayer ->
            DalCommandRequest(context, command_path, **command_parameters) ->
                [Middleware, ...] ->
                    Service
    Middleware may prevent commands from being called by raising exceptions.

    Since a `DalCommand` is not bound to a `DataAccessContext`, it can be re-used and
    passed to queues, other functions, or as an event handler to be performed at a
    later time.
    """

    # Defining type here allows subclasses to easily provide another class
    PathSegment = PathSegment

    def __init__(self, handler: Callable, path: Tuple[PathSegment, ...]):
        """
        Args:
            handler (Callable): A callable that handles calling the underlying
                attribute by wrapping it so that method middleware can run before
                and after calling a method
            path (Tuple[PathSegment, ...]): A tuple of PathSegments representing
                the current attribute path that has been requested.
        """
        self._handler = handler
        self.path = path

    def __getattr__(self, name: str) -> "DalCommand":
        return self.__class__(self._handler, self.path + (self.PathSegment(name=name),))

    def __call__(self, *args, **kwargs):
        return self._handler(self.path, *args, **kwargs)

    def __str__(self):
        return ".".join([p.name for p in self.path])


def dal_resolver(ctx, request_path):
    """
    This function resolves a dal method call to its underlying
    service
    """
    service_or_method = None
    for (path, service_or_method) in resolve(ctx, request_path):
        if not (
            service_or_method and isinstance(service_or_method, (Callable, Service))
        ):
            raise DalMethodError(path=path)
    if not service_or_method:
        raise DalMethodError(request_path)
    return service_or_method


def resolve(ctx: DataAccessContext, path: Tuple[PathSegment]):
    """
    A generator that returns a list of path segments traversed
    during resolving the dal attribute and the method to call, if any.
    """
    service_or_method = ctx.dal._services  # noqa
    paths = list(path)
    location = []

    while paths:
        path_segment = paths.pop(0)
        location.append(path_segment)
        # Third time through, service_or_method might be `None`, but we want
        # to continue walking the path. Everything after the first missing
        # service/method will be `(location, None)`.
        if service_or_method:

            # This if condition is handling the case of the first loop here.
            # we cannot use attribute access on the dal directly because of how
            # attribute access is deferred with DalCommandRequest objects.
            if isinstance(service_or_method, dict):

                # If the code being resolved has typo'd a service name, this
                # could be returning something that is not a service.
                service_or_method = service_or_method.get(path_segment.name)
            else:
                # second time through (and beyond), service or method is a real
                # service or method, and we do not need to use a special case for
                # finding the first service.
                try:
                    service_or_method = getattr(service_or_method, path_segment.name)
                except AttributeError:
                    service_or_method = None

            yield tuple(location), service_or_method
        else:
            yield tuple(location), None


def dal_method_resolver_middleware(request: DalCommandRequest, handler: Callable):
    """
    A Method Middleware that resolves deferred dal attribute access to
    underlying services/methods that has to be called
    Args:
         request: Input from caller
         handler: Downstream middleware or actual DAL method handler
    """
    request.dal_method = dal_resolver(request.ctx, request.path)
    return handler(request)


def handle_dal_method(request: DalCommandRequest):
    """
    The default method middleware handler for a DalCommand

    Args:
        request (DalCommandRequest): The method request context.

    Returns: Mixed
    """
    if not request.dal_method:
        raise DalMethodError(request.path)
    return request.dal_method(*request.args, **request.kwargs)
