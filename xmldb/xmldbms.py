# -*- coding: utf-8 -*-

from zope.interface import implements
from twisted.enterprise import util as dbutil

from seishub.defaults import DEFAULT_PREFIX,RESOURCE_TABLE, \
                             INDEX_TABLE,METADATA_TABLE, \
                             METADATA_INDEX_TABLE, URI_TABLE
from seishub.defaults import ADD_RESOURCE_QUERY, DELETE_RESOURCE_QUERY, \
                             REGISTER_URI_QUERY, REMOVE_URI_QUERY, \
                             GET_NEXT_ID_QUERY, GET_ID_BY_URI_QUERY, \
                             QUERY_STR_MAP, GET_RESOURCE_BY_URI_QUERY
from seishub.core import SeisHubError
                       
from seishub.xmldb.interfaces import IResourceStorage, IXmlIndex
from seishub.xmldb.xmlresource import XmlResource

__all__=['XMLDBManager']

class DbError(SeisHubError):
    pass

class UnknownUriError(SeisHubError):
    pass

class XmlDbManagerError(SeisHubError):
    pass

class XmlDbManager(object):
    """XmlResource layer, connects XmlResources to relational db storage"""
    implements(IResourceStorage)
    
    def __init__(self,adbapi_connection):
        if not hasattr(adbapi_connection,'runInteraction'):
            raise TypeError("adbapi connector expected!")
            self.db=None
        else:
            self.db=adbapi_connection
        
    def addResource(self,xml_resource):
        """Add a new resource to the storage
        
        return: A Deferred which will fire a Failure on error"""
        def _addResourceTxn(txn):
            # get next unique id:
            get_next_id_query=GET_NEXT_ID_QUERY % (DEFAULT_PREFIX,
                                                   RESOURCE_TABLE)
            txn.execute(get_next_id_query)
            next_id=txn.fetchall()[0][0]
            # insert into RESOURCE_TABLE:
            add_res_query=ADD_RESOURCE_QUERY % (DEFAULT_PREFIX,RESOURCE_TABLE,
                                                next_id,
                                                dbutil.quote(xml_resource.getData(),
                                                             "text"))
            txn.execute(add_res_query)
            # register uri
            txn.execute(REGISTER_URI_QUERY % (DEFAULT_PREFIX,URI_TABLE,
                                              next_id,
                                              dbutil.quote(xml_resource.getUri(),
                                                           "text")))
            return next_id
        
        # perform this as a transaction to avoid a race condition between two 
        # requests trying to add a resource with the same uri at the same time
        d=self.db.runInteraction(_addResourceTxn)
        return d
    
    def getResource(self,uri):
        """Get a resource by it's uri from the database.
        return: Deferred returning a XmlResource on success
        """
        
        map_str=QUERY_STR_MAP
        map_str['uri']=uri
        query=GET_RESOURCE_BY_URI_QUERY % map_str
        
        def _procResults(results,uri):
            xml_data=results[0][0]
            return XmlResource(xml_data=xml_data,uri=uri)
        
        d=self.db.runQuery(query).addCallback(_procResults,uri)
        return d
    
    def deleteResource(self,uri):
        """Remove a resource from the database.
        return: Deferred which will fire a Failure on error.
        """
        def _delResourceTxn(txn):
            str_map=QUERY_STR_MAP
            str_map['uri']=uri
            
            #get res_id:
            get_id_query=GET_ID_BY_URI_QUERY % str_map
            txn.execute(get_id_query)
            res_id=txn.fetchall()[0][0]
            
            #remove uri
            remove_uri_query=REMOVE_URI_QUERY % str_map
            txn.execute(remove_uri_query)
            
            #delete from resource table
            str_map['res_id']=res_id
            del_res_query=DELETE_RESOURCE_QUERY % str_map
            txn.execute(del_res_query)
            
            return res_id
        
        d=self.db.runInteraction(_delResourceTxn)
        return d
    
    def _resolveUri(self,uri):
        if not isinstance(uri,basestring):
            raise ValueError("invalid uri: string expected")
            return None
        
        str_map=QUERY_STR_MAP
        str_map['uri']=uri
        query=GET_ID_BY_URI_QUERY % str_map
        
        def _procResults(res):
            if len(res) == 1 and len(res[0]) == 1:
                id=res[0][0]
            else:
                raise UnknownUriError("%s is not present in storage." % uri)
                id=None
            return id
        
        d=self.db.runQuery(query)
        d.addCallback(_procResults)
        return d
        
        
        
        