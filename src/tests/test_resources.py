from __future__ import absolute_import
from polydatum import DataManager
from polydatum.errors import ResourceSetupException
from polydatum.resources import ValueResource
import pytest


def test_resource_setup_and_teardown():
    """
    Verify that Resources are setup and torndown.
    """
    class TestResource(object):
        """
        Example resource that sets as state at
        setup/teardown.
        """
        def __init__(self, store):
            self._store = store

        def __call__(self, context):
            self._store['state'] = 'setup'
            yield self._store['state']
            self._store['state'] = 'torndown'

    store = {}
    data_manager = DataManager()
    data_manager.register_resources(
        test_state=TestResource(store)
    )

    with data_manager.context() as ctx:
        assert 'test_state' not in ctx, 'Resource should be lazy created'
        assert ctx.test_state == 'setup', 'Resource should have been setup'

    assert store['state'] == 'torndown', 'Resource should have been torndown'
    assert len(ctx.get_resource_exit_errors()) == 0


def test_resource_active_context():
    """
    Verify that Resources can not be used if the context is not active.
    """
    data_manager = DataManager()
    data_manager.register_resources(test=ValueResource(True))

    ctx = data_manager.context()

    with pytest.raises(RuntimeError):
        assert ctx.test
        pytest.fail('Resource should not be useable when context has not been setup')

    with ctx:
        assert ctx.test is True

    assert len(ctx.get_resource_exit_errors()) == 0

    with pytest.raises(RuntimeError):
        assert ctx.test
        pytest.fail('Resource should not be useable when context has been torndown')


def test_resource_that_does_not_yield():
    """
    Verify that a resource that does not yield raises a
    ResourceSetupException and ends the context
    """
    def bogus_resource(context):
        """
        This is a valid generator function because of the ``yield``
        but the ``yield`` will never occur so this is an invalid resource.
        Resources must ``yield`` once to be valid.
        """
        if False:
            yield

    data_manager = DataManager()
    data_manager.register_resources(test=bogus_resource)


    with pytest.raises(ResourceSetupException):
        with data_manager.context() as ctx:
            assert ctx.test
            pytest.fail('Context should not have continued')

    assert len(ctx.get_resource_exit_errors()) == 0


def test_resource_that_yields_too_much():
    """
    Verify that a resource that yields more
    than once raises a RuntimeError, but is suppressed
    """
    def chatty_resource(context):
        """
        Resource should only yield once
        """
        yield True
        yield False

    data_manager = DataManager()
    data_manager.register_resources(test=chatty_resource)

    with data_manager.context() as ctx:
        assert ctx.test

    assert ctx.get_resource_exit_errors()[0][0] is RuntimeError


def test_resource_that_has_setup_error():
    """
    Verify that a resource that raises an exception on setup
    prevents dal context from continuing.
    """
    class SetupError(Exception):
        pass

    def error_resource(context):
        if True:
            raise SetupError()
        pytest.fail('Should never get to the point of yielding')
        yield
        pytest.fail('Should never recover')

    data_manager = DataManager()
    data_manager.register_resources(test=error_resource)

    with pytest.raises(SetupError):
        with data_manager.context() as ctx:
            try:
                assert ctx.test
            except SetupError:
                # Expected
                raise
            else:
                pytest.fail('Should have raised SetupError inside context')

    # Even though an error occurred during setup, the resource
    # never has a chance to recover so can't generate any new
    # errors on exit
    assert len(ctx.get_resource_exit_errors()) == 0
