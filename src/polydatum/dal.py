from __future__ import absolute_import
from contextlib import contextmanager
from .context import DataAccessContext
from polydatum.errors import AlreadyExistsException
from polydatum.util import is_generator
from .resources import ResourceManager
from .context import _ctx_stack


class DataAccessLayer(object):
    """
    Gives you access to a DataManager's services.
    """

    def __init__(self, data_manager):
        self._services = {}
        self._data_manager = data_manager

    def register_services(self, **services):
        """
        Register Services that can be accessed by this DAL. Upon
        registration, the service is set up.

        :param **services: Keyword arguments where the key is the name
          to register the Service as and the value is the Service.
        """
        for key, service in services.items():
            if key in self._services:
                raise AlreadyExistsException('A Service for {} is already registered.'.format(key))

            self._init_service(key, service)
        return self

    def replace_service(self, key, service):
        """
        Replace a Service with another. Usually this is a bad
        idea but is often done in testing to replace a Service
        with a mock version. It's also used for practical
        reasons if you need to swap out services for different
        framework implementations (ex: Greenlet version vs
        threaded)

        :param key: Name of service
        :param service: Service
        """
        return self._init_service(key, service)

    def _init_service(self, key, service):
        service.setup(self._data_manager)
        self._services[key] = service
        return service

    def __getattr__(self, name):
        assert self._data_manager.get_active_context(), 'A DataAccessContext must be started to access the DAL.'
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
        loc = self._services[p]
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

    def __init__(self, resource_manager=None):
        if not resource_manager:
            resource_manager = ResourceManager(self)

        self._resource_manager = resource_manager
        self._dal = DataAccessLayer(self)
        self._middleware = []

        # TODO Make _ctx_stack only exist on the DataManager
        self.ctx_stack = _ctx_stack

    def register_context_middleware(self, *middleware):
        """
        :param middleware: Middleware in order of execution
        """
        for m in middleware:
            if not is_generator(m):
                raise Exception('Middleware {} must be a Python generator callable.'.format(m))

        self._middleware.extend(middleware)

    def get_middleware(self, context):
        """
        Returns all middleware in order of execution

        :param context: The DataAccessContext. You could override the DataManager
            and return different middleware based on the context here.
        """
        return self._middleware

    def register_resources(self, **resources):
        """
        Register Resources with the ResourceManager.
        """
        self._resource_manager.register_resources(**resources)

    def replace_resource(self, key, resource):
        """
        Replace a Resources on the ResourceManager.
        """
        self._resource_manager.replace_resource(key, resource)

    def register_services(self, **services):
        """
        Register Services with the DataAccessLayer
        """
        self._dal.register_services(**services)

    def replace_service(self, key, service):
        """
        Replace a Service on the DataAccessLayer
        """
        self._dal.replace_service(key, service)

    def get_resource(self, name):
        if name in self._resource_manager:
            return self._resource_manager[name]

    def get_dal(self):
        return self._dal

    def context(self, meta=None):
        return DataAccessContext(self, meta=meta)

    def get_active_context(self):
        """
        Safely checks if there's a context active
        and returns it
        """
        if self.ctx_stack.top:
            return self.ctx_stack.top

    @contextmanager
    def dal(self, meta=None):
        """
        Start a new DataAccessContext.

        :returns: DataAccessLayer for this DataManager
        """
        with self.context(meta=meta):
            yield self._dal