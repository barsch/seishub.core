# -*- coding: utf-8 -*-

from seishub.exceptions import ForbiddenError, NotFoundError, SeisHubError, \
    NotAllowedError
from seishub.processor.interfaces import IXMLResource
from seishub.processor.processor import MAX_URI_LENGTH, PUT, GET
from seishub.processor.resources.resource import Resource, Folder
from seishub.util.path import splitPath
from seishub.util.text import isInteger
from seishub.util.xml import addXMLDeclaration
from twisted.web import http
from zope.interface import implements


class XMLResource(Resource):
    """A XML resource node."""
    implements(IXMLResource)
    
    # XXX: revision should be eventually a extra resource type ...
    # this would solve the issue about http.FORBIDDEN and http.NOT_ALLOWED
    
    def __init__(self, package_id, resourcetype_id, name, document=None):
        Resource.__init__(self)
        self.category = 'resource'
        self.is_leaf = True
        self.folderish = False
        self.package_id = package_id
        self.resourcetype_id = resourcetype_id
        self.name = name
        self.document = document
    
    def render_GET(self, request):
        """Process a resource query request.
        
        A query at the root of a resource type folder returns a list of all
        available XML resource objects of this resource type. Direct request on
        a XML resource results in the content of a XML document. Before 
        returning a XML document, we add a valid XML declaration header and 
        encode it as UTF-8 string.
        
        @see: http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.4.1
        for all possible error codes.
        """
        # test if version controlled resource
        if len(request.postpath)==1:
            if isInteger(request.postpath[0]):
                revision = request.postpath[0]
            else:
                raise NotFoundError()
        elif len(request.postpath)>1:
            raise ForbiddenError()
        else:
            revision = None
        # fetch resource
        result = request.env.catalog.getResource(self.package_id,
                                                 self.resourcetype_id,
                                                 self.name,
                                                 revision)
        data = result.document.data
        # ensure we return a utf-8 encoded string not an unicode object
        if isinstance(data, unicode):
            data = data.encode('utf-8')
        # set XML declaration inclusive UTF-8 encoding string
        if not data.startswith('<xml'):
            data = addXMLDeclaration(data, 'utf-8')
        return data
    
    def process_PUT(self, request):
        """Create request on a existing resource.
        
        @see: http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.6
        @see: http://thoughtpad.net/alan-dean/http-headers-status.gif
        
        "If the Request-URI refers to an already existing resource, the 
        enclosed entity SHOULD be considered as a modified version of the one 
        residing on the origin server. If an existing resource is modified, 
        either the 200 (OK) or 204 (No Content) response codes SHOULD be sent 
        to indicate successful completion of the request.
        
        If the resource could not be created or modified with the Request-URI,
        an appropriate error response SHOULD be given that reflects the nature
        of the problem." 
        
        Adding documents can be done directly on an existing resource type or 
        via user defined mapping.
        """
        self.render_POST(request)
    
    def render_POST(self, request):
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
        if len(request.postpath)!=0:
            raise ForbiddenError() 
        # seishub directory is not directly changeable
        if self.package_id=='seishub':
            msg = "SeisHub resources may not be modified directly."
            raise ForbiddenError(msg)
        # modify resource
        request.env.catalog.modifyResource(self.package_id,
                                           self.resourcetype_id,
                                           self.name,
                                           request.data)
        # resource successfully modified - set status code
        request.response_code = http.NO_CONTENT
        return ''
    
    def render_MOVE(self, request):
        """Processes a resource move/rename request.
        
        @see: http://msdn.microsoft.com/en-us/library/aa142926(EXCHG.65).aspx
        """
        # only resources may be moved
        if len(request.postpath)==1:
            raise ForbiddenError("Revisions may not be moved.") 
        if len(request.postpath)!=0:
            raise ForbiddenError() 
        # seishub directory is not directly changeable
        if self.package_id=='seishub':
            msg = "SeisHub resources may not be moved directly."
            raise ForbiddenError(msg)
        # test if destination is set
        destination = request.received_headers.get('Destination', False) 
        if not destination:
            msg = "Expected a destination header."
            raise SeisHubError(msg, code=http.BAD_REQUEST)
        if not destination.startswith(request.env.getRestUrl()):
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
        destination = destination[len(request.env.getRestUrl()):]
        # source uri and destination uri must not be the same value
        parts = splitPath(destination)
        if parts == request.prepath:
            msg = "Source uri and destination uri must not be the same value."
            raise ForbiddenError(msg)
        # test if valid destination path
        if len(parts)<1 or parts[:-1]!=request.prepath[:-1]:
            msg = "Destination %s not allowed." % destination
            raise ForbiddenError(msg)
        # moves or rename resource
        request.env.catalog.moveResource(self.package_id,
                                         self.resourcetype_id,
                                         self.name, 
                                         parts[-1])
        # on successful creation - set status code and location header
        request.response_code = http.CREATED
        url = request.env.getRestUrl() + destination
        request.response_header['Location'] = url
        return ''
    
    def render_DELETE(self, request):
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
        # only resource may be deleted
        if len(request.postpath)==1:
            raise ForbiddenError("Revisions may not be deleted directly.") 
        if len(request.postpath)!=0:
            raise ForbiddenError() 
        # resource in SeisHub directory are not directly deletable
        if self.package_id=='seishub':
            msg = "SeisHub resources may not be deleted directly."
            raise ForbiddenError(msg)
        # delete resource
        request.env.catalog.deleteResource(self.package_id,
                                           self.resourcetype_id,
                                           self.name)
        # resource deleted - set status code
        request.response_code = http.NO_CONTENT
        return ''


