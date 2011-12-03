class DataLayer(object):
    def __init__(self):
        self._services = {}

    def register_services(self, **services):
        for key, service in services.iteritems():
            service.setup(self)
            self._services[key] = service

    def __getattr__(self, name):
        return self._services[name]

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