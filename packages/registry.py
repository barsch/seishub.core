# -*- coding: utf-8 -*-
import sys
import os

from seishub.core import PackageManager, SeisHubError
from seishub.util.text import from_uri
from seishub.db.util import DbStorage
from sqlalchemy.exceptions import IntegrityError #@UnresolvedImport
from seishub.packages.interfaces import IPackage, IResourceType
from seishub.packages.defaults import schema_tab, stylesheet_tab, alias_tab, \
                                      packages_tab, resourcetypes_tab
from seishub.packages.package import PackageWrapper, ResourceTypeWrapper, \
                                     Alias, Schema, Stylesheet

class PackageDesc(object):
    # provide registry.packages with an updated package list on every access
    def __get__(self, obj, objtype):
        return PackageList(obj.getEnabledPackageIds(), obj)
    
    
class PackageList(list):
    def __init__(self, values, registry):
        list.__init__(self, values)
        self._registry = registry
        
    def get(self, package_id):
        return self._registry.getComponents(IPackage, package_id)[0]
        

class PackageRegistry(DbStorage):
    db_tables = {PackageWrapper: packages_tab,
                 ResourceTypeWrapper: resourcetypes_tab}
    db_mapping = {PackageWrapper: {
                      'package_id':'name',
                      'version':'version',
                      '_id':'id'
                  },
                  ResourceTypeWrapper: {
                      'resourcetype_id':'name',
                      'package._id':'package_id',
                      'version':'version',
                      'version_control':'version_control',
                  }}
    
    packages = PackageDesc()
    
    def __init__(self, env):
        DbStorage.__init__(self, env.db)
        self.env = env
        self.stylesheets = StylesheetRegistry(self.env)
        self.schemas = SchemaRegistry(self.env)
        self.aliases = AliasRegistry(self.env.db)
        
    def getComponents(self, interface, package_id = None):
        """Returns components implementing a certain interface with given 
        package id"""
        components = PackageManager.getComponents(interface, package_id, 
                                                  self.env)
        return components
    
#    def getPackageIds(self):
#        """Returns sorted list of all packages."""
#        # XXX: to be removed
#        packages = self.getComponents(IPackage)
#        packages = [str(p.package_id) for p in packages]
#        packages.sort()
#        return packages

    def getEnabledPackageIds(self):
        """Returns sorted list of all enabled packages"""
        all = PackageManager.getPackageIds()
        enabled = [id for id in all if self.env.isComponentEnabled \
                                  (PackageManager.getClasses(IPackage, id)[0])]
        enabled.sort()
        return enabled
    
    def getResourceTypes(self, package_id = None):
        """
        Returns sorted list of all resource types, optionally filtered by a 
        package id.
        """
        components = self.getComponents(IResourceType, package_id)
        resourcetypes = {}
        for c in components:
            id = c.resourcetype_id
            resourcetypes[id] = c
        return resourcetypes
    
    # methods for database registration of packages
    def registerPackage(self, package_id, version):
        o = PackageWrapper(package_id, version)
        self.store(o)
        
    def getPackage(self, package_id):
        try:
            return self.pickup(PackageWrapper, package_id = package_id)[0]
        except IndexError:
            return None
        
    def deletePackage(self, package_id):
        # XXX: check if any object with package id is present
        # or do this via ForeignKey
        try:
            self.drop(PackageWrapper, package_id = package_id)
        except IntegrityError:
            raise SeisHubError(("Package with id '%s' cannot be deleted due "+\
                               "to other objects depending on it.") %\
                                (str(package_id)))
        
    def registerResourcetype(self, resourcetype_id, package_id, version, 
                             version_control = False):
        package = self.getPackage(package_id)
        if not package:
            raise SeisHubError('Package not present in database: %s', 
                               str(package_id))
        o = ResourceTypeWrapper(resourcetype_id, package, 
                                version, version_control)
        self.store(o)
        
    def getResourcetype(self, package_id, resourcetype_id):
        package = self.getPackage(package_id)
        if not package:
            raise SeisHubError('Package not present in database: %s', 
                               str(package_id))
        try:
            rt = self.pickup(ResourceTypeWrapper, 
                             package_id = package._id,
                             resourcetype_id = resourcetype_id)[0]
        except IndexError:
            return None
        rt.package = package
        return rt
        
    def deleteResourcetype(self, package_id, resourcetype_id):
        # XXX: only delete if no object is present anymore => ForeignKey
        package = self.getPackage(package_id)
        if not package:
            raise SeisHubError('Package not present in database: %s', 
                               str(package_id))
        self.drop(ResourceTypeWrapper, package_id = package._id,
                  resourcetype_id = resourcetype_id)
    

