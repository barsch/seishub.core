# -*- coding: utf-8 -*-
import sys

from seishub.core import PackageManager
from seishub.util.text import from_uri
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
        
    def init_registration(self):
        """initiate registration of pre registered schemas, stylesheets and 
        aliases"""
        self.stylesheets.init_registration()
        self.schemas.init_registration()
        self.aliases.init_registration()
        
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
    
    @staticmethod
    def registerIndex(xpath, type = "text"):
        pass

registerIndex = PackageRegistry.registerIndex

class Registry(DbStorage):
    """base class for StylesheetRegistry and SchemaRegistry"""
    def __init__(self, env):
        super(DbStorage, self).__init__(env.db)
        self.catalog = env.catalog
        
    def init_registration(self):
        """register pre-registered schemas/stylesheets"""
        # check if registration
        
    
    # overloaded method from DbStorage
    def getMapping(self, table):
        return {'resourcetype_id':'resourcetype_id',
                'package_id':'package_id',
                'type':'type',
                'uid':'uid'}
    
    def register(self, package_id, resourcetype_id, type, xml_data):
        res = self.catalog.addResource(self.package_id, self.resourcetype_id, 
                                       xml_data)
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
    _registry = list()
    
    db_tables = [schema_tab]
    cls = Schema
    package_id = "seishub"
    resourcetype_id = "schema"
    
    @staticmethod
    def _pre_register(filename, type):
        """pre-register a schema from filesystem during startup, 
        the schema will be read and registered as soon as the 
        package gets activated"""
        # get package id and reosurcetype_id from calling class
        frame = sys._getframe(1)
        locals_ = frame.f_locals
        # Some sanity checks
        assert locals_ is not frame.f_globals and '__module__' in locals_, \
               'registerStylesheet() can only be used in a class definition'
        package_id = locals_.get('package_id')
        resourcetype_id = locals_.get('resourcetype_id')
        assert package_id and resourcetype_id, 'class must provide package_id'+\
               ' and resourcetype_id attributes'
        
        SchemaRegistry._registry.append([package_id, resourcetype_id, 
                                   filename, type])

registerSchema = SchemaRegistry._pre_register


class StylesheetRegistry(Registry):
    _registry = list()
    
    db_tables = [stylesheet_tab]
    cls = Stylesheet
    package_id = "seishub"
    resourcetype_id = "stylesheet"

    @staticmethod
    def _pre_register(filename, type):
        """pre-register a schema/stylesheet from filesystem during startup, 
        the schema/stylesheet will be read and registered as soon as the 
        package gets activated"""
        # get package id and reosurcetype_id from calling class
        frame = sys._getframe(1)
        locals_ = frame.f_locals
        # Some sanity checks
        assert locals_ is not frame.f_globals and '__module__' in locals_, \
               'registerStylesheet() can only be used in a class definition'
        package_id = locals_.get('package_id')
        resourcetype_id = locals_.get('resourcetype_id')
        assert package_id and resourcetype_id, 'class must provide package_id'+\
               ' and resourcetype_id attributes'
        
        StylesheetRegistry._registry.append([package_id, resourcetype_id, 
                                             filename, type])
        
registerStylesheet = StylesheetRegistry._pre_register


class AliasRegistry(DbStorage):
    _registry = list()
    
    db_tables = [alias_tab]
    cls = Alias
    
    # overloaded method from DbStorage
    def getMapping(self, table):
        return {'resourcetype_id':'resourcetype_id',
                'package_id':'package_id',
                'name':'name',
                'expr':'expr'}
    
    def register(self, package_id, resourcetype_id, name, expr):
        if package_id == '':
            package_id = None
        if resourcetype_id == '':
            resourcetype_id = None
        o = self.cls(package_id, resourcetype_id, name, expr)
        self.store(o)
        return True
    
    def get(self, package_id = None, resourcetype_id = None, 
                  name = None, expr = None):
        if package_id == '':
            package_id = None
        if resourcetype_id == '':
            resourcetype_id = None
        keys = {'package_id':package_id,
                'resourcetype_id':resourcetype_id,
                'name':name,
                'expr':expr}
        if package_id:
            null = ['resourcetype_id']
        else:
            null = list()
        objs = self.pickup(self.cls, null = null, **keys)
        if not objs:
            return list()
        if not isinstance(objs, list):
            objs = [objs]
        return objs
    
    def delete(self, package_id = None, resourcetype_id = None, name = None, 
               uri = None):
        if uri:
            package_id, resourcetype_id, name = from_uri(uri)
        if package_id == '':
            package_id = None
        if resourcetype_id == '':
            resourcetype_id = None
        self.drop(package_id = package_id,
                  resourcetype_id = resourcetype_id,
                  name = name)
        return True
    
    @staticmethod
    def _pre_register(name, query, limit = None, order_by = None):
        """pre-register an alias filesystem based during startup, 
        the alias will be registered as soon as the package gets activated"""
        # get package id and reosurcetype_id from calling class
        frame = sys._getframe(1)
        locals_ = frame.f_locals
        # Some sanity checks
        assert locals_ is not frame.f_globals and '__module__' in locals_, \
               'registerStylesheet() can only be used in a class definition'
        package_id = locals_.get('package_id')
        resourcetype_id = locals_.get('resourcetype_id')
        assert package_id and resourcetype_id, 'class must provide package_id'+\
               ' and resourcetype_id attributes'
               
        AliasRegistry._registry.append([package_id, resourcetype_id, 
                                        name, query, limit, order_by])
        
    def init_registration(self):
        pass

registerAlias = AliasRegistry._pre_register
