# -*- coding: utf-8 -*-
import sys
import os

from seishub.core import PackageManager
from seishub.util.text import from_uri
from seishub.db.util import DbStorage, IntegrityError
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
        self.log = env.log
        
    def init_registration(self):
        """add pre-registered items to the registry"""
        for item in self._registry:
            package = item[0]
            resourcetype = item[1]
            type = item[3]
            try:
                data = file(item[2], 'r').read()
                self.register(package, resourcetype, type, data)
            except IntegrityError, e:
                pass
                # XXX: check if already registered
#                o = self.get(package, resourcetype, type)[0]
#                if not o.resource.data == data:
#                    # XXX: perform update
#                    pass 
            except Exception, e:
                self.log.warn('Registration failed for: %s (%s)' % (item[2],e))
                continue
            
    def register(self, package_id, resourcetype_id, type, xml_data):
        res = self.catalog.addResource(self.package_id, self.resourcetype_id, 
                                       xml_data)
        try:
            o = self.cls(package_id, resourcetype_id, type, res.uid)
            self.store(o)
        except:
            self.catalog.deleteResource(res.uid)
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
    
    def delete(self, uid):
        self.catalog.deleteResource(uid)
        self.drop(self.cls, uid = uid)
        return True
    

class SchemaRegistry(Registry):
    _registry = list()
    
    db_tables = {Schema: schema_tab}
    db_mapping = {Schema:
                 {'resourcetype_id':'resourcetype_id',
                  'package_id':'package_id',
                  'type':'type',
                  'uid':'uid'}
                  }
    cls = Schema
    package_id = "seishub"
    resourcetype_id = "schema"
    
    @staticmethod
    def _pre_register(type, filename):
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
        path = os.path.join(os.path.dirname(frame.f_code.co_filename),filename)
        SchemaRegistry._registry.append([package_id, resourcetype_id, 
                                         path, type])

registerSchema = SchemaRegistry._pre_register


class StylesheetRegistry(Registry):
    _registry = list()
    
    db_tables = {Stylesheet:stylesheet_tab}
    db_mapping = {Stylesheet:
              {'resourcetype_id':'resourcetype_id',
               'package_id':'package_id',
               'type':'type',
               'uid':'uid'}
               }
    cls = Stylesheet
    package_id = "seishub"
    resourcetype_id = "stylesheet"

    @staticmethod
    def _pre_register(type, filename):
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
        path = os.path.join(os.path.dirname(frame.f_code.co_filename),filename)
        StylesheetRegistry._registry.append([package_id, resourcetype_id, 
                                             path, type])
        
registerStylesheet = StylesheetRegistry._pre_register


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
        self.drop(self.cls,
                  package_id = package_id,
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
        """add pre-registered items to the registry"""
        for item in self._registry:
            package = item[0]
            resourcetype = item[1]
            name = item[2]
            query = item[3]
#            limit = item[4]
#            order_by = item[5]
            try:
                self.register(package, resourcetype, name, query)
            except IntegrityError, e:
                pass
                # XXX: check if already registered 
            except Exception, e:
                self.log.warn('Registration failed for: %s (%s)' % (item[2],e))
                continue

registerAlias = AliasRegistry._pre_register
