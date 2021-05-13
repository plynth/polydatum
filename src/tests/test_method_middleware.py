from typing import Callable

import pytest

from polydatum import DataAccessLayer, Service
from polydatum.dal import DataManager
from polydatum.middleware import DalCommandRequest, DalCommand, dal_method_resolver_middleware, \
    handle_dal_method, dal_resolver, DalMethodError
from polydatum.errors import InvalidMiddleware


class FooMiddleware:
    # Does not implement __call__ and hence not
    # a Callable
    pass


@pytest.mark.parametrize('middleware', [
    (FooMiddleware, ),
    (FooMiddleware(), ),
    (True, ),
    ('random-string',),
    ([],),
    (None,),
])
def test_dal_middleware_requires_callable(middleware):
    """
    Verify that you can specify method middleware as either an instance
    or a class (as a convenience).
    """
    with pytest.raises(InvalidMiddleware):
        DataAccessLayer(data_manager=None, middleware=[middleware], default_middleware=None)


def test_dal_method_middleware():
    """
    Verify that when calling a method on a service off the DAL,
    the method middlewares run, in the correct order and run
    before the method itself is called.


    We deliberately do not use the DalMethodResolverMiddleware here,
    because we are testing middleware call chains, not functionality
    of that class.
    """
    def test_method():
        return ['default-handler-call']

    class OuterMiddleware:
        def __call__(self, request, handler):
            result = ['outer-middleware-ingress']
            result.extend(handler(request))
            result.append('outer-middleware-egress')
            return result

    class SecondMiddleware:
        def __call__(self, request, handler):
            result = ['second-middleware-ingress']
            result.extend(handler(request))
            result.append('second-middleware-egress')
            return result

    # Verify custom default middleware
    class DefaultMiddleware:
        def __call__(self, request, handler):
            result = ['default-middleware-ingress']
            # We need to get past the DalMethodResolverMiddleware
            # which sets the `dal_method` attribute to
            # the method that has to be called
            request.dal_method = test_method
            result.extend(handler(request))
            result.append('default-middleware-egress')
            return result

    dm = DataManager()

    dal = DataAccessLayer(data_manager=dm, middleware=[OuterMiddleware(), SecondMiddleware()],
        default_middleware=(DefaultMiddleware(),))

    with dm.context():
        result = dal.fake.service.method()

    assert result == [
        'outer-middleware-ingress',
        'second-middleware-ingress',
        'default-middleware-ingress',
        'default-handler-call',
        'default-middleware-egress',
        'second-middleware-egress',
        'outer-middleware-egress',
    ]


def test_dal_method_middleware_abort():
    """
    Verify that when method middleware runs, any middleware that
    raises an exception will prevent the method from getting called.
    """

    middleware_requests = []

    class SpecificException(Exception):
        pass

    def test_method():
        middleware_requests.append("test_method_called")
        return True

    class AuthMiddleware():
        """
        An example middleware for authentication purposes
        """

        def user_is_authenticated(self, path):
            """
            Simulating an authenticated method to check for
            no exception cases
            """
            return path[-1].name == 'authenticated_method'

        def __call__(self, request, handler):
            if self.user_is_authenticated(request.path):
                result = handler(request)
                return result
            raise SpecificException

    # Verify custom default middleware
    class DefaultMiddleware:
        def __call__(self, request, handler):
            # We need to get past the DalMethodResolverMiddleware
            # which sets the `dal_method` attribute to
            # the method that has to be called
            request.dal_method = test_method
            result = handler(request)
            return result

    dm = DataManager()

    dal = DataAccessLayer(data_manager=dm, middleware=[AuthMiddleware()],
                          default_middleware=(DefaultMiddleware(),))

    with dm.context():
        assert dal.fake.authenticated_method()
        assert middleware_requests[0] == "test_method_called"
        with pytest.raises(SpecificException):
            dal.fake.service.method()


def test_dal_attribute_access_returns_dal_method_requester():
    """
    Verify that accessing an attribute on the DAL that does not
    exist returns an instance of DalCommand.

    This is important because this starts building the call chain
    which is used to resolve methods later.
    """
    dm = DataManager()
    dal = DataAccessLayer(data_manager=dm)

    # Explicitly show that an attribute that is reset returns a
    # DMR instance
    dal.real = "real attribute"
    del dal.real
    with dm.context():
        assert isinstance(dal.real, DalCommand)

    with dm.context():
        thing = dal.foo.bar.fake
        thing2 = dal.service.foo.test.example
        thing3 = dal.method
        assert isinstance(thing, DalCommand)
        assert isinstance(thing2, DalCommand)
        assert isinstance(thing3, DalCommand)
        thing4 = getattr(dal, 'random')
        assert isinstance(thing4, DalCommand)

    # also make sure to verify the error case where a context
    # has not been started yet.
    with pytest.raises(AssertionError):
        dal.foo.bar.fake


def test_default_dal_handler(path_segment_factory):
    """
    Verify that the default dal handler performs validation on the request,
    and then calls the dal method that was resolved.
    """
    called_args = []

    def my_method(*args, **kwargs):
        called_args.append((args, kwargs))

    dm = DataManager()

    expected_args = ['foo']
    expected_kwargs = dict(test='bar')
    with dm.context() as ctx:
        request = DalCommandRequest(
            ctx,
            path_segment_factory(),
            args=expected_args,


            kwargs=expected_kwargs
        )
        request.dal_method = my_method

    handle_dal_method(request)

    assert len(called_args) == 1
    assert expected_args, expected_kwargs == called_args[0]


def test_dal_middleware_monkeypatch(monkeypatch):
    """
    Verify that pytest monkeypatching still works with dal services and methods.
    """

    class ExampleService(Service):
        def example_foo(self):
            return "example-foo"

    def mock_example_foo(*args):
        return 'mock value'

    dm = DataManager()
    dm.register_services(
        example=ExampleService()
    )

    with dm.context() as ctx:
        monkeypatch.setattr(
            # Mock the DAL method after anticipate is called (`func` is the original
            # function for the decorated method).
            dal_resolver(ctx, ctx.dal.example.path),
            "example_foo",
            mock_example_foo,
        )
        result = ctx.dal.example.example_foo()
        assert result == 'mock value'


def test_resolve_empty_path():
    """
    Verify dal_resolver resolves empty path
    """
    class SampleService(Service):
        def sample_method(self):
            pass

    dm = DataManager()
    with dm.context() as ctx:
        with pytest.raises(DalMethodError):
            dal_resolver(ctx, ())

    dm.register_services(sample=SampleService())
    with dm.context() as ctx:
        with pytest.raises(DalMethodError):
            # verify that even with a service, we aren't
            # accidentally verifying some edge case on the DAL
            dal_resolver(ctx, ())
