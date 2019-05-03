from __future__ import absolute_import
from polydatum import DataManager, Service
from polydatum.errors import MiddlewareSetupException
from polydatum.resources import ValueResource
import pytest


class StateTestService(Service):
    def ping(self):
        return 'PONG'

    def change_state(self, state):
        self._ctx.store['state'] = state

    def get_state(self):
        return self._ctx.store['state']


def test_middleware():
    """
    Verify that Middleware can access Resources and that
    the Middleware is setup and torndown.
    """
    class TestMiddleware(object):
        """
        Example middleware that sets it's state at
        setup and teardown.
        """
        def __call__(self, context):
            context.store['state'] = 'setup'
            yield
            context.store['state'] = 'torndown'

    data_store = {}

    data_manager = DataManager()
    data_manager.register_services(test=StateTestService())
    # Middleware that starts and ends with the context
    data_manager.register_context_middleware(
        TestMiddleware(),
    )
    data_manager.register_resources(
        store=ValueResource(data_store)
    )

    with data_manager.dal() as dal:
        assert dal.test.get_state() == 'setup'
        dal.test.change_state('middle')
        assert dal.test.get_state() == 'middle'

    assert data_store['state'] == 'torndown'


def test_middleware_that_does_not_yield():
    """
    Verify that middleware that does not yield raises a
    MiddlewareSetupException and prevents dal context from starting.
    """
    def bogus_middleware(context):
        """
        This is a valid generator function because of the ``yield``
        but the ``yield`` will never occur so this is invalid middleware.
        Middleware must ``yield`` once to be valid.
        """
        if False:
            yield

    data_manager = DataManager()
    data_manager.register_services(test=StateTestService())
    data_manager.register_context_middleware(bogus_middleware)

    with pytest.raises(MiddlewareSetupException):
        with data_manager.dal():
            pytest.fail('Context should not have continued')


def test_middleware_that_yields_too_much():
    """
    Verify that middleware that yields more
    than once raises a RuntimeError
    """
    def chatty_middleware(context):
        """
        Middleware should only yield once
        """
        yield
        yield

    data_manager = DataManager()
    data_manager.register_context_middleware(chatty_middleware)

    with pytest.raises(RuntimeError):
        with data_manager.dal():
            pass


def test_middleware_that_has_setup_error():
    """
    Verify that middleware that raises an exception on setup
    prevents dal context from starting
    """
    class SetupError(Exception):
        pass

    def error_middleware(context):
        if True:
            raise SetupError()
        yield

    data_manager = DataManager()
    data_manager.register_services(test=StateTestService())
    data_manager.register_context_middleware(error_middleware)

    with pytest.raises(SetupError):
        with data_manager.dal():
            pytest.fail('Context should not have continued')
