# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.packages.installer import registerStylesheet, registerIndex
from seishub.packages.interfaces import IPackage, IResourceType
import os


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
    
    registerStylesheet('resourcelist.xhtml', 
                       'xslt' + os.sep + 'resourcelist_xhtml.xslt')
    registerStylesheet('resourcelist.json', 
                       'xslt' + os.sep + 'resourcelist_json.xslt')
    registerStylesheet('resourcelist.admin', 
                       'xslt' + os.sep + 'resourcelist_admin.xslt')
    registerIndex('/xsl:stylesheet/xsl:output/@media-type', 'text')


class SchemaResource(Component):
    """
    A schema resource type for SeisHub.
    """
    implements(IResourceType)
    
    package_id = 'seishub'
    resourcetype_id = 'schema'
