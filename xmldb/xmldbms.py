# -*- coding: utf-8 -*-

from zope.interface import implements
from sqlalchemy import select
from sqlalchemy.sql import and_

from seishub.xmldb.interfaces import IResourceStorage
from seishub.xmldb.util import DbStorage
from seishub.xmldb.xmlresource import XmlResource
from seishub.xmldb.errors import *
from seishub.xmldb.defaults import resource_tab, uri_tab

class XmlDbManager(DbStorage):
    """XmlResource layer, connects XmlResources to relational db storage"""
    implements(IResourceStorage)
    
    # XXX: order of tables is IMPORTANT here!
    db_tables = [resource_tab, uri_tab]
    
    def _resolveUri(self,uri):
        if not isinstance(uri,basestring):
            raise InvalidUriError("string expected")
        
        query = select([uri_tab.c.res_id],
                       uri_tab.c.uri == uri)
        res = self._db.execute(query)
        try:
            id = res.fetchone()[0]
            res.close()
        except:
            raise UnknownUriError(uri)
        
        return id
    
    # overloaded methods from DbStorage
    def getMapping(self, table):
        if table == resource_tab:
            return {'_id':'id',
                    'data':'data'}
        if table == uri_tab:
            return {'_id':'res_id',
                    'uri':'uri',
                    'resource_type':'res_type'}
    
    # methods from IResourceStorage            
    def addResource(self,xml_resource):
        """Add a new resource to the storage
        @return: True on success"""
        try:
            self.store(xml_resource)
        except Exception, e:
            raise AddResourceError(e)
        return True
    
    def getResource(self, uri):
        """Get a resource by it's uri from the database.
        @return: XmlResource or None
        """
        # XXX: bypass xml parsing on resource retrieval
        id = self._resolveUri(uri)
        xml_resource = XmlResource(uri = uri)
        self.pickup(xml_resource, _id = id)
        return xml_resource
    
    def deleteResource(self,uri):
        """Remove a resource from the storage.
        @return: True on success
        """
        id = self._resolveUri(uri)
        try:
            self.drop(_id = id)
        except Exception, e:
            raise DeleteResourceError(e)      
        return True
    
    def getUriList(self,type = None):
        w = None
        if type:
            w = uri_tab.c.res_type == type
        query = select([uri_tab.c.uri], w)
        try:
            res = self._db.execute(query)
            uris = res.fetchall()
        except:
            return list()
        finally:
            res.close()
        return [uri[0] for uri in uris]
    
    def uriExists(self, uri):
        query = select([uri_tab.c.uri],
                       (uri_tab.c.uri == uri))
        try:
            res = self._db.execute(query)
            res.fetchall()[0]
        except:
            return False
        finally:
            res.close()
        return True
