from __future__ import absolute_import
import pytest
from polydatum import DataManager
from polydatum import Service
from polydatum.errors import AlreadyExistsException


def test_register_unique_service():
    """
    Verify you can not register an existing service
    """
    data_manager = DataManager()
    data_manager.register_services(test=Service())

    with pytest.raises(AlreadyExistsException):
        data_manager.register_services(test=Service())


def test_replace_unique_service():
    """
    Verify you can replace an existing service
    """
    data_manager = DataManager()
    data_manager.register_services(test=Service())

    new_service = Service()
    data_manager.replace_service('test', new_service)

    with data_manager.dal() as dal:
        assert dal.test is new_service


def test_register_unique_resource():
    """
    Verify you can not register an existing resource
    """
    def resource(context):
        yield

    data_manager = DataManager()
    data_manager.register_resources(test=resource)

    with pytest.raises(AlreadyExistsException):
        data_manager.register_resources(test=resource)


def test_replace_unique_resource():
    """
    Verify you can replace an existing resource
    """

    def resource_a(context):
        yield 'a'

    def resource_b(context):
        yield 'b'

    data_manager = DataManager()
    data_manager.register_resources(test=resource_a)

    data_manager.replace_resource('test', resource_b)

    with data_manager.context() as ctx:
        assert ctx.test == 'b'