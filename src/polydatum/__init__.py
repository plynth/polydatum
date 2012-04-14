from polydatum.request import Request
from polydatum.globals import _request_ctx_stack

class Context(object):
    def __init__(self, dal, request):
        self.dal = dal
        self.request = request

class DataLayer(object):
    def __init__(self):
        self._services = {}

    def register_services(self, **services):
        for key, service in services.iteritems():
            service.setup(self)
            self._services[key] = service

    def __getattr__(self, name):
        assert self.request, 'A DataLayer Request must be started.'
        return self._services[name]

    def __getitem__(self, path):
        """
        Get a service method by dot notation path.
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

    def __enter__(self):
        request = Request()
        _request_ctx_stack.push(Context(self, request))
        return request

    def __exit__(self, exc_type=None, exc_value=None, tb=None):
        _request_ctx_stack.pop()

    @property
    def request(self):
        """
        Get the current request
        """
        return _request_ctx_stack.top

class Service(object):
    def __init__(self):
        self.dal = None
        self._services = {}

    def register_services(self, **services):
        for key, service in services.iteritems():
            service.setup(self.dal)
            self._services[key] = service

    def __getattr__(self, name):
        return self._services[name]

    def setup(self, dal):
        self.dal = dal
        for key, service in self._services.iteritems():
            service.setup(self.dal)