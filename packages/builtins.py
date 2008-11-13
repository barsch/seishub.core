# -*- coding: utf-8 -*-

import os

from seishub.core import Component, implements
from seishub.packages.interfaces import IPackage, IResourceType
from seishub.packages.interfaces import IMapperMethod
from seishub.packages.interfaces import IGETMapper, IPUTMapper
from seishub.packages.interfaces import IPOSTMapper, IDELETEMapper
from seishub.packages.installer import registerStylesheet, registerIndex


class GETMethod(Component):
    """HTTP GET method for mappers."""
    implements(IMapperMethod)
    
    id = 'GET'
    mapper = IGETMapper


class PUTMethod(Component):
    """HTTP PUT method for mappers."""
    implements(IMapperMethod)
    
    id = 'PUT'
    mapper = IPUTMapper


class POSTMethod(Component):
    """HTTP POST method for mappers."""
    implements(IMapperMethod)
    
    id = 'POST'
    mapper = IPOSTMapper


class DELETEMethod(Component):
    """HTTP DELETE method for mappers."""
    implements(IMapperMethod)
    
    id = 'DELETE'
    mapper = IDELETEMapper


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
