class ServiceError(Exception):
    code = 500


class NotFound(ServiceError):
    code = 404


class ErrorsOnClose(Exception):
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


class MiddlewareException(Exception):
    pass


class MiddlewareSetupException(MiddlewareException):
    pass