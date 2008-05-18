# -*- coding: utf-8 -*-

from defaults import schema_tab, stylesheet_tab
from seishub.core import PackageManager
from seishub.db.util import DbStorage, Serializable
from seishub.packages.interfaces import IPackage, IResourceType


class PackageRegistry(object):
    def __init__(self, env):
        self.env = env
        self.stylesheets = StylesheetRegistry(self.env.db)
        self.schemas = SchemaRegistry(self.env.db)
        self.aliases = AliasRegistry(self.env.db)
        
    def getComponents(self, interface, package_id = None):
        components = PackageManager.getComponents(interface, package_id, 
                                                  self.env)
        return components
    
    def getPackageIds(self):
        """Returns sorted dict of all packages."""
        packages = self.getComponents(IPackage)
        packages = [str(p.package_id) for p in packages]
        packages.sort()
        return packages
    
    def getResourceTypes(self, package_id=None):
        """
        Returns sorted dict of all resource types, optional filtered by a 
        package id.
        """
        components = self.getComponents(IResourceType, package_id)
        resourcetypes = {}
        for c in components:
            id = c.resourcetype_id
            resourcetypes[id] = c
        return resourcetypes


class Registry(DbStorage):
    # overloaded methods from DbStorage
    def getMapping(self, table):
        return {'resourcetype_id':'resourcetype_id',
                'package_id':'package_id',
                'type':'type',
                'uri':'uri'}
    
    # methods from IResourceStorage
    def register(self, package_id, resourcetype_id, type, uri):
        o = self.cls(package_id, resourcetype_id, type, uri)
        self.store(o)
        return True
    
    def get(self, package_id = None, resourcetype_id = None, 
                  type = None, uri = None):
        o = self.cls()
        keys = {'package_id':package_id,
                'resourcetype_id':resourcetype_id,
                'type':type,
                'uri':uri}
        self.pickup(o, **keys)
        return o
    
    def delete(self, uri):
        self.drop(uri = uri)
        return True


class Schema(Serializable):
    def __init__(self, package_id = None, resourcetype_id = None, 
                 type = None, uri = None):
        super(Serializable, self).__init__()
        self.package_id = package_id
        self.resourcetype_id = resourcetype_id
        self.type = type
        self.uri = uri
    
    def getFields(self):
        return {'resourcetype_id':self.resourcetype_id,
                'package_id':self.package_id,
                'type':self.type,
                'uri':self.uri
                }
    
    def getResourceTypeId(self):
        return self._resourcetype_id
     
    def setResourceTypeId(self, data):
        self._resourcetype_id = data
        
    resourcetype_id = property(getResourceTypeId, setResourceTypeId, 
                               "Resource type id")
    
    def getPackageId(self):
        return self._package_id
    
    def setPackageId(self, data):
        self._package_id = data
        
    package_id = property(getPackageId, setPackageId, "Package id")
    
    def getUri(self):
        return self._uri
    
    def setUri(self, data):
        self._uri = data
        
    uri = property(getUri, setUri, "Uri")
    
    def getType(self):
        return self._type
    
    def setType(self, data):
        self._type = data
    
    type = property(getType, setType, "Type")
    

class Stylesheet(Schema):
    pass


class SchemaRegistry(Registry):
    db_tables = [schema_tab]
    cls = Schema

    
class StylesheetRegistry(Registry):
    db_tables = [stylesheet_tab]
    cls = Stylesheet
    

class AliasRegistry(DbStorage):
    pass


class Alias(Serializable):
    pass 