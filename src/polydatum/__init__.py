from polydatum.request import Request, _request_ctx_stack

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

    def __enter__(self):
        request = Request()
        _request_ctx_stack.push(request)
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