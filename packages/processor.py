# -*- coding: utf-8 -*-

from StringIO import StringIO

from twisted.web import http

from seishub.core import SeisHubError
from seishub.util.list import unique
from seishub.util.text import isInteger
from seishub.util.path import splitPath
from seishub.util.xml import addXMLDeclaration 
from seishub.xmldb.errors import GetResourceError, ResourceDeletedError


# @see: http://www.boutell.com/newfaq/misc/urllength.html
MAX_URI_LENGTH = 1000

PUT = 'PUT'
GET = 'GET'
POST = 'POST'
DELETE = 'DELETE'
MOVE = 'MOVE'

ALLOWED_HTTP_METHODS = [GET, PUT, POST, DELETE, MOVE]
NOT_IMPLEMENTED_HTTP_METHODS = ['TRACE', 'OPTIONS', 'COPY']


class ProcessorError(SeisHubError):
    """The processor error class."""
    
    def __init__(self, code, message=''):
        SeisHubError.__init__(self)
        self.code = code
        self.message = message or http.RESPONSES.get(code, '')
    
    def __str__(self):
        return 'ProcessorError %s: %s' % (self.code, self.message)


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
        # set content
        self.content = StringIO()
        self.data = StringIO()
    
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
            raise ProcessorError(http.REQUEST_URI_TOO_LONG)
        # post process self.path
        self.postpath = splitPath(self.path)
        self.postpath_firstchar = [pp[0] for pp in self.postpath]
        
        # we like upper case method names
        self.method = self.method.upper()
        # check for valid but not implemented methods
        if self.method in NOT_IMPLEMENTED_HTTP_METHODS:
            raise ProcessorError(http.NOT_IMPLEMENTED)
        # check for valid methods
        if self.method not in ALLOWED_HTTP_METHODS:
            raise ProcessorError(http.NOT_ALLOWED)
        
        # read content
        self.content.seek(0)
        self.data=self.content.read()
        
        # check if alias
        if '@' in self.postpath_firstchar:
            return self._processAlias()
        # check if property
        if '.' in self.postpath_firstchar:
            return self._processProperty()
        # check if resource
        if len(self.postpath)>=3 and self.postpath[1]=='xml':
            if self.env.registry.isResourceTypeId(self.postpath[0], 
                                                  self.postpath[2]):
                return self._processResource()
        # more GET processing
        if self.method==GET:
            # check if root GET request
            if len(self.postpath)==0:
                return self._getRoot()
            # check if package GET request
            if len(self.postpath)==1:
                if self.env.registry.isPackageId(self.postpath[0]):
                    return self._getPackage(self.postpath[0])
            # check if resource types XML directory
            if len(self.postpath)==2 and self.postpath[1]=='xml':
                if self.env.registry.isPackageId(self.postpath[0]):
                    return self._getResourceTypes(self.postpath[0])
        # test if it fits directly to a valid mapping
        if self.env.registry.mappers.get(self.path, self.method):
            return self._processMapping()
        #import pdb;pdb.set_trace()
        #XXX: finally it could be a sub path of a mapping
        return self._checkForMappingSubPath()
        raise ProcessorError(http.FORBIDDEN)
    
    def _processResource(self):
        """Process a resource request."""
        # check for method
        if self.method == GET:
            # a resource type directory
            if len(self.postpath)==3:
                return self._getResourceType(self.postpath[0], 
                                             self.postpath[2])
            # a non version controlled resource
            if len(self.postpath)==4:
                return self._getResource(self.postpath[0], 
                                         self.postpath[2],
                                         self.postpath[3])
            # a version controlled resource
            if len(self.postpath)==5 and isInteger(self.postpath[4]):
                return self._getResource(self.postpath[0], 
                                         self.postpath[2],
                                         self.postpath[3],
                                         self.postpath[4])
        elif self.method == POST and len(self.postpath)==4:
            return self._modifyResource(self.postpath[0], 
                                        self.postpath[2],
                                        self.postpath[3])
        elif self.method == PUT:
            # without a given name
            if len(self.postpath)==3:
                return self._createResource(self.postpath[0], 
                                            self.postpath[2])
            # with a given name
            if len(self.postpath)==4:
                return self._createResource(self.postpath[0], 
                                            self.postpath[2],
                                            self.postpath[3])
        elif self.method == DELETE and len(self.postpath)==4:
            return self._deleteResource(self.postpath[0], 
                                        self.postpath[2],
                                        self.postpath[3])
        elif self.method == MOVE and len(self.postpath)==4:
            return self._moveResource(self.postpath[0], 
                                      self.postpath[2],
                                      self.postpath[3])
        raise ProcessorError(http.FORBIDDEN)
    
    def _processProperty(self):
        """Process a property request."""
        # XXX: missing yet
        raise NotImplementedError
    
    def _processMapping(self):
        """Process a mapping request. 
        
        The result a HTTP GET request is either a basestring or unicode object 
        containing a XML resource document or a dictionary consisting of 
        further mappings and resource entries. All other HTTP methods return 
        nothing, but status code and document location.
        
        Errors should be handled in the user-defined mapping functions by 
        raising a ProcessError with an proper error code and message defined
        in twisted.web.http.
        """
        if not self.path:
            return
        mapper = self.env.registry.mappers.get(url=self.path, 
                                               method=self.method) 
        if not mapper:
            raise ProcessorError(http.NOT_FOUND, 
                                 "There is no %s mapper defined for %s." % + \
                                 (self.method, self.path))
        # only use first found object, but warn if multiple implementations
        #if len(mapper)>1:
        #    self.log.error('Multiple %s mappings found for %s' % 
        #                   (self.method, self.path))
        func = getattr(mapper[0], 'process'+self.method)
        if not func:
            raise ProcessorError(http.NOT_IMPLEMENTED, "Function process%s" + \
                                 "is not implemented." % self.method)
        # general error handling should be done by the mapper functions
        try:
            result = func(self)
        except Exception, e:
            if isinstance(e, ProcessorError):
                raise
            else:
                raise ProcessorError(http.INTERNAL_SERVER_ERROR, 
                                     "Error processing %s mapper for %s." % + \
                                     (self.method, self.path))
        if self.method in [DELETE, POST]:
            self.response_code = http.NO_CONTENT
            return ''
        if self.method==PUT :
            self.response_code = http.CREATED
            self.response_header['Location'] = str(result)
            return ''
        # test if basestring -> could be a resource
        if isinstance(result, basestring):
            return self.renderResource(result)
        # result must be a dictionary with either mapping or resource entries
        if not isinstance(result, dict):
            raise ProcessorError(http.INTERNAL_SERVER_ERROR, 
                                 "A mapper must return a dictionary " + \
                                 "containing mapping or resource elements.")
        mapping_urls = result.get('mapping', [])
        resource_urls = result.get('resource', [])
        return self.renderResourceList(mapping=mapping_urls, 
                                       resource=resource_urls)
    
    def _processAlias(self, package_id, resourcetype_id, alias):
        """Process an alias request."""
        # if alias > 1 - may be an indirect resource request - SFTP problem
        if len(alias)>1:
            # XXX: missing yet
            raise ProcessorError(http.NOT_IMPLEMENTED)
        # remove leading @
        alias_id = alias[0][1:]
        # fetch alias
        aliases = self.env.registry.aliases.get(package_id, resourcetype_id,
                                                alias_id)
        try:
            resource_objs = self.env.catalog.query(aliases[0].getQuery())
        except Exception, e:
            self.env.log.error(e)
            raise ProcessorError(http.INTERNAL_SERVER_ERROR, e)
            return
        else:
            return self.renderResourceList(resource=resource_objs)
    
    def _getResource(self, package_id, resourcetype_id, name, revision=None):
        """Fetches the content of an existing resource.
        
        @see: http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.4.1
        for all possible error codes.
        """
        try:
            result = self.env.catalog.getResource(package_id,
                                                  resourcetype_id,
                                                  name,
                                                  revision)
        # XXX: 401 Unauthorized
        # XXX: 409 Conflict/415 Unsupported Media Type 
        # XSD not valid - here we need additional info why
        except GetResourceError, e:
            # 404 Not Found
            self.env.log.debug(e)
            raise ProcessorError(http.NOT_FOUND, e)
        except ResourceDeletedError, e:
            # 410 Gone
            self.env.log.debug(e)
            raise ProcessorError(http.GONE, e)
        except Exception, e:
            # 500 Internal Server Error
            self.env.log.error(e)
            raise ProcessorError(http.INTERNAL_SERVER_ERROR, e)
        else:
            data = result.document.data
            # ensure we return a utf-8 encoded string not an unicode object
            if isinstance(data, unicode):
                data = data.encode('utf-8')
            # set XML declaration inclusive UTF-8 encoding string
            if not data.startswith('<xml'):
                data = addXMLDeclaration(data, 'utf-8')
            return data
    
    def _createResource(self, package_id, resourcetype_id, name=None):
        """Process a resource creation request.
        
        @see: http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.6
        @see: http://thoughtpad.net/alan-dean/http-headers-status.gif
        
        "The PUT method requests that the enclosed entity be stored under the 
        supplied Request-URI. If the Request-URI refers to an already existing 
        resource, the enclosed entity SHOULD be considered as a modified 
        version of the one residing on the origin server. If the Request-URI 
        does not point to an existing resource, and that URI is capable of 
        being defined as a new resource by the requesting user agent, the 
        server can create the resource with that URI. If a new resource is 
        created, the origin server MUST inform the user agent via the 201 
        (Created) response. If an existing resource is modified, either the 
        200 (OK) or 204 (No Content) response codes SHOULD be sent to indicate 
        successful completion of the request. If the resource could not be 
        created or modified with the Request-URI, an appropriate error response
        SHOULD be given that reflects the nature of the problem." 
        
        Adding documents can be done directly on an existing resource type or 
        via user defined mapping.
        """
        # seishub directory is not directly changeable
        if package_id=='seishub':
            raise ProcessorError(http.FORBIDDEN, 
                                 "SeisHub resources may not be added " + \
                                 "directly.")
        # add a new resource
        try:
            res = self.env.catalog.addResource(package_id, 
                                               resourcetype_id,
                                               self.data, 
                                               name=name)
        except Exception, e:
            self.env.log.error(e)
            raise ProcessorError(http.INTERNAL_SERVER_ERROR, e)
        # resource created - set status code and location header
        self.response_code = http.CREATED
        self.response_header['Location'] = self.env.getRestUrl() + str(res)
        return ''
    
    def _modifyResource(self, package_id, resourcetype_id, name):
        """Processes a resource modification request.
        
        @see: http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.5
        
        "The POST method is used to request that the origin server accept the 
        entity enclosed in the request as a new subordinate of the resource 
        identified by the Request-URI in the Request-Line.
        
        The action performed by the POST method might not result in a resource 
        that can be identified by a URI. In this case, either 200 (OK) or 204 
        (No Content) is the appropriate response status, depending on whether 
        or not the response includes an entity that describes the result. If a 
        resource has been created on the origin server, the response SHOULD be 
        201 (Created) and contain an entity which describes the status of the 
        request and refers to the new resource, and a Location header." 
        
        Modifying a document always needs a valid path to a resource or uses a 
        user defined mapping.
        """
        # test if the request was called in a resource type directory 
        if len(self.postpath)!=4:
            raise ProcessorError(http.FORBIDDEN, 
                                 "Modifying resources is not allowed here.")
        # seishub directory is not directly changeable
        if package_id=='seishub':
            raise ProcessorError(http.FORBIDDEN, "SeisHub resources may not "
                                 "be modified directly.")
        # modify resource
        try:
            self.env.catalog.modifyResource(package_id,
                                            resourcetype_id,
                                            name,
                                            self.data)
        except Exception, e:
            self.env.log.error(e)
            raise ProcessorError(http.INTERNAL_SERVER_ERROR, e)
        # resource successfully modified - set status code
        self.response_code = http.NO_CONTENT
        return ''
    
    def _deleteResource(self, package_id, resourcetype_id, name):
        """Processes a resource deletion request.
        
        @see: http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.7
        
        "The DELETE method requests that the server deletes the resource 
        identified by the given request URI. 
        
        A successful response SHOULD be 200 (OK) if the response includes an 
        entity describing the status, 202 (Accepted) if the action has not yet 
        been enacted, or 204 (No Content) if the action has been enacted but 
        the response does not include an entity."
        
        Deleting a document always needs a valid path to a resource or may use 
        a user defined mapping.
        """
        # test if the request was called in a resource type directory 
        if len(self.postpath)!=4:
            raise ProcessorError(http.FORBIDDEN, 
                                 "Deleting resources is not allowed here.")
        # resource in SeisHub directory are not directly deletable
        if package_id=='seishub':
            raise ProcessorError(http.FORBIDDEN, "SeisHub resources may not "
                                 "be deleted directly.")
        # delete resource
        try:
            self.env.catalog.deleteResource(package_id,
                                            resourcetype_id,
                                            name)
        except GetResourceError, e:
            raise ProcessorError(http.NOT_FOUND, e)
        except Exception, e:
            self.env.log.error(e)
            raise ProcessorError(http.INTERNAL_SERVER_ERROR, e)
        # resource deleted - set status code
        self.response_code = http.NO_CONTENT
        return ''
    
    def _moveResource(self, package_id, resourcetype_id, name):
        """Processes a resource move/rename request.
        
        @see: http://msdn.microsoft.com/en-us/library/aa142926(EXCHG.65).aspx
        """
        # test if the request was called in a resource type directory 
        if len(self.postpath) != 4:
            raise ProcessorError(http.FORBIDDEN, 
                                 "Moving resources is not allowed here.")
        # seishub directory is not directly changeable
        if package_id=='seishub':
            raise ProcessorError(http.FORBIDDEN, "SeisHub resources may not "
                                 "be moved directly.")
        # test if destination is set
        destination = self.received_headers.get('Destination', False) 
        if not destination:
            raise ProcessorError(http.BAD_REQUEST,
                                 "Expected a destination header.")
        if not destination.startswith(self.env.getRestUrl()):
            if destination.startswith('http'):
                raise ProcessorError(http.BAD_GATEWAY, "Destination URI is "
                                     "located on a different server.")
            raise ProcessorError(http.BAD_REQUEST,
                                 "Expected a complete destination path.")
        # test size of destination URI
        if len(destination)>=MAX_URI_LENGTH:
            raise ProcessorError(http.REQUEST_URI_TOO_LONG, 
                                 "Destination URI is to long.")
        # strip host
        destination = destination[len(self.env.getRestUrl()):]
        # source uri and destination uri must not be the same value
        destination_part = splitPath(destination)
        if destination_part == self.postpath:
            raise ProcessorError(http.FORBIDDEN, "Source uri and destination "
                                 "uri must not be the same value.")
        # test if valid destination path
        if len(destination_part)!=4:
            raise ProcessorError(http.FORBIDDEN,
                                 "Destination %s not allowed." % destination)
        # test destination path
        if destination_part[0:3] != self.postpath[0:3]:
            raise ProcessorError(http.FORBIDDEN, "You may only move resources "
                                 "within the same resource type directory.")
        # moves or rename resource
        try:
            self.env.catalog.moveResource(package_id,
                                          resourcetype_id,
                                          name, 
                                          destination_part[3])
        # XXX: BUG - see ticket #61
        # processor should raise FORBIDDEN if resource already exists
        except Exception, e:
            self.env.log.error(e)
            raise ProcessorError(http.INTERNAL_SERVER_ERROR, e)
        # on successful creation - set status code and location header
        self.response_code = http.CREATED
        self.response_header['Location'] = self.env.getRestUrl() + destination
        return ''
    
    def _getRoot(self):
        """GET request on the root element of SeisHub.
        
        The root element shows a list of all available packages, root mappings 
        and properties.
        """
        package_urls = self.env.registry.getPackageURLs()
        # get all root mappings not starting with a package name
        urls = self.env.registry.mappers.getMappings(method=self.method)
        mapping_urls = []
        for url in urls:
            parts = url.split('/')
            if parts[1] in self.env.registry.getPackageIds():
                continue
            mapping_urls.append('/'.join(parts[0:2]))
        mapping_urls=unique(mapping_urls)
        mapping_urls.sort()
        # XXX: missing yet
        property_urls = []
        return self.renderResourceList(package=package_urls, 
                                       mapping=mapping_urls,
                                       property=property_urls)
    
    def _getPackage(self, package_id):
        """GET request on a package directory. 
        
        Now we search for all allowed sub types of this package (e.g., 
        package aliases and mappings) and return a resource 
        list in form of a dictionary. Also we append the special resource types
        directory xml.
        """
        # fetch package aliases
        aliases = self.env.registry.aliases.get(package_id)
        alias_urls = [str(alias) for alias in aliases]
        alias_urls.sort()
        # fetch all package mappings
        urls = self.env.registry.mappers.getMappings(method=self.method,
                                                     base=self.path)
        mapping_urls = []
        for url in urls:
            parts = url.split('/')
            mapping_urls.append('/'.join(parts[0:3]))
        mapping_urls=unique(mapping_urls)
        # fetch all package properties
        # XXX: missing yet
        property_urls = []
        # special xml directory
        resourcetype_urls = ['/' + package_id + '/xml',]
        return self.renderResourceList(alias=alias_urls,
                                       mapping=mapping_urls,
                                       property=property_urls,
                                       resourcetype=resourcetype_urls)
    
    def _getResourceTypes(self, package_id):
        """GET request on the resource types XML directory.
        
        This resource list only contains all package specific resource types.
        """
        # fetch all resource types of this package
        resourcetype_urls = self.env.registry.getResourceTypeURLs(package_id)
        return self.renderResourceList(resourcetype=resourcetype_urls)
    
    def _getResourceType(self, package_id, resourcetype_id):
        """GET request on a single resource type root of a package. 
        
        Now we search for resource type aliases or indexes defined by the user.
        """
        # fetch resource type aliases
        aliases = self.env.registry.aliases.get(package_id, resourcetype_id)
        alias_urls = [str(alias) for alias in aliases]
        alias_urls.sort()
        # fetch indexes
        indexes = self.env.catalog.listIndexes(package_id, resourcetype_id)
        index_urls = [str(i) for i in indexes]
        index_urls.sort()
        # fetch all resource type properties
        # XXX: missing yet
        property_urls = []
        # fetch all resource objects
        resource_objs = self.env.catalog.getResourceList(package_id, 
                                                         resourcetype_id)
        return self.renderResourceList(property=property_urls,
                                       alias=alias_urls,
                                       index=index_urls,
                                       resource=resource_objs)
    
    def _checkForMappingSubPath(self, uris=None):
        """This method checks if we can find at least some sub paths of 
        registered mappings and returns it as resource list.
        """
        if not uris:
            uris = self.env.registry.mappers.getMappings(method=self.method,
                                                         base=self.path)
            if not uris:
                raise ProcessorError(http.NOT_FOUND)
        pos = len(self.postpath)+2
        mapping_ids = ['/'.join(uri.split('/')[0:pos]) for uri in uris]
        return self.renderResourceList(mapping=mapping_ids)
    
    def renderResource(self, data):
        """Resource handler. Returns content of this resource as utf-8 string.
        
        This method should be overwritten by the inheriting class in order to
        further validate and format the output of this document.
        """
        return data
    
    def renderResourceList(self, **kwargs):
        """Resource list handler. 
        
        Here we return a dict of objects. Each object contains a list of valid 
        absolute URI's, e.g.
        {'package': ['/quakeml', '/resp'], 'properties': ['/.version']}.
        
        Exception of this rule above is the list of resources as they are 
        returned as full resource objects, e.g. 
        {'resource': [<seishub.xmldb.resource.Resource object at 0x0365EA90>, 
                      <seishub.xmldb.resource.Resource object at 0x0365EA91>]}.
        
        This method should be overwritten by the inheriting class in order to
        further validate and format the output of this resource list.
        """
        return kwargs