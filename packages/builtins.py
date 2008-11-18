# -*- coding: utf-8 -*-

import os

from seishub.core import Component, implements
from seishub.packages.interfaces import IPackage, IResourceType
from seishub.packages.installer import registerStylesheet, registerIndex


class SeisHubPackage(Component):
    """The SeisHub package.""" 
    implements(IPackage)
    package_id = 'seishub'
    
    version = '0.1'


class StylesheetResource(Component):
    """A stylesheet resource type for SeisHub."""
    implements(IResourceType)
    
    package_id = 'seishub'
    resourcetype_id = 'stylesheet'
    
    registerStylesheet('resourcelist.xhtml', 
                       'xslt' + os.sep + 'resourcelist_xhtml.xslt')
    registerStylesheet('resourcelist.json', 
                       'xslt' + os.sep + 'resourcelist_json.xslt')
    registerIndex('/xsl:stylesheet/xsl:output/@media-type', 'text')


class SchemaResource(Component):
    """A schema resource type for SeisHub."""
    implements(IResourceType)
    
    package_id = 'seishub'
    resourcetype_id = 'schema'
