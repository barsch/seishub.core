# -*- coding: utf-8 -*-
"""
REST based resources.
"""

from lxml import etree
from obspy.core import UTCDateTime
from seishub.core.exceptions import ForbiddenError, NotFoundError, \
    SeisHubError, NotAllowedError, UnauthorizedError
from seishub.core.processor.interfaces import IRESTResource, IRESTProperty, \
    IXMLIndex
from seishub.core.processor.processor import MAXIMAL_URL_LENGTH, PUT, GET, \
    HEAD, POST
from seishub.core.processor.resources.resource import Resource, Folder, \
    StaticFolder
from seishub.core.db.util import formatResults
from seishub.core.util.path import splitPath
from seishub.core.util.text import isInteger
from seishub.core.util.xml import addXMLDeclaration
from sqlalchemy import sql, Table
from twisted.web import http
from zope.interface import implements


class RESTResource(Resource):
    """
    A REST resource node.
    """
    implements(IRESTResource)

    def __init__(self, res, **kwargs):
        Resource.__init__(self, **kwargs)
        self.category = 'resource'
        self.is_leaf = True
        self.folderish = False
        # initialize REST resource either via dictionary or a given resource
        if isinstance(res, dict):
            self.package_id = res['package_id']
            self.resourcetype_id = res['resourcetype_id']
            self.name = res['resource_name']
            self.revision = res['revision']
            self.res = None
            self.meta = res
        else:
            self.package_id = res.package.package_id
            self.resourcetype_id = res.resourcetype.resourcetype_id
            self.name = res.name
            self.revision = res.document.revision
            self.res = res
            meta = self.res.document.meta
            self.meta = {
                'meta_size': meta.size,
                'meta_uid': meta.uid,
                'meta_datetime': meta.datetime
            }
        # set url
        self.url = "/xml/%s/%s/%s" % (self.package_id, self.resourcetype_id,
                                      self.name)

    def getMetadata(self):
        temp = int(UTCDateTime(self.meta['meta_datetime']).timestamp)
        return {
            'permissions': 0100644,
            'uid': self.meta['meta_uid'],
            'size': self.meta['meta_size'],
            'atime': temp,
            'mtime': temp
        }

    def _format(self, request, data):
        """
        Handles output/format conversion of content.
        """
        # parse request headers for output/format options
        formats = request.args.get('format', []) or \
                  request.args.get('output', [])
        # handle output/format conversion
        for format in formats:
            # fetch a XSLT document objects
            reg = request.env.registry
            xslt = reg.stylesheets.get(package_id=self.package_id,
                                       resourcetype_id=self.resourcetype_id,
                                       type=format)
            if len(xslt):
                xslt = xslt[0]
                # transform
                data = xslt.transform(data, request.env.xslt_params)
                # set additional content-type if given in XSLT
                if xslt.content_type:
                    request.setHeader('content-type',
                                      xslt.content_type + '; charset=UTF-8')
                continue
            # search for a ResourceFormater class
            cls = reg.formaters.get(package_id=self.package_id,
                                    resourcetype_id=self.resourcetype_id,
                                    format=format)
            if cls:
                return cls.format(request, data, self.name)
            # else log error
            msg = 'There is no output format "%s" for request %s.'
            request.env.log.debug(msg % (format, request.path))
        return data

    def _checkPermissions(self, request, permissions=755):
        # authenticate
        uid = request.getUser()
        doc_uid = self.meta['meta_uid']
        if not doc_uid:
            return
        if uid == doc_uid:
            return
        # check permission for local user
        user = request.env.auth.getUser(uid)
        if user.permissions < permissions:
            raise UnauthorizedError()

    def render_GET(self, request):
        """
        Process a resource query request.

        A query at the root of a resource type folder returns a list of all
        available XML resource objects of this resource type. Direct request on
        a XML resource results in the content of a XML document. Before
        returning a XML document, we add a valid XML declaration header and
        encode it as UTF-8 string.

        @see:
        U{http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html#sec10.4.1}
        for all possible error codes.
        """
        # global anonymous access allowed
        if request.env.auth.getUser('anonymous').permissions != 755:
            self._checkPermissions(request, 755)
        data = self.res.document.data
        # ensure we return a UTF-8 encoded string not an Unicode object
        if isinstance(data, unicode):
            data = data.encode('utf-8')
        # set XML declaration inclusive UTF-8 encoding string
        if not data.startswith('<xml'):
            data = addXMLDeclaration(data, 'utf-8')
        # handle output/format conversion
        data = self._format(request, data)
        # set last-modified time
        dt = UTCDateTime(self.res.document.meta.getDatetime())
        try:
            request.setLastModified(dt.timestamp)
        except:
            pass
