# -*- coding: utf-8 -*-

from seishub.core import PackageManager
from seishub.db.util import DbStorage
from seishub.packages.interfaces import IPackage, IResourceType
from seishub.packages.defaults import schema_tab, stylesheet_tab, alias_tab
from seishub.packages.alias import Alias
from seishub.packages.schema import Schema
from seishub.packages.stylesheet import Stylesheet


class PackageRegistry(object):
    def __init__(self, env):
        self.env = env
        self.stylesheets = StylesheetRegistry(self.env)
        self.schemas = SchemaRegistry(self.env)
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
    
    def getResourceTypes(self, package_id = None):
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
    def __init__(self, env):
        super(DbStorage, self).__init__(env.db)
        self.catalog = env.catalog
    
    # overloaded method from DbStorage
    def getMapping(self, table):
        return {'resourcetype_id':'resourcetype_id',
                'package_id':'package_id',
                'type':'type',
                'uid':'uid'}
    
    def register(self, package_id, resourcetype_id, type, xml_data):
        res = self.catalog.addResource("seishub", "schema", xml_data)
        o = self.cls(package_id, resourcetype_id, type, res.uid)
        self.store(o)
        return True
    
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
    
    def delete(self, uid):
        self.catalog.deleteResource(uid)
        self.drop(uid = uid)
        return True
    

class SchemaRegistry(Registry):
    db_tables = [schema_tab]
    cls = Schema
    

class StylesheetRegistry(Registry):
    db_tables = [stylesheet_tab]
    cls = Stylesheet
    

class AliasRegistry(DbStorage):
    db_tables = [alias_tab]
    cls = Alias
    
    # overloaded method from DbStorage
    def getMapping(self, table):
        return {'resourcetype_id':'resourcetype_id',
                'package_id':'package_id',
                'name':'name',
                'expr':'expr'}
    
    def register(self, package_id, resourcetype_id, name, expr):
        o = self.cls(package_id, resourcetype_id, name, expr)
        self.store(o)
        return True
    
    def get(self, package_id = None, resourcetype_id = None, 
                  name = None, expr = None):
        keys = {'package_id':package_id,
                'resourcetype_id':resourcetype_id,
                'name':name,
                'expr':expr}
        objs = self.pickup(self.cls, **keys)
        if not objs:
            return list()
        if not isinstance(objs, list):
            objs = [objs]
        return objs
    
    def delete(self, package_id, resourcetype_id, name):
        self.drop(package_id = package_id,
                  resourcetype_id = resourcetype_id,
                  name = name)
        return True

