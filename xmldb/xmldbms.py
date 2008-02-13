# -*- coding: utf-8 -*-

from zope.interface import implements
from sqlalchemy import select
from sqlalchemy.sql import and_

from seishub.xmldb.interfaces import IResourceStorage
from seishub.xmldb.xmlresource import XmlResource
from seishub.xmldb.errors import *
from seishub.xmldb.defaults import metadata, resource_tab, uri_tab

class XmlDbManager(object):
    """XmlResource layer, connects XmlResources to relational db storage"""
    implements(IResourceStorage)
    
    def __init__(self, db):
        self.db = db.engine
        self.metadata = db.metadata = metadata
        self._initDb()
        metadata.bind = db.engine
        
    def _initDb(self):
        #create all tables
        #this will check for the presence of a table first before creating
        self.metadata.create_all(self.db, checkfirst=True)
    
    def _resolveUri(self,uri):
        if not isinstance(uri,basestring):
            raise ValueError("invalid uri: string expected")
            return
        
        query = select([uri_tab.c.res_id],
                       uri_tab.c.uri == uri)
        res = self.db.execute(query)
        try:
            id = res.fetchone()[0]
        except:
            raise UnknownUriError(uri)
            return None
        
        return id
    
    # methods from IResourceStorage            
    def addResource(self,xml_resource):
        """Add a new resource to the storage
        @return: Boolean"""
        conn = self.db.connect()
        
        # begin transaction:
        txn = conn.begin()
        try:
            res = conn.execute(resource_tab.insert(),
                               data = xml_resource.getData())
            conn.execute(uri_tab.insert(), 
                         uri = xml_resource.getUri(),
                         res_id = res.last_inserted_ids()[0],
                         res_type = xml_resource.getResource_type())
            txn.commit()
        except Exception, e:
            txn.rollback()
            raise
        
        return True
    
    def getResource(self, uri):
        """Get a resource by it's uri from the database.
        @return: XmlResource or None
        """
        # TODO: bypass xml parsing on resource retrieval
        query = select([resource_tab.c.data],
                       and_(
                            resource_tab.c.id == uri_tab.c.res_id,
                            uri_tab.c.uri == uri
                       ))
        res = self.db.execute(query)
        try:
            xml_data = res.fetchone()[0]
        except:
            raise UnknownUriError(uri)
            return None
        
        return XmlResource(xml_data = xml_data, uri = uri)
    
    def deleteResource(self,uri):
        """Remove a resource from the storage.
        @return: True on success
        """
        res_id = self._resolveUri(uri)
        if not id:
            return
        
        conn = self.db.connect()
        
        # begin transaction:
        txn = conn.begin()
        try:
            # remove uri first:
            conn.execute(uri_tab.delete(uri_tab.c.uri == uri))
            # then remove data:
            conn.execute(resource_tab.delete(resource_tab.c.id == res_id))
            txn.commit()
        except Exception, e:
            txn.rollback()
            raise
        
        return True
    
    def getUriList(self,type = None):
        w = None
        if type:
            w = uri_tab.c.res_type == type
        query = select([uri_tab.c.uri], w)
        try:
            res = self.db.execute(query)
            uris = res.fetchall()
        except:
            return list()
        
        return [uri[0] for uri in uris]
