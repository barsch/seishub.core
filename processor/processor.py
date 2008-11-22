# -*- coding: utf-8 -*-

from StringIO import StringIO
from seishub.exceptions import SeisHubError, NotFoundError, NotImplementedError
from seishub.util.path import splitPath
from twisted.web import http


# @see: http://www.boutell.com/newfaq/misc/urllength.html
MAX_URI_LENGTH = 1000

PUT = 'PUT'
GET = 'GET'
POST = 'POST'
DELETE = 'DELETE'
MOVE = 'MOVE'

ALLOWED_HTTP_METHODS = [GET, PUT, POST, DELETE, MOVE]


class Processor:
    """General class for processing a resource request.
    
    This class is the layer underneath services like REST, SFTP and WebDAV.
    """
    
    def __init__(self, env):
        self.env = env
        # response code and header for a request
        self.response_code = http.OK
        self.response_header = {}
        self.received_headers = {}
        # set default content
        self.content = StringIO()
        self.data = StringIO()
        # get resource tree
        self.prepath = ''
        self.tree = self.env.tree
    
    def run(self, method, path='/', content=None, received_headers={}):
        """A shortcut to call Processor.process with default arguments."""
        self.method = method
        self.path = path
        if content:
            self.content = content
        if received_headers:
            self.received_headers = received_headers
        return self._process()
    
    def _process(self):
        """Working through the process chain.
        
        This method may return either a dictionary for a folder resource or an
        single object/basestring for an actual file/document resource.
        
        A folder dictionary contains ids and objects implementing IResource.
        """
        # check for URI length
        if len(self.path) >= MAX_URI_LENGTH:
            raise SeisHubError(code=http.REQUEST_URI_TOO_LONG)
        # post process path
        self.postpath = splitPath(self.path)
        self.prepath = []
        # we like upper case method names
        self.method = self.method.upper()
        # check for valid methods
        if self.method not in ALLOWED_HTTP_METHODS:
            msg = 'HTTP %s is not implemented.' % self.method
            raise NotImplementedError(msg)
        # read content
        self.content.seek(0)
        self.data=self.content.read()
        # traverse the resource tree
        child = getChildForRequest(self.env.tree, self)
        return child.render(self)


def getChildForRequest(resource, request):
    """Traverse resource tree to find who will handle the request."""
    
    while request.postpath and not resource.is_leaf:
        id = request.postpath.pop(0)
        request.prepath.append(id)
        resource = resource.getChildWithDefault(id, request)
        if not resource:
            raise NotFoundError()
    return resource
