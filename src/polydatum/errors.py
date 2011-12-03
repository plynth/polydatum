class ServiceError(Exception):
    code = 500

class NotFound(ServiceError):
    code = 404