#        # cache control - 10 seconds
#       now = UTCDateTime()
#       request.setHeader("Cache-Control", "max-age = 10")
#       request.setHeader("Expires", http.datetimeToString(now.timestamp + 10))
        # return data
        return data

    def render_PUT(self, request):
        """
        Processes a resource modification request.

        "The PUT method requests that the enclosed entity be stored under the
        supplied Request-URI. If the Request-URI does not point to an existing
        resource, and that URI is capable of being defined as a new resource by
        the requesting user agent, the server can create the resource with that
        URI. If a new resource is created, the origin server MUST inform the
        user agent via the 201 (Created) response.

        If the resource could not be created or modified with the Request-URI,
        an appropriate error response SHOULD be given that reflects the nature
        of the problem."

        @see: U{http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.6}
        @see: U{http://thoughtpad.net/alan-dean/http-headers-status.gif}

        Modifying a document always needs a valid path to a resource or uses a
        user defined mapping.
        """
        self._checkPermissions(request, 777)
        # SeisHub directory is not directly changeable
        if self.package_id == 'seishub':
            msg = "SeisHub resources may not be modified directly."
            raise ForbiddenError(msg)
        # parse request headers for output/format options
        data = request.data
        # handle output/format conversion
        data = self._format(request, data)
        # get UID
        uid = request.getUser()
        # modify resource
        request.env.catalog.modifyResource(self.res, data, uid=uid)
        # resource successfully modified - set status code
        request.code = http.NO_CONTENT
        return ''

    def render_MOVE(self, request):
        """
        Processes a resource move/rename request.

        @see:
        U{http://msdn.microsoft.com/en-us/library/aa142926(EXCHG.65).aspx}
        """
        self._checkPermissions(request, 777)
        # seishub directory is not directly changeable
        if self.package_id == 'seishub':
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
        if len(destination) >= MAXIMAL_URL_LENGTH:
            msg = "Destination URI is to long."
            raise SeisHubError(msg, code=http.REQUEST_URI_TOO_LONG)

        # strip host
        destination = destination[len(request.env.getRestUrl()):]
        # source URI and destination URI must not be the same value
        parts = splitPath(destination)
        if parts == request.prepath:
            msg = "Source URI and destination URI must not be the same value."
            raise ForbiddenError(msg)
        # test if valid destination path
        if len(parts) < 1 or parts[:-1] != request.prepath[:-1]:
            msg = "Destination %s not allowed." % destination
            raise ForbiddenError(msg)
        # rename resource
        request.env.catalog.renameResource(self.res, parts[-1])
        # on successful creation - set status code and location header
        request.code = http.CREATED
        url = request.env.getRestUrl() + destination
        # won't accept Unicode
        request.headers['Location'] = str(url)
        return ''

    def render_DELETE(self, request):
        """
        Processes a resource deletion request.

        @see: U{http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.7}

        "The DELETE method requests that the server deletes the resource
        identified by the given request URI.

        A successful response SHOULD be 200 (OK) if the response includes an
        entity describing the status, 202 (Accepted) if the action has not yet
        been enacted, or 204 (No Content) if the action has been enacted but
        the response does not include an entity."

        Deleting a document always needs a valid path to a resource or may use
        a user defined mapping.
        """
        self._checkPermissions(request, 777)
        # resource in SeisHub directory are not directly removable
        if self.package_id == 'seishub':
            msg = "SeisHub resources may not be deleted directly."
            raise ForbiddenError(msg)
        # delete resource
        request.env.catalog.deleteResource(self.res)
        # resource deleted - set status code
        request.code = http.NO_CONTENT
        return ''


