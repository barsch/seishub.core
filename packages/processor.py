# -*- coding: utf-8 -*-

from StringIO import StringIO

from twisted.web import http

from seishub.core import SeisHubError
from seishub.util.list import unique
from seishub.util.text import isInteger
from seishub.util.path import splitPath
from seishub.xmldb.errors import GetResourceError, ResourceDeletedError


PUT = 'PUT'
GET = 'GET'
POST = 'POST'
DELETE = 'DELETE'
MOVE = 'MOVE'


class ProcessorError(SeisHubError):
    
    def __init__(self, code, message=''):
        SeisHubError.__init__(self)
        self.code = code
        self.message = message or http.RESPONSES.get(code, '')
    
    def __str__(self):
        return 'ProcessorError %s: %s' % (self.code, self.message)


class Processor:
    """General class for processing a resource request used by services, like
    REST and SFTP.
    """
    
    def __init__(self, env):
        self.env = env
        # response code and header for a request
        self.response_code = http.OK
        self.response_header = {}
        # set content
        self.content = StringIO()
        self.data = StringIO()
    
    def run(self, method, path='/', content=None, received_headers={}):
        self.method = method
        self.path = path
        if content:
            self.content = content
        if received_headers:
            self.received_headers = received_headers
        return self.process()
    
    def process(self):
        """Working through the process chain."""
        # post process self.path
        self.postpath = splitPath(self.path)
        # check if correct method
        self.method = self.method.upper()
        # read content
        self.content.seek(0)
        self.data=self.content.read()
        if self.method == GET:
            return self._processGET()
        elif self.method == POST:
            return self._processPOST()
        elif self.method == PUT:
            return self._processPUT()
        elif self.method == DELETE:
            return self._processDELETE()
        elif self.method == MOVE:
            return self._processMOVE()
        raise ProcessorError(http.NOT_ALLOWED)
    
    def _processGET(self):
        """Working through the GET process chain."""
        # test if plain root node
        if len(self.postpath)==0:
            return self._processRoot()
        # test if root property
        if self.postpath[0].startswith('.'):
            return self._processRootProperty(self.postpath[0:])
        # test if root mapping
        if self.postpath[0].startswith('~'):
            return self._processMapping()
        
        ### from here on we have a valid package_id
        package_id = self.postpath[0]
        # test if valid package at all
        if not self.env.registry.isPackageId(package_id):
            raise ProcessorError(http.NOT_FOUND)
        # test if only package is requested
        if len(self.postpath)==1:
            return self._processPackage(package_id)
        # test if package property
        if self.postpath[1].startswith('.'):
            return self._processPackageProperty(package_id, self.postpath[1:])
        # test if package alias
        if self.postpath[1].startswith('@'):
            return self._processAlias(package_id, None, self.postpath[1:])
        # test if package mapping
        if self.postpath[1].startswith('~'):
            return self._processMapping()
        
        ### from here on we can rely on a valid resourcetype_id
        resourcetype_id = self.postpath[1]
        # test if valid resource type at all
        if not self.env.registry.isResourceTypeId(package_id, resourcetype_id):
            raise ProcessorError(http.NOT_FOUND)
        # test if only resource type is requested
        if len(self.postpath)==2:
            return self._processResourceType(package_id, resourcetype_id)
        # test if resource type property
        if self.postpath[2].startswith('.'):
            return self._processResourceTypeProperty(package_id, 
                                                     resourcetype_id, 
                                                     self.postpath[2:])
        # test if resource type alias
        if self.postpath[2].startswith('@'):
            return self._processAlias(package_id, resourcetype_id, 
                                      self.postpath[2:])
        # test if resource type mapper
        if self.postpath[2].startswith('~'):
            return self._processMapping()
        
        ### from here on we can rely on a valid resource_name
        resource_name = self.postpath[2]
        # test if only resource is requested
        if len(self.postpath)==3:
            return self._getResource(package_id, resourcetype_id, 
                                     resource_name)
        # test if resource property
        if self.postpath[3].startswith('.'):
            return self._processResourceProperty(package_id, 
                                                 resourcetype_id,
                                                 resource_name, 
                                                 None,
                                                 self.postpath[4:])
        # test if resource mapper
        if self.postpath[3].startswith('~'):
            return self._processMapping()
        
        ### from here on we can rely on a valid version_id
        version_id = self.postpath[3]
        # test if a version controlled resource at all
        if not isInteger(version_id):
            raise ProcessorError(http.NOT_FOUND)
        # test if only version controlled resource is requested
        if len(self.postpath)==4:
            return self._getResource(package_id, resourcetype_id, 
                                     resource_name, version_id)
        # test if version controlled resource property
        if self.postpath[3].startswith('.'):
            return self._processResourceProperty(package_id, 
                                                 resourcetype_id,
                                                 resource_name,
                                                 version_id,
                                                 self.postpath[4:])
        raise ProcessorError(http.NOT_FOUND)
    
    def _processPUT(self):
        """Process a resource creation request.
        
        @see: http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.6
        
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
        # test if it fits to a valid mapping
        if self.env.registry.mappers.get(self.path, self.method):
            return self._processMapping()
        # test if the request was called in a resource type directory 
        if not len(self.postpath) in [2, 3]:
            raise ProcessorError(http.FORBIDDEN, 
                                 "Adding resources is not allowed here.")
        # seishub directory is not directly changeable
        if self.postpath[0]=='seishub':
            raise ProcessorError(http.FORBIDDEN, 
                                 "SeisHub resources may not be added " + \
                                 "directly.")
        # only resource types are accepting PUTs
        if not self.env.registry.isResourceTypeId(self.postpath[0], 
                                                  self.postpath[1]):
            raise ProcessorError(http.FORBIDDEN,
                                 "Adding resources is not allowed here.")
        if len(self.postpath)==3:
            res = self._addResource(self.postpath[0], self.postpath[1], 
                                    self.postpath[2])
        else:
            res = self._addResource(self.postpath[0], self.postpath[1])
        # create resource
        
        self.response_code = http.CREATED
        self.response_header['Location'] = str(res)
        return ''
    
    def _processPOST(self):
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
        # test if it fits to a valid mapping
        if self.env.registry.mappers.get(self.path, self.method):
            return self._processMapping()
        # test if the request was called in a resource type directory 
        if len(self.postpath)!=3:
            raise ProcessorError(http.FORBIDDEN, 
                                 "Modifying resources is not allowed here.")
        # seishub directory is not directly changeable
        if self.postpath[0]=='seishub':
            raise ProcessorError(http.FORBIDDEN, 
                                 "SeisHub resources may not be modified " + \
                                 "directly.")
        # only resource types are accepting POSTs
        if not self.env.registry.isResourceTypeId(self.postpath[0], 
                                                  self.postpath[1]):
            raise ProcessorError(http.FORBIDDEN,
                                 "Modifying resources is not allowed here.")
        # modify resource
        self._modifyResource(self.postpath[0],
                             self.postpath[1],
                             self.postpath[2])
        self.response_code = http.NO_CONTENT
        return ''
    
    def _processDELETE(self):
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
        # test if it fits to a valid mapping
        if self.env.registry.mappers.get(self.path, self.method):
            return self._processMapping()
        # test if the request was called in a resource type directory 
        if len(self.postpath) not in (3, 4):
            raise ProcessorError(http.FORBIDDEN, 
                                 "Only resources may be deleted.")
        # seishub directory is not directly changeable
        if self.postpath[0]=='seishub':
            raise ProcessorError(http.FORBIDDEN, 
                                 "SeisHub resources may not be deleted " + \
                                 "directly.")
        # only resource types are accepted
        if not self.env.registry.isResourceTypeId(self.postpath[0], 
                                                  self.postpath[1]):
            raise ProcessorError(http.FORBIDDEN,
                                 "Only resources may be deleted.")
        # unversioned or version controlled resource
        if len(self.postpath) == 4:
            # test if version controlled resource
            rt = self.env.registry.getResourceType(self.postpath[0], 
                                                   self.postpath[1])
            if not rt.version_control:
                raise ProcessorError(http.FORBIDDEN)
            # deleting resource
            self._deleteResource(self.postpath[0],
                                 self.postpath[1],
                                 self.postpath[2],
                                 self.postpath[3])
        else:
            self._deleteResource(self.postpath[0],
                                 self.postpath[1],
                                 self.postpath[2])
        self.response_code = http.NO_CONTENT
        return ''
    
    def _processMOVE(self):
        """Processes a resource rename request.
        
        @see: http://msdn.microsoft.com/en-us/library/aa142926(EXCHG.65).aspx
        """
        # test if the request was called in a resource type directory 
        if len(self.postpath) != 3:
            raise ProcessorError(http.FORBIDDEN, 
                                 "Only resources may be renamed.")
        # seishub directory is not directly changeable
        if self.postpath[0]=='seishub':
            raise ProcessorError(http.FORBIDDEN, 
                                 "SeisHub resources may not be renamed " + \
                                 "directly.")
        # only resource types are accepted
        if not self.env.registry.isResourceTypeId(self.postpath[0], 
                                                  self.postpath[1]):
            raise ProcessorError(http.FORBIDDEN,
                                 "Only resources may be renamed.")
        # check if destination is set
        destination = self.received_headers.get('Destination', False) 
        if not destination:
            raise ProcessorError(http.INTERNAL_SERVER_ERROR,
                                 "Expected a destination header.")
        # destination must be an absolute path
        if not destination.startswith(self.env.getRestUrl()):
            raise ProcessorError(http.INTERNAL_SERVER_ERROR, "Destination " + \
                                 "header must be an absolute path.")
        destination = destination[len(self.env.getRestUrl()):]
        destination_part = destination.split('/')
        if len(destination_part)!=4 or \
           destination_part[1]!=self.postpath[0] or \
           destination_part[2]!=self.postpath[1]:
            raise ProcessorError(http.FORBIDDEN, "Destination " + \
                                 "%s is not allowed." % destination)
        self._moveResource(self.postpath[0],
                           self.postpath[1],
                           self.postpath[2], destination_part[3])
        self.response_code = http.CREATED
        return ''
    
    def _processRoot(self):
        """The root element can be only accessed via the GET method and shows 
        only a list of all available packages, root mappings and properties.
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
        property_urls = ['/.info']
        return self.renderResourceList(package=package_urls, 
                                       mapping=mapping_urls,
                                       property=property_urls)
    
    def _processRootProperty(self, property_id=[]):
        # XXX: missing yet
        raise NotImplementedError
    
    def _processPackage(self, package_id):
        """Request on a package root. Now we search for all allowed sub types 
        of this package (e.g., resource types, package aliases and mappings) 
        and return a resource list.
        """
        # fetch resource types
        resourcetype_urls = self.env.registry.getResourceTypeURLs(package_id)
        # fetch package aliases
        aliases = self.env.registry.aliases.get(package_id)
        alias_urls = [str(alias) for alias in aliases]
        alias_urls.sort()
        # fetch all mappings in this package, not being a resource type
        urls = self.env.registry.mappers.getMappings(method=self.method,
                                                     base=self.path)
        mapping_urls = []
        for url in urls:
            parts = url.split('/')
            if parts[2] in self.env.registry.getResourceTypeIds(package_id):
                continue
            mapping_urls.append('/'.join(parts[0:3]))
        mapping_urls=unique(mapping_urls)
        # special properties
        # XXX: missing yet
        property_urls = []
        property_urls.sort()
        return self.renderResourceList(alias=alias_urls,
                                       resourcetype=resourcetype_urls,
                                       mapping=mapping_urls,
                                       property=property_urls)
    
    def _processPackageProperty(self, package_id, property_id):
        # XXX: missing yet
        raise NotImplementedError
    
    def _processResourceType(self, package_id, resourcetype_id):
        """Request on a resource type root of a package. Now we search for 
        resource type aliases, indexes or package mappings defined by the user.
        """
        # fetch resource type aliases
        aliases = self.env.registry.aliases.get(package_id, resourcetype_id)
        alias_urls = [str(alias) for alias in aliases]
        alias_urls.sort()
        # fetch all mappings in this package and resource type
        urls = self.env.registry.mappers.getMappings(method=self.method,
                                                     base=self.path)
        mapping_urls = []
        for url in urls:
            parts = url.split('/')
            mapping_urls.append('/'.join(parts[0:4]))
        mapping_urls=unique(mapping_urls)
        # fetch indexes
        indexes = self.env.catalog.listIndexes(package_id, resourcetype_id)
        index_urls = [str(i) for i in indexes]
        index_urls.sort()
        # special properties
        # XXX: missing yet
        property_urls = []
        property_urls.sort()
        # fetching resource objects
        resource_objs = self.env.catalog.getResourceList(package_id, 
                                                         resourcetype_id)
        
        return self.renderResourceList(property=property_urls,
                                       alias=alias_urls,
                                       mapping=mapping_urls,
                                       index=index_urls,
                                       resource=resource_objs)
    
    def _processResourceTypeProperty(self, package_id, resourcetype_id,
                                     property_id):
        """Property request on a resource type."""
        # XXX: missing yet
        raise ProcessorError(http.NOT_IMPLEMENTED)
    
    def _checkForMappingSubPath(self):
        """This method checks if we can find at least some sub paths of 
        registered mappings and returns it as resource list.
        """
        urls = self.env.registry.mappers.getMappings(method=self.method,
                                                     base=self.path)
        if not urls:
            raise ProcessorError(http.NOT_FOUND)
        pos = len(self.postpath)+2
        mapping_ids = ['/'.join(url.split('/')[0:pos]) for url in urls]
        return self.renderResourceList(mapping=mapping_ids)
    
    def _processMapping(self):
        """Here we processing a registered mapping. 
        
        The result a HTTP GET request is either a basestring containing a XML
        resource document or a resource list consisting of further mappings and
        resource entries. All other HTTP mehtods return nothing, but status 
        code and document location.
        
        Errors should be handled in the user-defined mapping functions by 
        raising a ProcessError with an proper error code and message defined
        in twisted.web.http.
        """
        mapper = self.env.registry.mappers.get(url=self.path, 
                                               method=self.method) 
        if not mapper:
            raise ProcessorError(http.NOT_FOUND, 
                                 "There is no %s mapper defined for %s." % + \
                                 (self.method, self.path))
        # XXX: is this possible anymore??
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
            print e
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
        """Generates a list of resources from an alias query."""
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
            res = self.env.catalog.query(aliases[0].getQuery())
        except Exception, e:
            self.env.log.error(e)
            raise ProcessorError(http.INTERNAL_SERVER_ERROR, e)
            return
        else:
            resource_ids = [str(r) for r in res]
            resource_ids.sort()
            return self.renderResourceList(resource=resource_ids)
    
    def _processResourceProperty(self, package_id, resourcetype_id, 
                                 resource_id, version_id, property_id):
        # XXX: missing yet
        raise ProcessorError(http.NOT_IMPLEMENTED)
    
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
            # XXX: set utf-8 encoding header
            # return resource content
            return result.document.data.encode('utf-8')
    
    def _modifyResource(self, package_id, resourcetype_id, name):
        """Modifies the content of an existing resource."""
        try:
            self.env.catalog.modifyResource(package_id,
                                            resourcetype_id,
                                            name,
                                            self.data)
        # XXX: fetch all kind of exception types and return to clients
        except Exception, e:
            self.env.log.error(e)
            raise ProcessorError(http.INTERNAL_SERVER_ERROR, e)
    
    def _addResource(self, package_id, resourcetype_id, name=None):
        """Adds a new resource."""
        try:
            res = self.env.catalog.addResource(package_id, resourcetype_id,
                                               self.data, name=name)
        # XXX: fetch all kind of exception types and return to clients
        except Exception, e:
            self.env.log.error(e)
            raise ProcessorError(http.INTERNAL_SERVER_ERROR, e)
        else:
            return res
    
    def _deleteResource(self, package_id, resourcetype_id, name, 
                        revision=None):
        """Deletes a resource."""
        try:
            self.env.catalog.deleteResource(package_id,
                                            resourcetype_id,
                                            name,
                                            revision)
        # XXX: fetch all kind of exception types and return to clients
        except GetResourceError, e:
            raise ProcessorError(http.NOT_FOUND, e)
        except Exception, e:
            self.env.log.error(e)
            raise ProcessorError(http.INTERNAL_SERVER_ERROR, e)
    
    def _moveResource(self, package_id, resourcetype_id, oldname, newname):
        """Deletes a resource."""
        try:
            self.env.catalog.moveResource(package_id,
                                          resourcetype_id,
                                          oldname,
                                          newname)
        # XXX: fetch all kind of exception types and return to clients
        except Exception, e:
            self.env.log.error(e)
            raise ProcessorError(http.INTERNAL_SERVER_ERROR, e)
    
    def renderResource(self, data):
        """Resource handler. Returns a content of this resource as string.
        
        This method should be overwritten by the inheriting class in order to
        further validate and format the output of this document.
        """
        return data
    
    def renderResourceList(self, **kwargs):
        """Resource list handler. Here we return a dict of objects. Each object
        contains a list of valid url's, e.g. {'package':['/quakeml','/resp']}.
        
        This method should be overwritten by the inheriting class in order to
        further validate and format the output of this resource list.
        """
        return kwargs