from __future__ import absolute_import
from polydatum.errors import AlreadyExistsException
from polydatum.util import is_generator


class Resource(object):
    # Deprecated 0.8.4
    _data_manager = None

    def setup(self, data_manager):
        """
        Hook to setup this Resource with a specific DataManager.

        Deprecated (0.8.4) in favor of making Resources simple enough
        that they can be context managers. To access the
        data_manager, use ``context.data_manager`` in the
        ``__call__`` method.
        """
        self._data_manager = data_manager

    def __call__(self, context):
        """
        Called by DataAccessContext when a resource is first
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
    Manages resources for a DAL. Resources can be things such
    as database connections, caches, etc.
    """
    def __init__(self, data_manager):
        self._resources = {}
        self._data_manager = data_manager

    def register_resources(self, **resources):
        """
        Register resources with the ResourceManager.
        """
        for key, resource in resources.items():
            if key in self._resources:
                raise AlreadyExistsException('A Service for {} is already registered.'.format(key))

            self._init_resource(key, resource)

    def replace_resource(self, key, resource):
        """
        Replace a Resource with another. Usually this is a bad
        idea but is often done in testing to replace a Resource
        with a mock version. It's also used for practical
        reasons if you need to swap out resources for different
        framework implementations (ex: Greenlet version vs
        threaded)

        :param key: Name of resource
        :param resource: Resource
        """
        return self._init_resource(key, resource)

    def _init_resource(self, key, resource):
        if not is_generator(resource):
            raise Exception('Resource {}:{} must be a Python generator callable.'.format(key, resource))

        if hasattr(resource, 'setup') and callable(resource.setup):
            # Setup is deprecated as of 0.8.4
            resource.setup(self._data_manager)

        self._resources[key] = resource

    def __getitem__(self, name):
        """
        Get a Resource by name.
        """
        return self._resources[name]

    def __contains__(self, name):
        return name in self._resources


class ValueResource(Resource):
    """
    Resource that's just the instantiated value
    """

    def __init__(self, value):
        super(ValueResource, self).__init__()
        self._value = value

    def __call__(self, context):
        yield self._value