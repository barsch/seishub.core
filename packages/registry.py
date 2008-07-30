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

class PackageListDesc(object):
    # provide registry.packages with an updated package list on every access
    def __get__(self, obj, objtype):
        return PackageList(obj.getEnabledPackageIds(), obj)
    
    
class PackageList(list):
    def __init__(self, values, registry):
        list.__init__(self, values)
        self._registry = registry
        
    def __getitem__(self, key):
        return self.get(key)
        
    def get(self, package_id):
        return self._registry.getComponents(IPackage, package_id)[0]
        

class PackageRegistry(DbStorage):  
    packages = PackageListDesc()
    
    def __init__(self, env):
        DbStorage.__init__(self, env.db)
        self.env = env
        self.stylesheets = StylesheetRegistry(self)
        self.schemas = SchemaRegistry(self)
        self.aliases = AliasRegistry(self)
        
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
    
    def objects_from_id(self, package_id, resourcetype_id):
        package = None
        resourcetype = None
        if not package_id:
            return package, resourcetype
        package = self.db_getPackage(package_id)
        if not package:
            raise SeisHubError('Package not present in database: %s' %\
                               str(package_id))
        if not resourcetype_id:
            return package, resourcetype
        resourcetype = self.db_getResourceType(package_id, 
                                                        resourcetype_id)
        if not resourcetype:
            raise SeisHubError('Resourcetype not present in database: %s', 
                               str(package_id))
        return package, resourcetype
    
    # methods for database registration of packages
    def db_registerPackage(self, package_id, version = ''):
        o = PackageWrapper(package_id, version)
        self.store(o)
        return o
        
    def db_getPackages(self, package_id = None):
        kwargs = dict()
        if package_id:
            kwargs['package_id'] = package_id
        return self.pickup(PackageWrapper, **kwargs)
    
    def db_getPackage(self, package_id):
        try:
            return self.db_getPackages(package_id)[0]
        except IndexError:
            return None
        
    def db_deletePackage(self, package_id):
        #XXX: workaround to check if there are any dependencies on this object
        # as not all dbs are supporting foreign keys
        if not self._is_package_deletable(package_id):
            raise SeisHubError(("Package with id '%s' cannot be deleted due "+\
                               "to other objects depending on it.") %\
                                (str(package_id)))
        self.drop(PackageWrapper, package_id = package_id)
        #except IntegrityError:
        #    raise SeisHubError(("Package with id '%s' cannot be deleted due "+\
        #                       "to other objects depending on it.") %\
        #                        (str(package_id)))
        
    def db_registerResourceType(self, resourcetype_id, package_id, 
                                version = '', version_control = False):
        try:
            package = self.db_getPackages(package_id)[0]
        except IndexError:
            raise SeisHubError('Package not present in database: %s' %\
                               str(package_id))
        o = ResourceTypeWrapper(resourcetype_id, package, 
                                version, version_control)
        self.store(o)
        return o
        
    def db_getResourceTypes(self, package_id = None, resourcetype_id = None):
        kwargs = dict()
        if resourcetype_id:
            kwargs['resourcetype_id'] = resourcetype_id
        if package_id:
            kwargs['package'] = {'package_id':package_id}
        rt = self.pickup(ResourceTypeWrapper, **kwargs)
        return rt
    
    def db_getResourceType(self, package_id, resourcetype_id):
        try:
            return self.db_getResourceTypes(package_id, resourcetype_id)[0]
        except IndexError:
            return None
        
    def db_deleteResourceType(self, package_id, resourcetype_id):
        # XXX: workaround to check if there are any dependencies on this object
        # as not all dbs are supporting foreign keys
        if not self._is_resourcetype_deletable(package_id, resourcetype_id):
            raise SeisHubError(("Resourcetype with id '%s' in package '%s' "+\
                                "cannot be deleted due to other objects " +\
                                "depending on it.") %\
                                (str(resourcetype_id), str(package_id)))
        kwargs = dict()
        package = self.db_getPackages(package_id)[0]
        if not package:
            raise SeisHubError('Package not present in database: %s', 
                               str(package_id))
        kwargs['package'] = package
        kwargs['resourcetype_id'] = resourcetype_id
        self.drop(ResourceTypeWrapper, **kwargs)
        
    def _is_package_deletable(self, package_id):
        try:
            p = self.db_getPackages(package_id)[0]
        except IndexError:
            raise SeisHubError('Package not present in database: %s', 
                               str(package_id))
        # check if any resourcetype is present:
        resourcetypes = self.db_getResourceTypes(package_id)
        if len(resourcetypes) > 0:
            return False
        # XXX: check if schemas/stylesheets or aliases are present:
        # XXX: check if any catalog entries are present
        return True
    
    def _is_resourcetype_deletable(self, package_id, resourcetype_id):
        try:
            rt = self.db_getResourceTypes(package_id, resourcetype_id)[0] 
        except IndexError:
            raise SeisHubError("Resourcetype with id '%s' in package '%s' "+\
                               "not present in database!", 
                               (str(resourcetype_id), str(package_id)))
        # XXX: check if schemas/stylesheets or aliases are present:
        # XXX: check if any catalog entries are present
        return True


