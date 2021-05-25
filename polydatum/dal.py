from __future__ import absolute_import

import inspect
from contextlib import contextmanager
from functools import partial, update_wrapper
from typing import Callable, Tuple

from polydatum.context import DataAccessContext
from polydatum.errors import AlreadyExistsException, InvalidMiddleware
from polydatum.middleware import (
    DalCommand,
    DalCommandRequest,
    PathSegment,
    dal_method_resolver_middleware,
    handle_dal_method,
)
from polydatum.util import is_generator

from .context import _ctx_stack
from .resources import ResourceManager


class DataAccessLayer(object):
    """
    Gives you access to a DataManager's services.
    """

    # default middleware classes need to be instantiated before being
    # passed to the init function because the resulting object is called
    # directly (__call__).
    def __init__(
        self,
        data_manager,
        middleware=None,
        default_middleware=(dal_method_resolver_middleware,),
        handler=handle_dal_method,
    ):
        self._services = {}
        self._data_manager = data_manager
        self._handler = handler
        reversed_middleware = []

        middleware = middleware or []
        if default_middleware:
            middleware.extend(default_middleware)
        for m in reversed(middleware):
            if inspect.isclass(m):
                m = m()
            if not isinstance(m, Callable):
                raise InvalidMiddleware(f"{m} is not a valid Callable middleware")
            reversed_middleware.append(m)

        # Reverse middleware so that self._handler is the first middleware to call
        # and at the end of the stack is `self._handler`
        for m in reversed_middleware:
            self._handler = update_wrapper(
                partial(m, handler=self._handler), self._handler
            )

    def register_services(self, **services):
        """
        Register Services that can be accessed by this DAL. Upon
        registration, the service is set up.

        :param **services: Keyword arguments where the key is the name
          to register the Service as and the value is the Service.
        """
        for key, service in services.items():
            if key in self._services:
                raise AlreadyExistsException(
                    "A Service for {} is already registered.".format(key)
                )

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

    def _call(self, path: Tuple[PathSegment, ...], *args, **kwargs):
        return self._handler(
            request=DalCommandRequest(
                self._data_manager.require_active_context(), path, args, kwargs
            )
        )

    def __getattr__(self, name: str) -> DalCommand:
        return DalCommand(self._call, path=(PathSegment(name=name),))

    def __getitem__(self, path):
        """
        Get a service method by dot notation path. Useful for
        serializing DAL methods as strings.

        If the first part of the path is "dal", it is ignored.

        Example::

            dal['myservice.get'](my_id)
        """
        paths = path.split(".")
        paths = paths[1:] if paths[0] == "dal" else paths
        path_segments = tuple(PathSegment(name=p) for p in paths)
        return DalCommand(self._call, path=path_segments)


class DataManager(object):
    """
    Registry for Services, Resources, and other DAL objects.
    """

    DataAccessLayer = DataAccessLayer

    def __init__(self, resource_manager=None):
        if not resource_manager:
            resource_manager = ResourceManager(self)

        self._resource_manager = resource_manager
        self._dal = self.DataAccessLayer(self)
        self._middleware = []

        # TODO Make _ctx_stack only exist on the DataManager
        self.ctx_stack = _ctx_stack

    def register_context_middleware(self, *middleware):
        """
        :param middleware: Middleware in order of execution
        """
        for m in middleware:
            if not is_generator(m):
                raise Exception(
                    "Middleware {} must be a Python generator callable.".format(m)
                )

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

    def require_active_context(self):
        """
        Get the active context, but require it to actually be active.

        :return: DataAccessContext
        :raises: RuntimeError if no context is active
        """
        context = self.get_active_context()
        if not context:
            raise RuntimeError("No active context")
        return context

    @contextmanager
    def dal(self, meta=None):
        """
        Start a new DataAccessContext.

        :returns: DataAccessLayer for this DataManager
        """
        with self.context(meta=meta):
            yield self._dal
