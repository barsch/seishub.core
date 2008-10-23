# -*- coding: utf-8 -*-

from twisted.web import http #@unresolved import

class SeisHubError(Exception):
    """The processor error class."""
    
    def __init__(self, *args, **kwargs):
        """@keyword message: error message
        @type message: str 
        @keyword code: http error code
        @type code: int
        """
        Exception.__init__(self, *args, **kwargs)
        message = kwargs.get('message', None)
        if not message and args:
            message = args[0]
        self.code = kwargs.get('code', 500)
        self.message = message or http.RESPONSES.get(self.code, '')
    
    def __str__(self):
        return 'Error %s: %s' % (self.code, self.message)
    
class UnauthorizedError(SeisHubError):
    code = 401 # Unauthorized
    
class InternalServerError(SeisHubError):
    code = 500 # Internal server error
    
class NotFoundError(SeisHubError):
    code = 404 # Not found
    
class DeletedObjectError(SeisHubError):
    code = 410 # Gone
    
class DuplicateObjectError(SeisHubError):
    code = 409 # Conflict
    
class InvalidObjectError(SeisHubError):
    code = 400 # Bad request
    
class InvalidParameterError(SeisHubError):
    code = 400 # Bad request
