# -*- coding: utf-8 -*-

from twisted.web import http


class SeisHubError(Exception):
    """The general SeisHub error class."""
    code = None
    
    def __init__(self, *args, **kwargs):
        """@keyword message: error message
        @type message: str 
        @keyword code: http error code
        @type code: int
        """
        message = kwargs.pop('message', None)
        if not message and args:
            message = str(args[0])
        self.message = message or http.RESPONSES.get(self.code, '')
        code = kwargs.pop('code', http.INTERNAL_SERVER_ERROR)
        self.code = self.code or code
        Exception.__init__(self, *args, **kwargs)
    
#    def __str__(self):
#        return 'Error %s: %s' % (self.code, self.message)


class UnauthorizedError(SeisHubError):
    code = http.UNAUTHORIZED # 401


class InternalServerError(SeisHubError):
    code = http.INTERNAL_SERVER_ERROR # 500


class NotFoundError(SeisHubError):
    code = http.NOT_FOUND # 404


class DeletedObjectError(SeisHubError):
    code = http.GONE # 410


class DuplicateObjectError(SeisHubError):
    code = http.CONFLICT # 409


class InvalidObjectError(SeisHubError):
    code = http.BAD_REQUEST # 400


class InvalidParameterError(SeisHubError):
    code = http.BAD_REQUEST # 400


class ForbiddenError(SeisHubError):
    code = http.FORBIDDEN # 403


class NotImplementedError(SeisHubError):
    code = http.NOT_IMPLEMENTED # 501
