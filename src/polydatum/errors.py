class PolydatumException(Exception):
    pass


class ServiceError(PolydatumException):
    code = 500


class NotFound(ServiceError):
    code = 404


class ErrorsOnClose(PolydatumException):
    def __init__(self, message, exceptions):
        super(Exception, self).__init__(message)
        self.message = message
        self.exceptions = exceptions

    def __str__(self):
        return '<{} {}: {}>'.format(
            self.__class__.__name__,
            self.message,
            self.exceptions
        )


class MiddlewareException(PolydatumException):
    pass


class MiddlewareSetupException(MiddlewareException):
    """
    Middleware setup failed
    """


class ResourceException(PolydatumException):
    pass


class ResourceSetupException(ResourceException):
    """
    Resource setup failed
    """