class XMLIndex(Resource):
    """
    A XML index node.
    """
    implements(IXMLIndex)

    def __init__(self, **kwargs):
        Resource.__init__(self, **kwargs)
        self.category = 'index'
        self.is_leaf = True
        self.folderish = False


class RESTProperty(Resource):
    """
    A REST property node.
    """
    implements(IRESTProperty)

    def __init__(self, package_id, resourcetype_id, name, revision=None,
                 **kwargs):
        Resource.__init__(self, **kwargs)
        self.is_leaf = True
        self.folderish = False
        self.package_id = package_id
        self.resourcetype_id = resourcetype_id
        self.name = name
        self.revision = revision

    def render_GET(self, request):
        property = request.postpath[-1]
        # check for valid properties
        if property == '.index':
            res = request.env.catalog.getResource(self.package_id,
                                                  self.resourcetype_id,
                                                  self.name,
                                                  self.revision)
            # dictionary of indexes
            index_dict = request.env.catalog.getIndexData(res)
            # create a XML document
            root = etree.Element("seishub")
            for label, values_dict in index_dict.iteritems():
                sub = etree.SubElement(root, label)
                for _pos, values in values_dict.iteritems():
                    for value in values:
                        if not value:
                            continue
                        if not isinstance(value, basestring):
                            value = unicode(value)
                        etree.SubElement(sub, "value").text = value
            data = etree.tostring(root, pretty_print=True, encoding='utf-8')
            format_prefix = 'index'
        elif property == '.meta':
            res = request.env.catalog.getResource(self.package_id,
                                                  self.resourcetype_id,
                                                  self.name,
                                                  self.revision)
            meta = res.document.meta
            # create a XML document
            root = etree.Element("seishub")
            etree.SubElement(root, "package").text = self.package_id
            etree.SubElement(root, "resourcetype").text = self.resourcetype_id
            etree.SubElement(root, "name").text = self.name
            etree.SubElement(root, "document_id").text = str(res.document._id)
            etree.SubElement(root, "resource_id").text = str(res._id)
            etree.SubElement(root, "revision").text = \
                str(res.document.revision)
            etree.SubElement(root, "uid").text = unicode(meta.uid)
            etree.SubElement(root, "datetime").text = \
                unicode(meta.datetime.isoformat())
            etree.SubElement(root, "size").text = unicode(meta.size)
            etree.SubElement(root, "hash").text = unicode(meta.hash)
            data = etree.tostring(root, pretty_print=True, encoding='utf-8')
            format_prefix = 'meta'
        else:
            raise NotFoundError("Property %s is not defined." % property)
        # ensure we return a utf-8 encoded string not an unicode object
        if isinstance(data, unicode):
            data = data.encode('utf-8')
        # set XML declaration inclusive UTF-8 encoding string
        if not data.startswith('<xml'):
            data = addXMLDeclaration(data, 'utf-8')
        # parse request headers for output type
        format = request.args.get('format', [None])[0] or \
                 request.args.get('output', [None])[0]
        # handle output/format conversion
        if format:
            format = '%s.%s' % (format_prefix, format)
            # fetch a XSLT document object
            reg = request.env.registry
            xslt = reg.stylesheets.get(package_id='seishub',
                                       resourcetype_id='stylesheet',
                                       type=format)
            if len(xslt):
                xslt = xslt[0]
                data = xslt.transform(data)
                # set additional content-type if given in XSLT
                if xslt.content_type:
                    request.setHeader('content-type',
                                      xslt.content_type + '; charset=UTF-8')
            else:
                msg = "There is no stylesheet for requested format %s."
                request.env.log.debug(msg % format)
        return data


