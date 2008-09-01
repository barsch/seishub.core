# -*- coding: utf-8 -*-

from seishub.core import Component, implements
from seishub.packages.interfaces import IPackage, IResourceType, \
                                        IMapperMethod, \
                                        IGETMapper, IPUTMapper, \
                                        IPOSTMapper, IDELETEMapper


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


class SchemaResource(Component):
    """A schema resource type for SeisHub."""
    implements(IResourceType)
    
    package_id = 'seishub'
    resourcetype_id = 'schema'
    

class GETMethod(Component):
    """HTTP GET method for mappers"""
    implements(IMapperMethod)
    
    id = 'GET'
    mapper = IGETMapper


class PUTMethod(Component):
    """HTTP PUT method for mappers"""
    implements(IMapperMethod)
    
    id = 'PUT'
    mapper = IPUTMapper
    

class POSTMethod(Component):
    """HTTP POST method for mappers"""
    implements(IMapperMethod)
    
    id = 'POST'
    mapper = IPOSTMapper
    

class DELETEMethod(Component):
    """HTTP DELETE method for mappers"""
    implements(IMapperMethod)
    
    id = 'DELETE'
    mapper = IDELETEMapper
    
