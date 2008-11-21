# -*- coding: utf-8 -*-

from StringIO import StringIO
from seishub.exceptions import SeisHubError
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
ALLOWED_MAPPER_METHODS = [GET, PUT, POST, DELETE]
NOT_IMPLEMENTED_HTTP_METHODS = ['TRACE', 'OPTIONS', 'COPY', 'HEAD', 'PROPFIND',
                                'PROPPATCH', 'MKCOL', 'CONNECT', 'PATCH',
                                'LOCK', 'UNLOCK']


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
        self.tree = self.env.tree
    
    def run(self, method, path='/', content=None, received_headers={}):
        """A shortcut to call Processor.process with default arguments."""
        self.method = method
        self.path = path
        if content:
            self.content = content
        if received_headers:
            self.received_headers = received_headers
        return self.process()
    
    def process(self):
        """Working through the process chain."""
        # check for URI length
        if len(self.path) >= MAX_URI_LENGTH:
            raise SeisHubError(code=http.REQUEST_URI_TOO_LONG)
        # post process path
        self.postpath = splitPath(self.path)
        self.prepath = []
        # we like upper case method names
        self.method = self.method.upper()
        # check for valid but not implemented methods
        if self.method in NOT_IMPLEMENTED_HTTP_METHODS:
            msg = 'HTTP %s is not implemented.' % self.method
            raise SeisHubError(msg, code=http.NOT_IMPLEMENTED)
        # check for valid methods
        if self.method not in ALLOWED_HTTP_METHODS:
            msg = 'HTTP %s is not allowed.' % self.method
            raise SeisHubError(msg, code=http.NOT_ALLOWED)
        # read content
        self.content.seek(0)
        self.data=self.content.read()
        # traverse the resource tree
        data =self.tree.start(self)
        return self.render(data)

#    def _processAlias(self, package_id, resourcetype_id, alias):
#        """Process an alias request."""
#        # if alias > 1 - may be an indirect resource request - SFTP problem
#        if len(alias)>1:
#            # XXX: missing yet
#            raise SeisHubError(code=http.NOT_IMPLEMENTED)
#        # remove leading @
#        alias_id = alias[0][1:]
#        # fetch alias
#        aliases = self.env.registry.aliases.get(package_id, resourcetype_id,
#                                                alias_id)
#        try:
#            resource_objs = self.env.catalog.query(aliases[0].getQuery())
#        except Exception, e:
#            self.env.log.error(e)
#            raise SeisHubError(e, code = http.INTERNAL_SERVER_ERROR)
#        else:
#            return self.renderResourceList(resource=resource_objs)
    
    def render(self, data):
        """Renders results of a request.
        
        This method may return either a dictionary for a folder resource or an
        single object/basestring for an actual file/document resource.
        
        A folder dictionary contains ids and objects implementing IResource.
        
        This method should be overwritten by an inheriting class in order to
        further validate and format the output of this document.
        """
        return data
