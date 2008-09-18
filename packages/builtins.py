# -*- coding: utf-8 -*-

import os

from twisted.web import http

from seishub.core import Component, implements
from seishub.packages.interfaces import IPackage, IResourceType, \
                                        IMapperMethod, \
                                        IGETMapper, IPUTMapper, \
                                        IPOSTMapper, IDELETEMapper
from seishub.packages.processor import RequestError
from seishub.packages.installer import registerStylesheet


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
    
    registerStylesheet('resourcelist:xhtml', 
                       'xslt' + os.sep + 'resourcelist_xhtml.xslt')
    registerStylesheet('resourcelist:json', 
                       'xslt' + os.sep + 'resourcelist_json.xslt')


class SchemaResource(Component):
    """A schema resource type for SeisHub."""
    implements(IResourceType)
    
    package_id = 'seishub'
    resourcetype_id = 'schema'


class SchemaResourceMapper(Component):
    """A mapper for all registered schemas."""
    implements(IGETMapper, IPUTMapper, IPOSTMapper, IDELETEMapper)
    
    mapping_url = '/seishub/schema/browser'
    
    def processGET(self, request):
        postlen = len(request.postpath)
        # test if root element - show all packages
        if postlen==3:
            ids = request._addBaseToList(self.mapping_url, request.package_ids)
            return {'mapping': ids}
        # test if package at all
        package_id = request.postpath[3]
        if package_id not in request.package_ids:
            raise RequestError(http.NOT_FOUND)
        # package level - show all resource types of this package
        if postlen==4:
            ids = self.env.registry.resourcetypes[package_id]
            ids.sort()
            ids = request._addBaseToList(self.mapping_url + '/' + package_id, 
                                         ids)
            return {'mapping': ids}
        # test if valid resource type
        resourcetype_id = request.postpath[4]
        if not request._checkResourceType(package_id, resourcetype_id):
            raise RequestError(http.NOT_FOUND)
        # resource type level - show all schemas named after label
        if postlen==5:
            # query catalog for schemas
            reg =  self.env.registry
            schemas = reg.schemas.get(package_id = package_id,
                                      resourcetype_id = resourcetype_id)
            ids = [schema.type for schema in schemas]
            ids.sort()
            ids = request._addBaseToList(self.mapping_url + '/' + \
                                         package_id + '/' + resourcetype_id, 
                                         ids)
            return {'resource': ids}
        # direct resource request
        reg =  self.env.registry
        schema = reg.schemas.get(package_id = package_id,
                                 resourcetype_id = resourcetype_id,
                                 type = request.postpath[5])
        if not schema:
            raise RequestError(http.NOT_FOUND)
        return schema[0].getResource().document.data
    
    def processDELETE(self, request):
        rpp = request.postpath
        if len(rpp)!=6:
            raise RequestError(http.NOT_ALLOWED)
        # direct resource request
        try:
            self.env.registry.schemas.delete(package_id = rpp[3],
                                             resourcetype_id = rpp[4],
                                             type = rpp[5])
        except Exception, e:
            self.env.log.info("Error deleting schemas", e)
            raise RequestError(http.NOT_FOUND)
    
    def processPUT(self, request):
        #import pdb;pdb.set_trace()
        rpp = request.postpath
        data = request.content.getvalue()
        if len(rpp)!=6:
            raise RequestError(http.NOT_ALLOWED)
        # direct resource request
        try:
            self.env.registry.schemas.register(rpp[3], rpp[4], rpp[5], data)
        except Exception, e:
            self.env.log.error("Error adding schemas", e)
            raise RequestError(http.INTERNAL_SERVER_ERROR)
        return self.mapping_url + '/'.join(rpp[3:])
