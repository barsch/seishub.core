# -*- coding: utf-8 -*-
from defaults import *
from seishub.core import PackageManager
from seishub.db.util import DbStorage, Serializable

class PackageRegistry(object):
    def __init__(self, env):
        self.env = env
        self.stylesheets = StylesheetRegistry(self.env.db)
        self.schemas = SchemaRegsitry(self.env.db)
        self.aliases = AliasRegistry(self.env.db)
        
    def getComponents(self, interface, package_id = None):
        components = PackageManager.getComponents(interface, package_id, 
                                                  self.env)
        return components


class SchemaRegsitry(DbStorage):
    db_tables = [schema_tab]
    
    # overloaded methods from DbStorage
    def getMapping(self, table):
        if table == schema_tab:
            return {'resourcetype_id':'resourcetype_id',
                    'package_id':'package_id',
                    'type':'type',
                    'uri':'uri'}
    
    # methods from IResourceStorage
    def registerSchema(self, package_id, resourcetype_id, type, uri):
        schema = Schema(package_id, resourcetype_id, type, uri)
        self.store(schema)
        return True
    
    def getSchema(self, package_id = None, resourcetype_id = None, 
                  type = None, uri = None):
        schema = Schema()
        keys = {'package_id':package_id,
                'resourcetype_id':resourcetype_id,
                'type':type,
                'uri':uri}
        self.pickup(schema, **keys)
        return schema
    
    def deleteSchema(self, uri):
        self.drop(uri = uri)
        return True
    
class StylesheetRegistry(DbStorage):
    pass


class AliasRegistry(DbStorage):
    pass


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


class Alias(Serializable):
    pass 