class Resource(object):
    def __init__(self):
        self._data_manager = None

    def setup(self, data_manager):
        """
        Hook to setup this Resource with a specific DataManager.
        """
        self._data_manager = data_manager

    def __call__(self, context):
        """
        Called by DataAccessContext when a resouce is first
        requested within a particular context. This generator
        should yield one value that represents the resource
        for `context`. It could open a new connection, or just
        return the current resource. After yielding, close
        the resource if it is no longer needed.

        Example::

            connection = self.new_connection()
            try:
                yield connection
            except:
                connection.rollback()
                connection.close()
            else:
                # No errors
                connection.commit()
                connection.close()
        """
        yield None

class ResourceManager(object):
    """
    Manages resouces for a DAL. Resouces can be things such
    as database connections, caches,etc.    
    """
    def __init__(self, data_manager):
        self._resources = {}
        self._data_manager = data_manager

    def register_resources(self, **resources):
        """
        Register resources with the ResourceManager.
        """
        for name, resource in resources.items():
            self._resources[name] = resource
            resource.setup(self._data_manager)

    def __getitem__(self, name):
        return self._resources[name]    