class RegistryBase(DbStorage):
    """base class for StylesheetRegistry and SchemaRegistry"""
    def __init__(self, env):
        super(DbStorage, self).__init__(env.db)
        self.catalog = env.catalog
        self.log = env.log
    
    db_tables = {Schema: schema_tab}
    db_mapping = {Schema:
                 {'resourcetype_id':'resourcetype_id',
                  'package_id':'package_id',
                  'type':'type',
                  'resource_id':'resource_id'}
                  }
            
    def register(self, package_id, resourcetype_id, type, xml_data):
        res = self.catalog.addResource(self.package_id, self.resourcetype_id, 
                                       xml_data)
        try:
            o = self.cls(package_id, resourcetype_id, type, res.resource_id)
            self.store(o)
        except:
            self.catalog.deleteResource(res.info.package_id, 
                                        res.info.resourcetype_id, 
                                        res.info.id)
            raise
        return True
    
    def update(self, package_id, resourcetype_id, type, xml_data):
        pass
    
    def get(self, package_id = None, resourcetype_id = None, 
                  type = None, uid = None):
        keys = {'package_id':package_id,
                'resourcetype_id':resourcetype_id,
                'type':type,
                'uid':uid}
        objs = self.pickup(self.cls, **keys)
        if not objs:
            return list()
        if not isinstance(objs, list):
            objs = [objs]
        # inject catalog into objs for lazy resource retrieval
        for o in objs:
            o._catalog = self.catalog
        return objs
    
    def delete(self, package_id, resourcetype_id, type):
        o = self.get(package_id, resourcetype_id, type)[0]
        self.catalog.xmldb.deleteResource(resource_id = o.resource_id)
        self.drop(self.cls, resource_id = o.resource_id)
        return True
    

class SchemaRegistry(RegistryBase):
    _registry = list()
    
    db_tables = {Schema: schema_tab}
    db_mapping = {Schema:
                 {'resourcetype_id':'resourcetype_id',
                  'package_id':'package_id',
                  'type':'type',
                  'resource_id':'resource_id'}
                  }
    cls = Schema
    package_id = "seishub"
    resourcetype_id = "schema"


class StylesheetRegistry(RegistryBase):
    _registry = list()
    
    db_tables = {Stylesheet:stylesheet_tab}
    db_mapping = {Stylesheet:
              {'resourcetype_id':'resourcetype_id',
               'package_id':'package_id',
               'type':'type',
               'resource_id':'resource_id'}
               }
    cls = Stylesheet
    package_id = "seishub"
    resourcetype_id = "stylesheet"


class AliasRegistry(DbStorage):
    _registry = list()
    
    db_tables = {Alias:alias_tab}
    db_mapping = {Alias:
             {'resourcetype_id':'resourcetype_id',
              'package_id':'package_id',
              'name':'name',
              'expr':'expr'}
             }
    cls = Alias
    
    def _split_uri(self, uri):
        args = list(from_uri(uri))
        if args[2].startswith('@'):
            args[2] = args[2][1:]
        return args
        
    def register(self, package_id, resourcetype_id, name, expr, limit = None,
                 order_by = None):
        package_id = package_id or None
        resourcetype_id = resourcetype_id or None
        o = self.cls(package_id, resourcetype_id, name, expr)
        self.store(o)
        return True
    
    def get(self, package_id = None, resourcetype_id = None, 
                  name = None, expr = None):
        package_id = package_id or None
        resourcetype_id = resourcetype_id or None
        keys = {'package_id':package_id,
                'resourcetype_id':resourcetype_id,
                'name':name,
                'expr':expr}
        null = list()
        if package_id:
            null = ['resourcetype_id']
        objs = self.pickup(self.cls, _null = null, **keys)
        if not objs:
            return list()
        if not isinstance(objs, list):
            objs = [objs]
        return objs
    
    def delete(self, package_id = None, resourcetype_id = None, name = None, 
               uri = None):
        if uri:
            package_id, resourcetype_id, name = self._split_uri(uri)
        package_id = package_id or None
        resourcetype_id = resourcetype_id or None
        null = list()
        if package_id:
            null = ['resourcetype_id']
        self.drop(self.cls,
                  package_id = package_id,
                  resourcetype_id = resourcetype_id,
                  name = name,
                  _null = null)
        return True
        