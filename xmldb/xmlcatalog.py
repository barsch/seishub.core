# -*- coding: utf-8 -*-
from zope.interface import implements
from zope.interface.exceptions import DoesNotImplement

from twisted.enterprise import util as dbutil

from seishub.core import SeishubError
from seishub.xmldb.interfaces import IXmlCatalog, IXmlIndex, IXmlResource
from seishub.xmldb.xmlindex import XmlIndex

from seishub.defaults import OperationalError
from seishub.defaults import DEFAULT_PREFIX, INDEX_DEF_TABLE
from seishub.defaults import ADD_INDEX_QUERY, DELETE_INDEX_BY_ID_QUERY, \
                             GET_NEXT_ID_QUERY, DELETE_INDEX_BY_KEY_QUERY, \
                             GET_INDEX_BY_ID_QUERY, GET_INDEX_BY_KEY_QUERY

class XmlCatalogError(SeishubError):
    pass

class XmlCatalog(object):
    implements(IXmlCatalog)
    
    def __init__(self,adbapi_connection):
        if not hasattr(adbapi_connection,'runInteraction'):
            raise TypeError("adbapi connector expected!")
            self._db=None
        else:
            self._db=adbapi_connection
            
    def __handleErrors(self,error):
        if error.check(OperationalError):
            raise XmlCatalogError(error.getErrorMessage())
        else:
            error.raiseException()
        
    def registerIndex(self,xml_index):
        def _addIndexTxn(txn):
            # get next unique id:
            get_next_id_query=GET_NEXT_ID_QUERY % (DEFAULT_PREFIX,
                                                   INDEX_DEF_TABLE)
            txn.execute(get_next_id_query)
            next_id=txn.fetchall()[0][0]
            # insert into INDEX_DEF_TABLE:
            add_query=ADD_INDEX_QUERY % \
                      {'prefix' : DEFAULT_PREFIX,
                       'table' : INDEX_DEF_TABLE,
                       'id' : next_id,
                       'key_path' : dbutil.quote(xml_index.getKey_path(),
                                                 "text"),
                       'value_path' : dbutil.quote(xml_index.getValue_path(),
                                                   "text"),
                       'data_type': dbutil.quote(xml_index.getType(), "text"),
                       }
            txn.execute(add_query)
            return next_id
                
        if not IXmlIndex.providedBy(xml_index):
            raise DoesNotImplement(IXmlIndex)
        else:
            d=self._db.runInteraction(_addIndexTxn)
            d.addErrback(self.__handleErrors)
        
        return d
    
    def removeIndex(self,id=None,key_path=None,value_path=None):
        if not isinstance(key_path,basestring) \
           and not isinstance(value_path,basestring):
            try:
                id=int(id)
            except ValueError:
                raise XmlCatalogError("No id or key_path, value_path given.")
                query=None
            else:
                query=DELETE_INDEX_BY_ID_QUERY
        else:
            query=DELETE_INDEX_BY_KEY_QUERY

        if query:
            str_map={'prefix' : DEFAULT_PREFIX,
                     'table' : INDEX_DEF_TABLE,
                     'id' : id,
                     'key_path' : dbutil.quote(key_path, "text"),
                     'value_path' : dbutil.quote(value_path,"text"),
                     }
            query%=str_map
            d=self._db.runOperation(query)
            d.addErrback(self.__handleErrors)
        else:
            d=None
            
        return d
    
    def getIndex(self,id=None,key_path=None,value_path=None):
        # select the proper query string:
        if not isinstance(key_path,basestring) \
           and not isinstance(value_path,basestring):
            try:
                id=int(id)
            except ValueError:
                raise XmlCatalogError("No id or key_path, value_path given.")
                query=None
            else:
                query=GET_INDEX_BY_ID_QUERY
        else:
            query=GET_INDEX_BY_KEY_QUERY
        
        # callback returning an XmlIndex on success:
        def return_index(res):
            #TODO: Find a way to clearly identify the entries in the result 
            #list with the table columns
            if len(res) == 1 and len(res[0]) == 4:
                index=XmlIndex(key_path = res[0][1],
                               value_path = res[0][2],
                               type = res[0][3])
            else:
                raise XmlCatalogError("Unexpected result set length.")
                index=None
            
            return index
        
        # perform query:
        if query:
            str_map={'prefix' : DEFAULT_PREFIX,
                     'table' : INDEX_DEF_TABLE,
                     'id' : id,
                     'key_path' : dbutil.quote(key_path, "text"),
                     'value_path' : dbutil.quote(value_path,"text"),
                     }
            query%=str_map
            d=self._db.runQuery(query)
            d.addErrback(self.__handleErrors)
            d.addCallback(return_index)
        else:
            d=None
            
        return d
    
    def indexResource(self,resource,index_id):
        if not IXmlResource.providedBy(resource):
            raise DoesNotImplement(IXmlResource)
            return None
        
        
        
        
        