class XMLIndex(Resource):
    """A XML index node."""
    
    def __init__(self):
        Resource.__init__(self)
        self.category = 'index'
        self.is_leaf = False
        self.folderish = False


class RESTResourceTypeFolder(Folder):
    """A REST resource type folder."""
    
    def __init__(self, package_id, resourcetype_id):
        Folder.__init__(self)
        self.category = 'resourcetype'
        self.is_leaf = True
        self.package_id = package_id
        self.resourcetype_id = resourcetype_id
    
    def getChild(self, id, request):
        """Returns a L{XMLResource} object if a valid id is given."""
        try:
            res = request.env.catalog.getResource(self.package_id,
                                                  self.resourcetype_id,
                                                  id)
            return XMLResource(self.package_id, 
                               self.resourcetype_id, 
                               res.name,
                               res.document)
        except NotFoundError:
            pass
    
    def render(self, request):
        if request.method==GET and len(request.postpath)==0:
            return self.render_GET(request)
        elif request.method==PUT:
            return self.render_PUT(request)
        elif len(request.postpath)>=1:
            id = request.postpath.pop(0)
            request.prepath.append(id)
            child = self.getChild(id, request)
            if child:
                return child.render(request)
            raise NotFoundError
        raise NotAllowedError("Operation is not allowed here.")
    
    def render_PUT(self, request):
        """Create a new XML resource for this resource type.
        
        "The PUT method requests that the enclosed entity be stored under the 
        supplied Request-URI. If the Request-URI does not point to an existing 
        resource, and that URI is capable of being defined as a new resource by
        the requesting user agent, the server can create the resource with that
        URI. If a new resource is created, the origin server MUST inform the 
        user agent via the 201 (Created) response. 
        
        If the resource could not be created or modified with the Request-URI, 
        an appropriate error response SHOULD be given that reflects the nature 
        of the problem." 
        
        @see: http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.6
        @see: http://thoughtpad.net/alan-dean/http-headers-status.gif
        """
        if len(request.postpath) not in [0, 1]:
            raise ForbiddenError("Operation is not allowed here.")
        # seishub directory is not directly changeable
        if self.package_id=='seishub':
            msg = "SeisHub resources may not be added directly."
            raise ForbiddenError(msg)
        # check if name is given
        if len(request.postpath)==1:
            name=request.postpath[0]
        else:
            name=None
        # add a new resource
        res = request.env.catalog.addResource(self.package_id,
                                              self.resourcetype_id,
                                              request.data,
                                              name=name)
        # resource created - set status code and location header
        request.response_code = http.CREATED
        url = request.env.getRestUrl() + request.path + '/' + str(res.name)
        request.response_header['Location'] = url
        return ''
    
    def render_GET(self, request):
        """Returns all resources and indexes of this resource type."""
        temp = {}
        for res in request.env.catalog.getResourceList(self.package_id,
                                                       self.resourcetype_id):
            temp[res.name] = XMLResource(self.package_id, 
                                         self.resourcetype_id, 
                                         res.name,
                                         res.document)
        for id in request.env.catalog.listIndexes(self.package_id,
                                                  self.resourcetype_id):
            temp[str(id)] = XMLIndex()
        return temp


class RESTPackageFolder(Folder):
    """A REST package folder."""
    
    def __init__(self, package_id):
        Folder.__init__(self)
        self.category = 'package'
        self.package_id = package_id
    
    def getChild(self, id, request):
        """Returns a L{RESTResourceTypeFolder} object for a valid id."""
        if request.env.registry.isResourceTypeId(self.package_id, id):
            return RESTResourceTypeFolder(self.package_id, id)
        raise NotFoundError
    
    def render_GET(self, request):
        """Returns a dictionary of all resource types of this package."""
        temp = {}
        for id in request.env.registry.getResourceTypeIds(self.package_id):
            temp[id] = RESTResourceTypeFolder(self.package_id, id)
        return temp


class RESTFolder(Folder):
    """A REST root folder."""
    
    def __init__(self):
        Folder.__init__(self)
        self.category = 'xmlroot'
    
    def getChild(self, id, request):
        """Returns a L{XMLPackageFolder} object for a valid id."""
        if request.env.registry.isPackageId(id):
            return RESTPackageFolder(id)
        raise NotFoundError
    
    def render_GET(self, request):
        """Returns a dictionary of all SeisHub packages."""
        temp = {}
        for id in request.env.registry.getPackageIds():
            temp[id] = RESTPackageFolder(id)
        return temp
