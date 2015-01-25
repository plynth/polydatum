from polydatum import DataManager
from polydatum import Service
from polydatum.context import DataAccessContext
import pytest


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