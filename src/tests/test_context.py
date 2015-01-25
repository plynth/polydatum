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
