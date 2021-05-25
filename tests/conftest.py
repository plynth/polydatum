import pytest

from polydatum import Service
from polydatum.dal import DataManager
from polydatum.middleware import PathSegment


@pytest.fixture
def path_segment_factory():
    """
    A factory fixture for a basic PathSegment for use in testing.

    Normally instantiating this for the first time in code implementation
    will be done by the DAL itself. Because it's somewhat cumbersome, this
    fixture helps prevent typos and such.
    """

    def _factory(name="example"):
        return (PathSegment(name=name),)

    return _factory


class UserService(Service):
    def user_method(self):
        return "user-service"


class UserProfileService(Service):
    def profile_method(self):
        return "profile-nested-service"


class SampleService(Service):
    def sample_method(self):
        return "sample-nested-service"


class ExampleService(Service):
    def example_method(self):
        return "example-nested-service"


class DemoService(Service):
    def demo_method(self):
        return "demo-nested-service"


@pytest.fixture()
def sub_service_setup():
    """
    Sample nested service structure
    """

    def _get_dam():
        data_manager = DataManager()
        data_manager.register_services(
            users=UserService().register_services(
                profile=UserProfileService().register_services(
                    sample=SampleService().register_services(
                        example=ExampleService().register_services(demo=DemoService())
                    )
                )
            )
        )
        return data_manager

    return _get_dam
