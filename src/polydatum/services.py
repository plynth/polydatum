class Service(object):
    def __init__(self):
        self._services = {}
        self._data_manager = None
        self._dal = None

    def register_services(self, **services):
        for key, service in services.items():
            service.setup(self._data_manager)
            self._services[key] = service
        return self

    def __getattr__(self, name):
        try:
            return self._services[name]
        except KeyError as e:
            raise AttributeError(name) from e

    def setup(self, data_manager):
        """
        Hook to setup this service with a specific DataManager.

        Will recursively setup sub-services.
        """
        self._data_manager = data_manager
        if self._data_manager:
            self._dal = self._data_manager.get_dal()
        else:
            self._dal = None

        for key, service in self._services.items():
            service.setup(self._data_manager)

    @property
    def _ctx(self):
        """
        Returns the current DataAccessContext.

        :return: DataAccessContext
        :raises: RuntimeError if no context is active
        """
        return self._data_manager.require_active_context()