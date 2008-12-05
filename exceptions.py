# -*- coding: utf-8 -*-

from twisted.web import http


class SeisHubError(Exception):
    """
    The general SeisHub error class.
    """
    code = None
    
    def __init__(self, *args, **kwargs):
        """
        @keyword message: error message
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
    """
    Returns HTTP Status Code 403: Forbidden.
    
    The server understood the request, but is refusing to fulfill it. 
    Authorization will not help and the request SHOULD NOT be repeated. If 
    the request method was not HEAD and the server wishes to make public why 
    the request has not been fulfilled, it SHOULD describe the reason for the 
    refusal in the entity. If the server does not wish to make this 
    information available to the client, the status code 404 (Not Found) can 
    be used instead. 
    """
    code = http.FORBIDDEN


class NotImplementedError(SeisHubError):
    """
    Returns HTTP Status Code 501: Not Implemented.
    
    The server does not support the functionality required to fulfill the 
    request. This is the appropriate response when the server does not 
    recognize the request method and is not capable of supporting it for any 
    resource.
    """ 
    code = http.NOT_IMPLEMENTED


class NotAllowedError(SeisHubError):
    """
    Returns HTTP Status Code 405: Method Not Allowed.
    
    The method specified in the Request-Line is not allowed for the resource 
    identified by the Request-URI. The response MUST include an Allow header 
    containing a list of valid methods for the requested resource.
    """
    code = http.NOT_ALLOWED
    allowed_methods = ()
    
    def __init__(self, allowed_methods, *args, **kwargs):
        self.allowed_methods = allowed_methods
        SeisHubError.__init__(self, allowed_methods, *args, **kwargs)
