# -*- coding: utf-8 -*-

import os

from twisted.web import http

from seishub.core import Component, implements
from seishub.packages.interfaces import IPackage, IResourceType, \
                                        IMapperMethod, \
                                        IGETMapper, IPUTMapper, \
                                        IPOSTMapper, IDELETEMapper
from seishub.packages.processor import ProcessorError
from seishub.packages.installer import registerStylesheet
from seishub.util.text import isInteger
from seishub.util.path import addBaseToList


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
        """Process a GET request at the mapping_url."""
        # test if root element - show all packages
        if len(request.postpath)==3:
            urls = self.registry.getPackageURLs(base=self.mapping_url)
            return {'mapping': urls}
        # test if package at all
        package_id = request.postpath[3]
        if not self.registry.isPackageId(package_id):
            raise ProcessorError(http.FORBIDDEN, "Invalid package.")
        # package level - show all resource types of this package
        if len(request.postpath)==4:
            urls = self.registry.getResourceTypeURLs(package_id, 
                                                     base=self.mapping_url)
            return {'mapping': urls}
        # test if valid resource type
        resourcetype_id = request.postpath[4]
        if not self.registry.isResourceTypeId(package_id, resourcetype_id):
            raise ProcessorError(http.FORBIDDEN, "Invalid resource type.")
        # resource type level - show all schemas named after label
        if len(request.postpath)==5:
            # query catalog for schemas
            objs = self.registry.schemas.get(package_id=package_id,
                                             resourcetype_id=resourcetype_id)
            ids = [obj.type for obj in objs]
            ids.sort()
            urls = addBaseToList('/'.join(request.postpath[0:5]), ids)
            return {'resource': urls}
        # direct resource request
        obj = self.registry.schemas.get(package_id=package_id,
                                        resourcetype_id=resourcetype_id,
                                        type=request.postpath[5])
        if not obj:
            raise ProcessorError(http.NOT_FOUND, "Schema not found.")
        return obj[0].getResource().document.data
    
    def processDELETE(self, request):
        """Process a DELETE request at the mapping_url."""
        if len(request.postpath)!=6:
            raise ProcessorError(http.BAD_REQUEST, "Invalid request.")
        # test if valid resource type
        if not self.registry.isResourceTypeId(request.postpath[3],
                                              request.postpath[4]):
            raise ProcessorError(http.FORBIDDEN, "Invalid resource type.")
        # direct resource request
        try:
            self.registry.schemas.delete(package_id=request.postpath[3],
                                         resourcetype_id=request.postpath[4],
                                         type=request.postpath[5])
        except Exception, e:
            self.log.info("Error deleting schemas", e)
            raise ProcessorError(http.INTERNAL_SERVER_ERROR, e)
    
    def processPUT(self, request):
        """Process a PUT request at the mapping_url."""
        if len(request.postpath)!=6:
            raise ProcessorError(http.BAD_REQUEST, "Invalid request.")
        # test if valid resource type
        if not self.registry.isResourceTypeId(request.postpath[3],
                                              request.postpath[4]):
            raise ProcessorError(http.FORBIDDEN, "Invalid resource type.")
        # check if a non integer id for file name
        if isInteger(request.postpath[5][0]):
            raise ProcessorError(http.FORBIDDEN, "Resource name must not " + \
                                 "start with an integer.")
        # direct resource request
        try:
            self.registry.schemas.register(request.postpath[3],
                                           request.postpath[4],
                                           request.postpath[5],
                                           request.data)
        except Exception, e:
            self.log.error("Error adding schemas", e)
            raise ProcessorError(http.INTERNAL_SERVER_ERROR, e)
        return self.mapping_url + '/'.join(request.postpath[3:])
    
    def processPOST(self, request):
        """Process a POST request at the mapping_url."""
        self.processDELETE(request)
        return self.processPUT(request)