class RESTResourceTypeFolder(Folder):
    """
    A REST resource type folder.

    Handles the following HTTP methods: GET, POST, PUT, MOVE, DELETE


    GET returns different things, depending on the exact path:

    * GET package/resource_type
        Returns a list with the indexed values for each resource of the given
        type
    * GET package/resource_type/.meta
        Returns all indexes and resources associated with the resource type
    * GET package/resource_type/resource_name
        Returns the actual resource
    * GET package/resource_type/resource_name/revision_number
        Returns the requested revision of the resource
    * GET package/resource_type/resource_name/.property
        Returns the property information for the specified resource. Currently
        implemented properties:
            .meta: Returns metainformation for the specified resource
            .index: Returns the indexed values for the specified resources
    * GET package/resource_type/resource_name/revision_number/.property
        Returns the property information for a specified revision.

    POST can create new named and unnamed resources. It cannot update an
    already existing resource:

    POST and PUT are almost identical with the difference that POST can also
    create unnamed resources.

    * POST/PUT package/resource_type/resource_name
        Create a new, named resource or update an existing one.
    * POST package/resource_type
        Creates a new, unnamed resource. Will automatically create a numeric
        resource name.

    MOVE and DELETE work with already existing resources:
    * MOVE/DELETE package/resource_type/resource_name
        Moves/deletes the specified resource.
    """

    def __init__(self, package_id, resourcetype_id, **kwargs):
        Folder.__init__(self, **kwargs)
        self.category = 'resourcetype'
        self.is_leaf = True
        self.package_id = package_id
        self.resourcetype_id = resourcetype_id

    def render(self, request):
        """
        All requests to any resource of this type will end up here.

        They will be routed according to the logic specified in the docstring
        of this class.
        """
        rlen = len(request.postpath)
        if request.method == "GET":
            return self.render_GET(request)
        elif request.method in ["POST"] and rlen <= 1:
            return self.render_POST(request)
        elif request.method in ["MOVE", "DELETE", "PUT"] and rlen == 1:
            return self._processResource(request)
        else:
            allowed_methods = ["GET", "POST"]
            msg = "This operation is not allowed on this resource."
            raise NotAllowedError(allowed_methods=allowed_methods, message=msg)

    def render_GET(self, request):
        """
        Handles all GET requests.
        """
        rlen = len(request.postpath)

        # If nothing else is given, just render a list of every resource of
        # this type.
        if rlen == 0:
            return self.renderResourceList(request)
        # Special .meta resource renders information about the resource type.
        elif rlen == 1 and request.postpath[0] == ".meta":
            return self.renderMetaInformation(request)
        # Otherwise attempt to render the most recent version of the specified
        # resource.
        elif rlen == 1:
            name = request.postpath.pop(0)
            request.prepath.append(name)
            res = request.env.catalog.getResource(self.package_id,
                self.resourcetype_id, name, revision=None)
            return RESTResource(res)

        # Longer paths can either request certain revisions of a resource or
        # metainformation of the resource.
        revision = None
        name = request.postpath.pop(0)
        request.prepath.append(name)
        if request.postpath and isInteger(request.postpath[0]):
            revision = request.postpath.pop(0)
            request.prepath.append(revision)
        # Property requests
        if request.postpath and request.postpath[0].startswith("."):
            return RESTProperty(self.package_id, self.resourcetype_id, name,
                revision=revision)

        # Finally return the resource.
        res = request.env.catalog.getResource(self.package_id,
            self.resourcetype_id, name, revision=revision)
        return RESTResource(res)

    def _processResource(self, request):
        """
        Delegates PUT, MOVE, and DELETE requests to the resource.
        """
        if request.prepath[0] == "seishub":
            msg = "Built-in resources cannot be modified"
            raise ForbiddenError(msg)
        # resource request
        try:
            res = request.env.catalog.getResource(self.package_id,
                                                  self.resourcetype_id,
                                                  request.postpath[0],
                                                  revision=None)
        except NotFoundError as e:
            # PUT can also create a named resource.
            if request.method == PUT:
                return self.render_POST(request)
            raise e
        except Exception as e:
            raise e
        # Update pre- and postpaths.
        name = request.postpath.pop(0)
        request.prepath.append(name)
        return RESTResource(res).render(request)

    def render_POST(self, request):
        """
        Create a new XML resource for this resource type.

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

        @see: U{http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html#sec9.5}
        """
        # SeisHub directory is not directly changeable
        if self.package_id == 'seishub':
            msg = "SeisHub resources may not be added directly."
            raise ForbiddenError(msg)
        # check if name is given
        if len(request.postpath) == 1:
            name = request.postpath[0]
        else:
            name = None
        # set uid
        uid = request.getUser()
        # parse request headers for output/format options
        data = request.data
        formats = request.args.get('format', []) or \
                  request.args.get('output', [])
        # handle output/format conversion
        for format in formats:
            # fetch a XSLT document objects
            reg = request.env.registry
            xslt = reg.stylesheets.get(package_id=self.package_id,
                                       resourcetype_id=self.resourcetype_id,
                                       type=format)
            if len(xslt):
                xslt = xslt[0]
                data = xslt.transform(data)
                # set additional content-type if given in XSLT
                if xslt.content_type:
                    request.setHeader('content-type',
                                      xslt.content_type + '; charset=UTF-8')
            else:
                msg = "There is no stylesheet for requested format %s."
                request.env.log.debug(msg % format)
        # add a new resource
        res = request.env.catalog.addResource(self.package_id,
                                              self.resourcetype_id,
                                              data, uid=uid, name=name)
        # resource created - set status code and location header
        request.code = http.CREATED
        url = "%s/%s/%s" % (request.env.getRestUrl(),
                            '/'.join(request.prepath),
                            str(res.name))
        # won't accept Unicode
        request.headers['Location'] = str(url)
        return ''

    def renderResourceList(self, request):
        """
        Returns the indexed values of every resource of the given type.

        This directly accesses the database and does not use the catalog. This
        should be faster as the heavy lifting is done by the database.
        """
        limit = int(request.args0.get("limit", 20))
        offset = int(request.args0.get("offset", 0))
        table = "/%s/%s" % (self.package_id, self.resourcetype_id)
        # Directly access the database via an SQLView which is automatically
        # created for every resource type and filled with all indexed values.
        tab = Table(table,
            request.env.db.metadata, autoload=True)

        count = sql.select([tab]).count()
        count = request.env.db.query(count).first()[0]
        query = sql.select([tab]).limit(limit).offset(offset)
        # Execute the query.
        result = request.env.db.query(query)

        result = formatResults(request, result, limit=limit, offset=offset,
            count=count)
        return result

    def renderMetaInformation(self, request):
        """
        Returns all resources and indexes of this resource type.
        """
        temp = {}
        # resources
        xpath = "/%s/%s" % (self.package_id, self.resourcetype_id)
        res_dict = request.env.catalog.query(xpath)
        for id in res_dict['ordered']:
            name = res_dict[id]['resource_name']
            # skip lower revisions
            if name in temp and temp[name].revision > res_dict[id]['revision']:
                continue
            temp[name] = RESTResource(res_dict[id])
        # indexes
        xmlindex_list = request.env.catalog.getIndexes(
            package_id=self.package_id, resourcetype_id=self.resourcetype_id)
        for id in xmlindex_list:
            temp[str(id)] = XMLIndex()
        return temp


