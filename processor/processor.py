# -*- coding: utf-8 -*-
"""
Request processor.

The processor resolves a resource request containing:

  (1) a method, e.g. GET, PUT, POST, DELETE, etc.,
  (2) a absolute path, e.g. '/folder2/resource1' and
  (3) header information, e.g. {'content-type': 'text/html'}) 

into one of the resource objects of the resource tree object. Errors should be
handled by raising a SeisHubError instance.
"""

from StringIO import StringIO
from seishub.exceptions import SeisHubError, NotFoundError, NotImplementedError
from seishub.util.path import splitPath
from twisted.web import http
import urllib


# Maximal length of an URL 
# see U{http://www.boutell.com/newfaq/misc/urllength.html}
MAXIMAL_URL_LENGTH = 1000

# shortcuts
PUT = 'PUT'
GET = 'GET'
POST = 'POST'
DELETE = 'DELETE'
MOVE = 'MOVE'
HEAD = 'HEAD'
OPTIONS = 'OPTIONS'

ALLOWED_HTTP_METHODS = [GET, PUT, POST, DELETE, MOVE, HEAD, OPTIONS]


class Processor:
    """
    General class for processing a resource request.
    
    This class is the layer underneath services like HTTP(S), SFTP and WebDAV.
    """
    def __init__(self, env):
        self.env = env
        # incoming headers
        self.received_headers = {}
        # outgoing headers
        self.code = http.OK
        self.headers = {}
        # set default content
        self.content = StringIO()
        self.data = StringIO()
        # set resource tree, default paths, arguments
        self.args = {}
        self.args0 = {}
        self.prepath = []
        self.postpath = []
        self.tree = self.env.tree
        # set allowed methods
        self.allowed_methods = ALLOWED_HTTP_METHODS
    
    def run(self, method, path='/', content=None, received_headers={}):
        """
        A shortcut to call Processor.process() with default arguments.
        """
        # reset defaults
        self.prepath = []
        self.postpath = []
        self.method = method
        self.path = path
        if content:
            self.content = content
        if received_headers:
            self.received_headers = received_headers
        return self.process()
    
    def process(self):
        """
        Working through the process chain.
        
        This method returns either a dictionary for a folder node containing 
        objects implementing the L{IResource} interface or a single object for 
        a leaf node, like a file or document resource.
        """
        if isinstance(self.path, unicode):
            raise TypeError("URL must be a str instance, not unicode!") 
        # unquote url
        self.path = urllib.unquote(self.path)
        # check for URI length
        if len(self.path) >= MAXIMAL_URL_LENGTH:
            raise SeisHubError(code=http.REQUEST_URI_TOO_LONG)
        # post process path
        self.postpath = splitPath(self.path)
        # we like upper case method names
        self.method = self.method.upper()
        # check for valid methods
        if self.method not in ALLOWED_HTTP_METHODS:
            msg = 'HTTP %s is not implemented.' % self.method
            raise NotImplementedError(msg)
        # read content
        self.content.seek(0, 0)
        self.data=self.content.read()
        # easy args handler
        for id in self.args:
            self.args0[id] = self.args[id][0]
        return self.render()
    
    def render(self):
        """
        Return the rendered result of a child object.
        
        This method should be overwritten in any inheriting class to further
        validate and format the output.
        """
        # traverse the resource tree
        child = getChildForRequest(self.env.tree, self)
        return child.render(self)
    
    def setHeader(self, id, value):
        self.headers[id]=value


def getChildForRequest(resource, request):
    """
    Traverse resource tree to find who will handle the request.
    """
    while request.postpath and not resource.is_leaf:
        id = request.postpath.pop(0)
        request.prepath.append(id)
        resource = resource.getChildWithDefault(id, request)
        if not resource:
            raise NotFoundError("Resource %s not found." % request.path)
    return resource
