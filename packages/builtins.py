# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.packages.installer import registerStylesheet, registerIndex
from seishub.packages.interfaces import IPackage, IResourceType, IMapper
import os
from seishub.util import toJSON


class SeisHubPackage(Component):
    """
    The SeisHub package.
    """
    implements(IPackage)
    package_id = 'seishub'

    version = '0.1'


class StylesheetResource(Component):
    """
    A stylesheet resource type for SeisHub.
    """
    implements(IResourceType)

    package_id = 'seishub'
    resourcetype_id = 'stylesheet'

    registerStylesheet('xslt' + os.sep + 'index_xhtml.xslt', 'index.xhtml')
    registerStylesheet('xslt' + os.sep + 'meta_xhtml.xslt', 'meta.xhtml')
    registerStylesheet('xslt' + os.sep + 'resourcelist_xhtml.xslt',
                       'resourcelist.xhtml',)
    registerStylesheet('xslt' + os.sep + 'resourcelist_json.xslt',
                       'resourcelist.json')
    registerStylesheet('xslt' + os.sep + 'resourcelist_admin.xslt',
                       'resourcelist.admin')
    registerIndex('media-type', '/xsl:stylesheet/xsl:output/@media-type',
                  'text')


class SchemaResource(Component):
    """
    A schema resource type for SeisHub.
    """
    implements(IResourceType)

    package_id = 'seishub'
    resourcetype_id = 'schema'


class XPathMapper(Component):
    """
    A mapper to directly query XPath expressions.
    """
    implements(IMapper)

    package_id = 'seishub'
    mapping_url = '/xpath'

    def process_GET(self, request):
        # get resources
        resources = self.env.catalog.query(request.path[6:], full=True)
        # get indexed data
        result = {}
        for resource in resources:
            data = self.env.catalog.getIndexData(resource)
            result[str(resource)] = data
        # generate correct header 
        request.setHeader('content-type', 'application/json; charset=UTF-8')
        return toJSON(result)
