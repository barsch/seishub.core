# -*- coding: utf-8 -*-

from zope.interface import implements
from sqlalchemy import select
from sqlalchemy.sql import and_

from seishub.xmldb.interfaces import IResourceStorage
from seishub.xmldb.util import DbEnabled
from seishub.xmldb.xmlresource import XmlResource
from seishub.xmldb.errors import *
from seishub.xmldb.defaults import resource_tab, uri_tab

class XmlDbManager(DbEnabled):
    """XmlResource layer, connects XmlResources to relational db storage"""
    implements(IResourceStorage)
    
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
    
    def _encode(self,data):
        return data.encode("utf-8")
    
    def _decode(self,data):
        return unicode(data, "utf-8")
    
    # methods from IResourceStorage            
    def addResource(self,xml_resource):
        """Add a new resource to the storage
        @return: Boolean"""
        # encode to byte array:
        data = self._encode(xml_resource.getData())
        
        # begin transaction:
        conn = self._db.connect()
        txn = conn.begin()
        
        try:
            res = conn.execute(resource_tab.insert(),
                         data = data)
            #import pdb; pdb.set_trace()
            conn.execute(uri_tab.insert(), 
                         uri = xml_resource.getUri(),
                         res_id = res.last_inserted_ids()[0],
                         res_type = xml_resource.getResource_type())
            txn.commit()
            res.close()
        except Exception, e:
            txn.rollback()
            raise AddResourceError(e)
        finally:
            conn.close()
        
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
        res = self._db.execute(query)
        try:
            xml_data = str(res.fetchone()[0])
        except:
            raise UnknownUriError(uri)
        finally:
            res.close()
        
        # decode to utf-8 string:
        xml_data = self._decode(xml_data)
        
        return XmlResource(xml_data = xml_data, uri = uri)
    
    def deleteResource(self,uri):
        """Remove a resource from the storage.
        @return: True on success
        """
        res_id = self._resolveUri(uri)
        if not id:
            return
        
        conn = self._db.connect()
        
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
            raise DeleteResourceError(e)
        finally:
            conn.close()
        
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
    
