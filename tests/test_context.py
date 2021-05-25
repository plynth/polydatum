from __future__ import absolute_import
from polydatum.context import DataAccessContext
from polydatum import DataManager, Service
import pytest


def test_meta():
    """
    Verify that meta can be given and retrieved from a context
    """
    class TestService(Service):
        def get_user(self):
            return self._ctx.meta.user

    user = object()

    dm = DataManager()
    dm.register_services(test=TestService())

    with dm.context(meta={'user': user}) as ctx:
        assert ctx.dal.test.get_user() is user

    # Verify meta can not change
    with dm.context(meta={'user': user}) as ctx:
        with pytest.raises(AttributeError):
            ctx.meta.user = 'foo'
        assert ctx.dal.test.get_user() is user


def test_unique_context():
    """
    Ensure that we get a new context on each DAL enter.
    """
    data_manager = DataManager()
    with data_manager.dal():
        context1 = data_manager.get_active_context()

    with data_manager.dal():
        context2 = data_manager.get_active_context()

    assert context1 != context2


def test_service_context():
    """
    Verify that if you access a Service's context when no
    context is active, you get a RuntimeError.
    """
    class TestService(Service):
        def get_context(self):
            return self._ctx


    data_manager = DataManager()
    data_manager.register_services(test=TestService())

    with data_manager.dal() as dal:
        ctx = dal.test.get_context()
        get_context = dal.test.get_context

    assert isinstance(ctx, DataAccessContext)

    with pytest.raises(RuntimeError):
        get_context()