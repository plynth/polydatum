from contextlib import contextmanager

from .request import Request
from . import context
from .resources import ResourceManager
from .services import Service

class DataAccessLayer(object):
    """
    Gives you access to a DataManager's services.
    """

    def __init__(self, data_manager):
        self._services = {}
        self._data_manager = data_manager

    def register_services(self, **services):
        for key, service in services.items():
            service.setup(self._data_manager)
            self._services[key] = service
        return self

    def __getattr__(self, name):
        assert context.current_context, 'A Request must be started to access the DAL.'
        return self._services[name]

    def __getitem__(self, path):
        """
        Get a service method by dot notation path. Useful for
        serializing DAL methods as strings.

        If the first part of the path is "dal", it is ignored.

        Example::

            dal['myservice.get'](my_id)
        """
        paths = path.split('.')
        p = paths.pop(0)
        if p == 'dal':
            p = paths.pop(0)
        loc = self._services[name]
        while 1:
            try:
                p = paths.pop(0)
            except IndexError:
                break
            else:
                loc = getattr(loc, p)
        return loc

class DataManager(object):
    """
    Registry for Services, Resources, and other DAL objects.
    """

    def __init__(self, resource_manager=None, request_class=Request):
        # Master Service that contains all other services
        self._request_class = request_class

        if not resource_manager:
            resource_manager = ResourceManager(self)

        self._resource_manager = resource_manager
        self._dal = DataAccessLayer(self)

    def register_resources(self, **resources):
        """
        Register Resources with the ResourceManager.
        """
        self._resource_manager.register_resources(**resources)

    def register_services(self, **services):
        """
        Register Services with the DataAccessLayer
        """
        self._dal.register_services(**services)

    def get_resource(self, name):
        return self._resource_manager[name]

    def get_dal(self):
        return self._dal

    @contextmanager
    def dal(self, request=None):
        """
        Start a new Request Context.

        :param request: A Request to handle. Creates a new one if None.

        :returns: DataAccessLayer for this DataManager
        """
        if not request:
            request = self._request_class()

        with context.DataAccessContext(self, request):
            yield self._dal