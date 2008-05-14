# -*- coding: utf-8 -*-

from zope.interface import implements
from sqlalchemy import select
from sqlalchemy.sql.expression import ClauseElement

from seishub.db.util import DbEnabled
from seishub.xmldb.errors import RegisterMetaResourceError
from seishub.xmldb.defaults import xsd_tab, xslt_tab

class MetaResourceRegistry(DbEnabled):
    def _setDbTable(self, table):
        self._db_table = table
    
    def registerMetaResource(self, *args, **kwargs):
        uri = args[0]
        kwargs['uri']=uri
        ins = self._db_table.insert()
        try:
            self._db.execute(ins, kwargs)
        except Exception, e:
            raise RegisterMetaResourceError(e)
        return True
    
    def unregisterMetaResource(self, uri):
        w = self._db_table.c.uri == uri
        self._db.execute(self._db_table.delete(w))
        return True
    
    def getMetaResources(self, *args, **kwargs):
        w = "1 = 1"
        for param in kwargs:
            if not kwargs[param]:
                continue
            w += " AND %s = '%s'" % (param, kwargs[param])
        q = select([self._db_table.c.uri], w)
        res = self._db.execute(q)
        try:
            uris = res.fetchall()
        except:
            return list()
        return uris

class SchemaRegistry(MetaResourceRegistry):
    def __init__(self, *args, **kwargs):
        super(MetaResourceRegistry, self).__init__(*args, **kwargs)
        self._setDbTable(xsd_tab)
        
    def registerSchema(self, uri, package_id):
        return self.registerMetaResource(uri, package_id = package_id)
    
    def unregisterSchema(self, uri):
        return self.unregisterMetaResource(uri)
    
    def getSchemata(self, package_id):
        return self.getMetaResources(package_id = package_id)

class StylesheetRegistry(MetaResourceRegistry):
    def __init__(self, *args, **kwargs):
        super(MetaResourceRegistry, self).__init__(*args, **kwargs)
        self._setDbTable(xslt_tab)
        
    def registerStylesheet(self, uri, package_id, format):
        return self.registerMetaResource(uri, 
                                         package_id = package_id,
                                         format = format)
    
    def unregisterStylesheet(self, uri):
        return self.unregisterMetaResource(uri)
    
    def getStylesheets(self, package_id=None, 
                            format=None):
        return self.getMetaResources(package_id = package_id,
                                     format = format)