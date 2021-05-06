import typing
from dataclasses import dataclass
from functools import partial, update_wrapper


@dataclass
class PathSegment:
    name: str
    meta: dict

    def __init__(self, name, **meta):
        self.name = name
        self.meta = meta


def requires_features(features):
    """
    @requires_features(features.pws.ios)
    def monkey():
         pass
         # if called, by gorrilla() both pws.ios and banana will be guarded
         # if called, by itself, only pws.ios will be guarded

    @requires_features(features.banana)
    def gorrilla():
         monkey()

         # Calling this should be fine, as long as `features.gateways`
         # was guarded somewhere in the guard stack
         dal.gateways.thing()

    @requires_features(features.gateway)
    def my_other_method():
        gorilla()

    """
    # inside decorator
    def _requires_features(func):
        def _inner(*args, **kwargs):
            with guard_stack.current().guarded(features):
                # push required features onto the guarded stack, the features are
                # now "guarded"
                return func(*args, **kwargs)
            # pop the last guarded features off the stack
        return _inner
    return _requires_features



class DalMethodRequestor:
    PathSegment = PathSegment

    def __init__(self, handler: Callable, path: typing.Tuple[PathSegment]):
        self._handler = handler
        self._path = path

    def __getattr__(self, name: str):
        return self.__class__(self._handler, self._path + (self.PathSegment(name=name),))

    def __call__(self, *args, **kwargs):
        return self._handler(self._path, *args, **kwargs)


def optional(requestor: DalMethodRequestor):
    """
    >>> optional(dal.foo).baz
    DalMethodRequestor(path=(PathSegment("foo", optional=True), PathSegment("baz")))
    >>> optional(dal.foo).baz()
    >>> foo_shortcut = dal.foo
    >>> assert isinstance(foo_shortcut, DalMethodRequestor)
    >>> optional_foo_shortcut = optional(foo_shortcut)
    >>> assert isinstance(optional_foo_shortcut, DalMethodRequestor)
    >>> assert optional_foo_shortcut != foo_shortcut
    >>> optional(foo_shortcut).baz() # Allowed if foo is disabled because of optional
    # If foo is disabled
    None
    >>> foo_shortcut() # Raises error because foo is disabled
    """
    last = requestor._path[-1]
    new_path = requestor._path[:-1]
    new_path = new_path + (PathSegment(name=last.name, optional=True, **last.meta),)
    return DalMethodRequestor(requestor._handler, path=new_path)


class DalMethodRequest:
    """
    Mutable request state. Middleware can modify this.
    """

    def __init__(
        self, ctx: DataAccessContext, path: List[PathSegment], args: List, kwargs: Dict
    ):
        self.ctx = ctx
        self.path = tuple(path)
        self.args = args
        self.kwargs = kwargs
        self.dal_method = None  # Not resolved yet


class DalMethodResolverMiddleware:
    def walk_path(self, request: DalMethodRequest):
        service_or_method = request.ctx.dal._services
        paths = request.path[:]
        # paths = (PathSegment("foo"), PathSegment("bar"), PathSegment("baz"))
        # location = [PathSegment("foo"), PathSegment("bar")] on second yield
        location = []
        while paths:
            segment_name = paths.pop(0)
            location.append(segment_name)
            # Third time through, service_or_method might be `None`, but we want
            # to continue walking the path. Everything after the first missing
            # service/method will be `(location, None)`.
            if service_or_method:
                if isinstance(service_or_method, dict):
                    # first time through, service_or_method is a dict of services
                    service_or_method = service_or_method.get(segment_name)
                else:
                    # second time through, service_or_method is
                    service_or_method = getattr(service_or_method, segment_name)
                yield location, service_or_method
            else:
                yield location, None

    def resolve(self, request: DalMethodRequest):
        service_or_method = None
        for (path_segments, service_or_method) in self.walk_path(request):
            if not service_or_method:
                raise DalMethodError(request, path=path_segments)
        return service_or_method

    def __call__(self, request: DalMethodRequest, handler: Callable):
        """
        Args:
             request: Input from caller
             handler: Downstream middleware or actual DAL method handler
        """
        service_or_method = self.resolve(request)
        if service_or_method and callable(service_or_method):
            request.dal_method = service_or_method
            return handler(request)
        else:
            raise DalMethodError(request)


class OptionalDalMethodResolverMiddleware(DalMethodResolverMiddleware):
    def resolve(self, request: DalMethodRequest):
        service_or_method = None
        for (path_segments, service_or_method) in self.walk_path(request):
            if not service_or_method:
                raise DalMethodError(request, path=path_segments)

            if TESTING: # FIXME metaphor -- do not do this
                if isinstance(service_or_method, OptionalService):
                    if path_segments[-1].optional:
                        # Segment is explicitly guarded
                        pass
                    else:
                        self._assert_feature_guarded(service_or_method.features)

        return service_or_method

    def _assert_feature_guarded(self, features):
        assert guard_stack.current().is_guarded(features)


def handle_dal_method(request: DalMethodRequest):
    assert request.dal_method, "DAL method not resolved"
    return request.dal_method(*request.args, **request.kwargs)


class DataAccessLayer:
    def __init__(
        self,
        middleware=None,
        default_middleware=(DalMethodResolverMiddleware,),
        handler=handle_dal_method,
    ):
        """
        Normally people don't want to think about `dal_method_resolver_middleware`
        because they want the default. Sometimes they want to change the order it
        happens or replace it. In that case:

        DataAccessLayer(middleware=[custom_resolver], default_middleware=None)
        DataAccessLayer(middleware=[
            pre_resolver,
            dal_method_resolver_middleware,
            post_resolve
        ], default_middleware=None)
        """
        self._handler = handler
        middleware = middleware or []
        if default_middleware:
            middleware.extend(default_middleware)

        # Wrap middleware so that self._handler is the first middleware to call
        # and at the end of the stack is `self._handle_dal_method`
        for m in reversed(middleware):
            self._handler = update_wrapper(
                partial(m, handler=self._handler), self._handler
            )

    def _call(self, path: typing.List[PathSegment], *args, **kwargs):
        return self._handler(
            request=DalMethodRequest(
                self._data_manager.get_active_context(), path, args, kwargs
            )
        )

    def __getattr__(self, path):
        assert (
            self._data_manager.get_active_context()
        ), "A DataAccessContext must be started to access the DAL."

        # TODO: OptionalService impl goes here
        # Note: For implementing optional services, we will subclass/implement
        # the `optional` attribute on these PathSegment objects.
        return DalMethodRequestor(self._call, [PathSegment(name=path)])