class RegistryBase(DbStorage):
    """base class for StylesheetRegistry, SchemaRegistry and AliasRegistry"""
    def __init__(self, registry):
        super(DbStorage, self).__init__(registry.env.db)
        self.catalog = registry.env.catalog
        self.log = registry.env.log
        self.registry = registry
            
    def register(self, package_id, resourcetype_id, type, xml_data):
        package, resourcetype = self.registry.objects_from_id(package_id, resourcetype_id)
        res = self.catalog.addResource(self.package_id, self.resourcetype_id, 
                                       xml_data)
        try:
            o = self.cls(package, resourcetype, type, res.resource_id)
            self.store(o)
        except:
            self.catalog.deleteResource(self.package_id, 
                                        self.resourcetype_id, 
                                        res.resource_id)
            raise
        return True
    
    def update(self, package_id, resourcetype_id, type, xml_data):
        pass
    
    def get(self, package_id = None, resourcetype_id = None, 
                  type = None, uid = None):
        # get package and resourcetype first
        #package, resourcetype = self.registry.objects_from_id(package_id, resourcetype_id)
        keys = {'type':type,
                'uid':uid}
        if package_id:
            keys['package'] = {'package_id' : package_id}
        if resourcetype_id:
            keys['resourcetype'] = {'resourcetype_id' : resourcetype_id}
        objs = self.pickup(self.cls, **keys)
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
    
    cls = Schema
    package_id = "seishub"
    resourcetype_id = "schema"


class StylesheetRegistry(RegistryBase):
    _registry = list()

    cls = Stylesheet
    package_id = "seishub"
    resourcetype_id = "stylesheet"


class AliasRegistry(RegistryBase):
    _registry = list()
    cls = Alias
    
    def _split_uri(self, uri):
        args = list(from_uri(uri))
        if args[2].startswith('@'):
            args[2] = args[2][1:]
        return args
        
    def register(self, package_id, resourcetype_id, name, expr, limit = None,
                 order_by = None):
        package, resourcetype = self.registry.objects_from_id(package_id, resourcetype_id)
        o = self.cls(package, resourcetype, name, expr)
        self.store(o)
        return True
    
    def get(self, package_id = None, resourcetype_id = None, 
                  name = None, expr = None):
        keys = {'name':name,
                'expr':expr}
        null = ['resourcetype']
        if package_id:
            keys['package'] = {'package_id' : package_id}
            keys['resourcetype'] = None
            if resourcetype_id:
                keys['resourcetype'] = {'resourcetype_id' : resourcetype_id}
        objs = self.pickup(self.cls, _null = null, **keys)
        return objs
    
    def delete(self, package_id = None, resourcetype_id = None, name = None, 
               uri = None):
        if uri:
            package_id, resourcetype_id, name = self._split_uri(uri)
        package, resourcetype = self.registry.objects_from_id(package_id, resourcetype_id)
        null = list()
        if package:
            null = ['resourcetype_id']
        self.drop(self.cls,
                  package = package,
                  resourcetype = resourcetype,
                  name = name,
                  _null = null)
        return True
        