class RESTPackageFolder(StaticFolder):
    """
    A REST package folder.
    """

    def __init__(self, package_id, **kwargs):
        Folder.__init__(self, **kwargs)
        self.category = 'package'
        self.package_id = package_id

    def getChild(self, id, request):
        """
        Returns a L{RESTResourceTypeFolder} object for a valid id.
        """
        if request.env.registry.isResourceTypeId(self.package_id, id):
            return RESTResourceTypeFolder(self.package_id, id)
        raise NotFoundError("XML resource type %s not found." % id)

    def render_GET(self, request):
        """
        Returns a dictionary of all resource types of this package.
        """
        temp = {}
        for id in request.env.registry.getResourceTypeIds(self.package_id):
            temp[id] = RESTResourceTypeFolder(self.package_id, id)
        return temp


class RESTFolder(StaticFolder):
    """
    A REST root folder.
    """

    def __init__(self, **kwargs):
        Folder.__init__(self, **kwargs)
        self.category = 'xmlroot'

    def getChild(self, id, request):
        """
        Returns a L{XMLPackageFolder} object for a valid id.
        """
        if request.env.registry.isPackageId(id):
            return RESTPackageFolder(id)
        raise NotFoundError("XML package %s not found." % id)

    def render_GET(self, request):
        """
        Returns a dictionary of all SeisHub packages.
        """
        temp = {}
        for id in request.env.registry.getPackageIds():
            temp[id] = RESTPackageFolder(id)
        return temp
