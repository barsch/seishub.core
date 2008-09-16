# -*- coding: utf-8 -*-

import string, StringIO

from twisted.web import http
from urllib import unquote

from seishub.core import SeisHubError
from seishub.util.text import isInteger
from seishub.xmldb.errors import GetResourceError, ResourceDeletedError


class RequestError(SeisHubError):
    pass


class Processor:
    """General class for processing a resource request used by services, like
    REST and SFTP."""
    
    package_id = None
    resourcetype_id = None
    resource_id = None
    
    def __init__(self, env):
        self.env = env
        # fetch all package ids in alphabetical order
        self.package_ids = list(self.env.registry.packages)
        # fetch all mapping URLs
        self.mapping_urls = dict(self.env.registry.mappers)
        # response code and header for a request
        self.response_code = http.OK
        self.response_header = {}
        # set content
        self.content = StringIO.StringIO()
    
    def process(self):
        """Working through the process chain."""
        # post process self.path
        self.postpath = filter(len, map(unquote,
                                        string.split(self.path[1:], '/')))
        # check if correct method
        self.method = self.method.upper()
        if self.method == 'GET':
            return self._processGET()
        elif self.method == 'POST':
            return self._processPOST()
        elif self.method == 'PUT':
            return self._processPUT()
        elif self.method == 'DELETE':
            return self._processDELETE()
        raise RequestError(http.NOT_ALLOWED)
    
    def _processGET(self):
        """Working through the GET process chain."""
        # test if plain root node
        if len(self.postpath)==0:
            return self._processRoot()
        
        # test if root property
        if self.postpath[0].startswith('.'):
            return self._processRootProperty(self.postpath[0:])
        
        # test if it fits to a valid mapping
        if self.env.registry.mappers.get(self.path, self.method):
            return self._processMapping()
        
        # test if package at all
        if self.postpath[0] not in self.package_ids:
            raise RequestError(http.NOT_FOUND)
        
        ### from here on we have a valid package_id
        package_id = self.postpath[0]
        self.package_id = package_id
        # test if only package is requested
        if len(self.postpath)==1:
            return self._processPackage(package_id)
        # test if package property
        if self.postpath[1].startswith('.'):
            return self._processPackageProperty(package_id, self.postpath[1:])
        # test if package alias
        if self.postpath[1].startswith('@'):
            return self._processAlias(package_id, None, self.postpath[1:])
        # test if valid resource type at all
        if not self._checkResourceType(package_id, self.postpath[1]):
            raise RequestError(http.NOT_FOUND)
        
        ### from here on we can rely on a valid resourcetype_id
        resourcetype_id = self.postpath[1]
        self.resourcetype_id = resourcetype_id
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
        # test if a resource at all
        if not isInteger(self.postpath[2]):
            raise RequestError(http.NOT_FOUND)
        
        ### from here on we can rely on a valid resource_id
        resource_id = self.postpath[2]
        self.resource_id = resource_id
        # test if only resource is requested
        if len(self.postpath)==3:
            return self._getResource(package_id, resourcetype_id, resource_id)
        # test if resource property
        if self.postpath[3].startswith('.'):
            return self._processResourceProperty(package_id, 
                                                 resourcetype_id,
                                                 resource_id, 
                                                 None,
                                                 self.postpath[4:])
        # test if a version controlled resource at all
        if not isInteger(self.postpath[3]):
            raise RequestError(http.NOT_FOUND)
        
        ### from here on we can rely on a valid version_id
        version_id = self.postpath[3]
        # test if only version controlled resource is requested
        if len(self.postpath)==4:
            return self._getResource(package_id, resourcetype_id, resource_id,
                                     version_id)
        # test if resource property
        if self.postpath[3].startswith('.'):
            return self._processResourceProperty(package_id, 
                                                 resourcetype_id,
                                                 resource_id,
                                                 version_id,
                                                 self.postpath[4:])
        raise RequestError(http.NOT_FOUND)
    
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
        via user defined mapping."""
        # test if it fits to a valid mapping
        if self.env.registry.mappers.get(self.path, self.method):
            return self._processMapping()
        # test if the request was called in a resource type directory 
        if len(self.postpath)==2:
            if self._checkResourceType(self.postpath[0], self.postpath[1]):
                res = self._addResource(self.postpath[0], self.postpath[1])
                self.response_code = http.CREATED
                self.response_header['Location'] = str(res)
                return ''
        raise RequestError(http.FORBIDDEN)
    
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
        user defined mapping."""
        # test if it fits to a valid mapping
        if self.env.registry.mappers.get(self.path, self.method):
            return self._processMapping()
        # test if the request was called on a resource 
        if len(self.postpath)==3 and isInteger(self.postpath[2]):
            if self._checkResourceType(self.postpath[0], self.postpath[1]):
                self._modifyResource(self.postpath[0],
                                     self.postpath[1],
                                     self.postpath[2])
                self.response_code = http.NO_CONTENT
                return ''
        raise RequestError(http.FORBIDDEN)
    
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
        a user defined mapping."""
        # test if it fits to a valid mapping
        if self.env.registry.mappers.get(self.path, self.method):
            return self._processMapping()
        # test if the request was called on a resource 
        if len(self.postpath)==3 and isInteger(self.postpath[2]):
            if self._checkResourceType(self.postpath[0], self.postpath[1]):
                self._deleteResource(self.postpath[0],
                                     self.postpath[1],
                                     self.postpath[2])
                self.response_code = http.NO_CONTENT
                return ''
        raise RequestError(http.FORBIDDEN)
    
    def _checkResourceType(self, package_id, resourcetype_id):
        """Returns True if the given resource type exists in the package."""
        if package_id in self.package_ids:
            resourcetypes = self.env.registry.getResourceTypes(package_id)
            resourcetypes = resourcetypes.keys()
            if resourcetype_id in resourcetypes:
                return True
        return False
    
    def _addBaseToList(self, base='/', items=[]):
        """Adds a base path to each single element of a list."""
        if not base.startswith('/'):
            base = '/' + base
        if not base.endswith('/'):
            base = base + '/'
        return [base + i for i in items]
    
    def _formatPathList(self, items=[], level=0):
        """Returns a list of unique paths cut at a certain level."""
        data = {}
        for item in items:
            temp = '/'.join(item.split('/')[0:level+1])
            data[temp] = temp;
        data=data.keys()
        data.sort()
        return data
    
    def _processRoot(self):
        """The root element can be only accessed via the GET method and shows 
        only a list of all available packages, root mappings and properties."""
        package_ids = self._addBaseToList('/', self.package_ids)
        # get all root mappings not starting with a package name
        def notPackageMapping(item):
            parts = item.split('/')
            if parts[1] in self.package_ids:
                return False
            return True
        mapping_ids = filter(notPackageMapping, self.mapping_urls.keys())
        mapping_ids = self._formatPathList(mapping_ids, 1)
        # XXX: missing yet
        property_ids = []
        return self.renderResourceList(package=package_ids, 
                                       mapping=mapping_ids,
                                       property=property_ids)
    
    def _processRootProperty(self, property_id=[]):
        # XXX: missing yet
        raise NotImplementedError
    
    def _processPackage(self, package_id):
        """Request on a package root. Now we search for all allowed sub types 
        of this package (e.g., resource types, package aliases and mappings) 
        and return them as a resource list."""
        # fetch resource types
        resourcetype_ids = self.env.registry.resourcetypes[package_id]
        resourcetype_ids.sort()
        resourcetype_ids = self._addBaseToList(package_id, resourcetype_ids)
        # fetch package aliases
        aliases = self.env.registry.aliases.get(package_id)
        alias_ids = [str(alias) for alias in aliases]
        alias_ids.sort()
        # fetch all mappings in this package, not being a resource type
        mapping_ids = []
        for url in self.mapping_urls.keys():
            if not url.startswith('/' + package_id + '/'):
                continue
            parts = url.split('/')
            if parts[2] in self.env.registry.resourcetypes[package_id]:
                continue
            mapping_ids.append(url)
        # special properties
        # XXX: missing yet
        property_ids = []
        property_ids.sort()
        return self.renderResourceList(alias=alias_ids,
                                       resourcetype=resourcetype_ids,
                                       mapping=mapping_ids,
                                       property=property_ids)
    
    def _processPackageProperty(self, package_id, property_id):
        # XXX: missing yet
        raise NotImplementedError
    
    def _processResourceType(self, package_id, resourcetype_id):
        """Request on a resource type root of a package. Now we search for 
        resource type aliases, indexes or package mappings defined by the user.
        Also we add a few fixed aliases, e.g. '.all'."""
        # fetch resource type aliases
        aliases = self.env.registry.aliases.get(package_id, resourcetype_id)
        alias_ids = [str(alias) for alias in aliases]
        alias_ids.sort()
        # fetch all mappings in this package and resource type
        mapping_ids = [url for url in self.mapping_urls.keys() 
                       if url.startswith('/' + package_id + '/' + \
                                         resourcetype_id + '/')]
        # fetch indexes
        indexes = self.env.catalog.listIndexes(package_id, resourcetype_id)
        index_ids = [str(i) for i in indexes]
        index_ids.sort()
        # special properties
        property_ids = ['.all']
        property_ids.sort()
        property_ids = self._addBaseToList(package_id + '/' + resourcetype_id, 
                                           property_ids)
        return self.renderResourceList(property=property_ids,
                                       alias=alias_ids,
                                       mapping=mapping_ids,
                                       index=index_ids)
    
    def _processResourceTypeProperty(self, package_id, resourcetype_id,
                                     property_id):
        """Property request on a resource type."""
        
        if property_id[0]=='.all':
            res = self.env.catalog.getResourceList(package_id, resourcetype_id)
            resource_ids = [str(r) for r in res]
            return self.renderResourceList(resource=resource_ids)
        else:
            raise RequestError(http.NOT_FOUND)
    
    def _processMapping(self):
        mapper = self.env.registry.mappers.get(url=self.path, 
                                               method=self.method) 
        if not mapper or len(mapper)<1:
            raise RequestError(http.NOT_IMPLEMENTED)
        # XXX: is this possible anymore??
        # only use first found object, but warn if multiple implementations
        #if len(mapper)>1:
        #    self.log.error('Multiple %s mappings found for %s' % 
        #                   (self.method, self.path))
        func = getattr(mapper[0], 'process'+self.method)
        if not func:
            raise RequestError(http.NOT_IMPLEMENTED)
        #XXX: error handling missing yet
        result = func(self)
        # test if basestring -> could be a resource
        if isinstance(result, basestring):
            return self.renderResource(result)
        # result must be a dictionary with either mapping or resource entries
        if not isinstance(result, dict):
            raise RequestError(http.INTERNAL_SERVER_ERROR)
        mappings = result.get('mapping', [])
        resources = result.get('resource', [])
        return self.renderResourceList(mapping=mappings, resource=resources)
    
    def _processAlias(self, package_id, resourcetype_id, alias):
        """Generates a list of resources from an alias query."""
        # if alias > 1 - may be an indirect resource request - SFTP problem
        if len(alias)>1:
            # XXX: missing yet
            raise NotImplementedError
        # remove leading @
        alias_id = alias[0][1:]
        # fetch alias
        aliases = self.env.registry.aliases.get(package_id, resourcetype_id,
                                                alias_id)
        try:
            res = self.env.catalog.query(aliases[0].getQuery())
        except Exception, e:
            self.env.log.error(e)
            raise RequestError(http.INTERNAL_SERVER_ERROR)
            return
        else:
            resource_ids = [str(r) for r in res]
            resource_ids.sort()
            return self.renderResourceList(resource=resource_ids)
    
    def _processResourceProperty(self, package_id, resourcetype_id, 
                                 resource_id, version_id, property_id):
        # XXX: missing yet
        raise NotImplementedError
    
    def _getResource(self, package_id, resourcetype_id, resource_id, 
                     version_id=None):
        """Fetches the content of an existing resource.
        
        @see: http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.4.1
        for all possible error codes.
        """
        try:
            result = self.env.catalog.getResource(package_id,
                                                  resourcetype_id,
                                                  resource_id,
                                                  version_id)
        # XXX: 401 Unauthorized
        # XXX: 409 Conflict/415 Unsupported Media Type -> XSD not valid - here we need additional info why
        except GetResourceError, e:
            # 404 Not Found
            self.env.log.debug(e)
            raise RequestError(http.NOT_FOUND)
        except ResourceDeletedError, e:
            # 410 Gone
            self.env.log.debug(e)
            raise RequestError(http.GONE)
        except Exception, e:
            # 500 Internal Server Error
            self.env.log.error(e)
            raise RequestError(http.INTERNAL_SERVER_ERROR)
        else:
            # return resource content
            return result.document.data
    
    def _modifyResource(self, package_id, resourcetype_id, resource_id):
        """Modifies the content of an existing resource."""
        try:
            self.env.catalog.modifyResource(package_id,
                                            resourcetype_id,
                                            resource_id,
                                            self.content.read())
        # XXX: fetch all kind of exception types and return to clients
        except Exception, e:
            self.env.log.error(e)
            print e
            raise RequestError(http.INTERNAL_SERVER_ERROR)
    
    def _addResource(self, package_id, resourcetype_id):
        """Adds a new resource."""
        try:
            res = self.env.catalog.addResource(package_id, resourcetype_id,
                                               self.content.read())
        # XXX: fetch all kind of exception types and return to clients
        except Exception, e:
            self.env.log.error(e)
            raise RequestError(http.INTERNAL_SERVER_ERROR)
        else:
            return res
    
    def _deleteResource(self, package_id, resourcetype_id, resource_id):
        """Deletes a resource."""
        try:
            self.env.catalog.deleteResource(package_id,
                                            resourcetype_id,
                                            resource_id)
        # XXX: fetch all kind of exception types and return to clients
        except Exception, e:
            self.env.log.error(e)
            raise RequestError(http.INTERNAL_SERVER_ERROR)
    
    def renderResource(self, data):
        """
        Resource handler. Returns a content of this resource as string.
        
        This method should be overwritten by the inheriting class in order to
        further validate and format the output of this document.
        """
        return data
    
    def renderResourceList(self, **kwargs):
        """Resource list handler. Here we return a dict of objects. Each object
        contains a list of valid url's, e.g. {'package':['/quakeml','/resp']}.
        
        This method should be overwritten by the inheriting class in order to
        further validate and format the output of this resource list."""
        return kwargs