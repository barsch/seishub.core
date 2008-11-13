# -*- coding: utf-8 -*-

from StringIO import StringIO

from twisted.web import http

from seishub.exceptions import SeisHubError, ForbiddenError, NotFoundError
from seishub.util.list import unique
from seishub.util.text import isInteger
from seishub.util.path import splitPath
from seishub.util.xml import addXMLDeclaration


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
            raise SeisHubError(code=http.REQUEST_URI_TOO_LONG)
        # post process self.path
        self.postpath = splitPath(self.path)
        self.postpath_firstchar = [pp[0] for pp in self.postpath]
        
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
        
        # check if alias
        if '@' in self.postpath_firstchar:
            return self._processAlias()
        # check if property
        if '.' in self.postpath_firstchar:
            return self._processProperty()
        # handle direct access to file system or XML resources
        if len(self.postpath)>=3:
            # check if XML resource
            if self.postpath[1]=='xml':
                if self.env.registry.isResourceTypeId(self.postpath[0], 
                                                      self.postpath[2]):
                    return self._processResource()
            # check if file system
            elif self.postpath[1]=='fs':
                if self._isFSDirectoryId(self.postpath[0], self.postpath[2]):
                    return self._processFileSystem()
        # more GET processing
        if self.method==GET:
            # check if root GET request
            if len(self.postpath)==0:
                return self._getRoot()
            # check if package GET request
            if len(self.postpath)==1:
                if self.env.registry.isPackageId(self.postpath[0]):
                    return self._getPackage(self.postpath[0])
            # check if root of XML or file system directories
            if len(self.postpath)==2:
                if self.env.registry.isPackageId(self.postpath[0]):
                    # check if XML resource directory
                    if self.postpath[1]=='xml':
                        return self._getResourceTypes(self.postpath[0])
                    # check if file system directory
                    elif self.postpath[1]=='fs':
                        return self._getFSDirectories(self.postpath[0])
        # test if it fits directly to a valid mapping
        if self.postpath and self.method in ALLOWED_MAPPER_METHODS:
            if self.env.registry.mappers.get(self.path, self.method):
                return self._processMapping()
        # finally it could be a sub path of a mapping
        if self.method==GET:
            return self._checkForMappingSubPath()
        raise ForbiddenError('This operation is not allowed.')
    
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
        raise ForbiddenError()
    
    def _processFileSystem(self):
        """Process a file system request."""
        # check for method
        if self.method == GET:
            if len(self.postpath)==3:
                return self._getFileSystem(self.postpath[0], 
                                           self.postpath[2])
            elif len(self.postpath)>3:
                return self._getFileSystem(self.postpath[0], 
                                           self.postpath[2],
                                           self.postpath[3:])
        raise ForbiddenError()
    
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
            msg = "There is no %s mapper defined for %s." % (self.method, 
                                                             self.path)
            raise SeisHubError(msg, code=http.NOT_FOUND)
        # only use first found object, but warn if multiple implementations
        if len(mapper)>1:
            self.log.warn('Multiple %s mappings found for %s' % 
                          (self.method, self.path))
        func = getattr(mapper[0], 'process'+self.method)
        if not func:
            msg = "Function process%s is not implemented." % (self.method)
            raise SeisHubError(msg, code=http.NOT_IMPLEMENTED)
        # general error handling should be done by the mapper functions
        try:
            result = func(self)
        except Exception, e:
            if isinstance(e, SeisHubError):
                raise
            else:
                msg = "Error processing %s mapper for %s." % (self.method, 
                                                              self.path)
                raise SeisHubError(msg, code=http.INTERNAL_SERVER_ERROR)
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
            msg = "A mapper must return a dictionary containing folder," + \
                  "file or resource elements."
            raise SeisHubError(msg, code=http.INTERNAL_SERVER_ERROR)
        mapping_urls = result.get('mapping', [])
        folder_urls = result.get('folder', [])
        file_urls = result.get('file', [])
        resource_urls = result.get('resource', [])
        return self.renderResourceList(mapping=mapping_urls,
                                       folder=folder_urls,
                                       file=file_urls,
                                       resource=resource_urls)
    
    def _processAlias(self, package_id, resourcetype_id, alias):
        """Process an alias request."""
        # if alias > 1 - may be an indirect resource request - SFTP problem
        if len(alias)>1:
            # XXX: missing yet
            raise SeisHubError(code=http.NOT_IMPLEMENTED)
        # remove leading @
        alias_id = alias[0][1:]
        # fetch alias
        aliases = self.env.registry.aliases.get(package_id, resourcetype_id,
                                                alias_id)
        try:
            resource_objs = self.env.catalog.query(aliases[0].getQuery())
        except Exception, e:
            self.env.log.error(e)
            raise SeisHubError(e, code = http.INTERNAL_SERVER_ERROR)
        else:
            return self.renderResourceList(resource=resource_objs)
    
    def _getResource(self, package_id, resourcetype_id, name, revision=None):
        """Fetches the content of an existing resource.
        
        @see: http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.4.1
        for all possible error codes.
        """
        result = self.env.catalog.getResource(package_id,
                                              resourcetype_id,
                                              name,
                                              revision)
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
            msg = "SeisHub resources may not be added directly."
            raise ForbiddenError(msg)
        # add a new resource
        res = self.env.catalog.addResource(package_id, 
                                           resourcetype_id,
                                           self.data, 
                                           name=name)
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
            msg = "Modifying resources is not allowed here."
            raise ForbiddenError(msg)
        # seishub directory is not directly changeable
        if package_id=='seishub':
            msg = "SeisHub resources may not be modified directly."
            raise ForbiddenError(msg)
        # modify resource
        self.env.catalog.modifyResource(package_id,
                                        resourcetype_id,
                                        name,
                                        self.data)
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
            msg = "Deleting resources is not allowed here."
            raise ForbiddenError(msg)
        # resource in SeisHub directory are not directly deletable
        if package_id=='seishub':
            msg = "SeisHub resources may not be deleted directly."
            raise ForbiddenError(msg)
        # delete resource
        self.env.catalog.deleteResource(package_id,
                                        resourcetype_id,
                                        name)
        # resource deleted - set status code
        self.response_code = http.NO_CONTENT
        return ''
    
    def _moveResource(self, package_id, resourcetype_id, name):
        """Processes a resource move/rename request.
        
        @see: http://msdn.microsoft.com/en-us/library/aa142926(EXCHG.65).aspx
        """
        # test if the request was called in a resource type directory 
        if len(self.postpath) != 4:
            msg = "Moving resources is not allowed here."
            raise ForbiddenError(msg)
        # seishub directory is not directly changeable
        if package_id=='seishub':
            msg = "SeisHub resources may not be moved directly."
            raise ForbiddenError(msg)
        # test if destination is set
        destination = self.received_headers.get('Destination', False) 
        if not destination:
            msg = "Expected a destination header."
            raise SeisHubError(msg, code=http.BAD_REQUEST)
        if not destination.startswith(self.env.getRestUrl()):
            if destination.startswith('http'):
                msg = "Destination URI is located on a different server."
                raise SeisHubError(msg, code=http.BAD_GATEWAY)
            msg = "Expected a complete destination path."
            raise SeisHubError(msg, code=http.BAD_REQUEST)
        # test size of destination URI
        if len(destination)>=MAX_URI_LENGTH:
            msg = "Destination URI is to long."
            raise SeisHubError(msg, code=http.REQUEST_URI_TOO_LONG)
        # strip host
        destination = destination[len(self.env.getRestUrl()):]
        # source uri and destination uri must not be the same value
        destination_part = splitPath(destination)
        if destination_part == self.postpath:
            msg = "Source uri and destination uri must not be the same value."
            raise ForbiddenError(msg)
        # test if valid destination path
        if len(destination_part)!=4:
            msg = "Destination %s not allowed." % destination
            raise ForbiddenError(msg)
        # test destination path
        if destination_part[0:3] != self.postpath[0:3]:
            msg = "Resources may moved only within the same resource type."
            raise ForbiddenError(msg)
        # moves or rename resource
        self.env.catalog.moveResource(package_id,
                                      resourcetype_id,
                                      name, 
                                      destination_part[3])
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
        # special xml and fs directory
        folder_urls = ['/' + package_id + '/xml', 
                             '/' + package_id + '/fs']
        return self.renderResourceList(alias=alias_urls,
                                       mapping=mapping_urls,
                                       property=property_urls,
                                       folder=folder_urls)
    
    def _getResourceTypes(self, package_id):
        """GET request on the resource types XML directory.
        
        This resource list contains all package specific resource types.
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
                raise NotFoundError()
        pos = len(self.postpath)+2
        mapping_ids = ['/'.join(uri.split('/')[0:pos]) for uri in uris]
        return self.renderResourceList(folder=mapping_ids)
    
    def _getFSDirectories(self, package_id):
        """GET request on the root of the file system directory.
        
        This resource list contains all package specific file system views.
        """
        from seishub.core import PackageManager
        from seishub.packages.interfaces import IFSDirectory
        all = PackageManager.getClasses(IFSDirectory, package_id)
        enabled = [cls for cls in all if self.env.isComponentEnabled(cls)]
        ids = [cls.directory_id for cls in enabled]
        ids.sort()
        urls = ['/' + package_id + '/fs/' + id for id in ids]
        return self.renderResourceList(resourcetype=urls)
    
    def _isFSDirectoryId(self, package_id, directory_id):
        """Checks for a valid file system directory."""
        from seishub.core import PackageManager
        from seishub.packages.interfaces import IFSDirectory
        all = PackageManager.getClasses(IFSDirectory, package_id)
        enabled = [cls for cls in all if self.env.isComponentEnabled(cls)]
        ids = [cls.directory_id for cls in enabled]
        if directory_id in ids:
            return True
        return False
    
    def _getFileSystem(self, package_id, directory_id, path=None):
        """GET request on a file system directory."""
        id = package_id + '.' + directory_id
        # XXX: here is stuff missing yet
        if self.env.config.has_site_option('fs', id):
            ids_and_paths = self.env.config.getlist('fs', id)
            
            return self.renderResourceList(folder=ids_and_paths)
        else:
            self.env.config.set('fs', id, '')
            self.env.config.save()
            return self.renderResourceList(resourcetype=[])
    
    def renderResource(self, data):
        """Resource handler.
        
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