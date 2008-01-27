# -*- coding: utf-8 -*-
from zope.interface import implements
from zope.interface.exceptions import DoesNotImplement

from twisted.enterprise import util as dbutil

from seishub.core import SeisHubError
from seishub.xmldb.interfaces import IXmlIndexCatalog, IIndexRegistry, \
                                     IResourceIndexing, IXmlIndex, IXmlResource
from seishub.xmldb.xmlindex import XmlIndex

#from seishub.db.dbmanager import OperationalError
from seishub.defaults import DEFAULT_PREFIX, INDEX_DEF_TABLE, INDEX_TABLE
from seishub.defaults import ADD_INDEX_QUERY, DELETE_INDEX_BY_ID_QUERY, \
                             GET_NEXT_ID_QUERY, DELETE_INDEX_BY_KEY_QUERY, \
                             GET_INDEX_BY_ID_QUERY, GET_INDEX_BY_KEY_QUERY, \
                             ADD_INDEX_DATA_QUERY, REMOVE_INDEX_DATA_BY_ID_QUERY, \
                             REMOVE_INDEX_DATA_BY_KEY_QUERY

class XmlIndexCatalogError(SeisHubError):
    pass

class XmlIndexCatalog(object):
    implements(IIndexRegistry,
               IResourceIndexing,
               IXmlIndexCatalog)
    
    def __init__(self,adbapi_connection):
        if not hasattr(adbapi_connection,'runInteraction'):
            raise TypeError("adbapi connector expected!")
            self._db=None
        else:
            self._db=adbapi_connection
            
    def __handleErrors(self,error):
        # this method does no real error handling, but simply wraps an
        # exception thrown by the db driver in one of our own
        if error.check(OperationalError):
            raise XmlIndexCatalogError(error.getErrorMessage())
        else:
            error.raiseException()
            
    def _parse_xpath_query(expr):
        pass
    _parse_xpath_query=staticmethod(_parse_xpath_query)
            
    # methods from IIndexRegistry:
        
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
    
    def removeIndex(self,xml_index=None,key_path=None,value_path=None):
        try:
            key_path=xml_index.getKey_path()
            value_path=xml_index.getValue_path()
        except AttributeError:
            if not (isinstance(key_path,basestring) and isinstance(value_path,basestring)):
                raise XmlIndexCatalogError("No xml_index or key_path, value_path given.")
                return None

        query=DELETE_INDEX_BY_KEY_QUERY

        # flush index first:
        d=self.flushIndex(key_path=key_path,value_path=value_path)
        
        # then remove index definition:
        str_map={'prefix' : DEFAULT_PREFIX,
                 'table' : INDEX_DEF_TABLE,
                 'key_path' : dbutil.quote(key_path, "text"),
                 'value_path' : dbutil.quote(value_path,"text"),
                 }
        query%=str_map
        d.addCallback(lambda f: self._db.runOperation(query))
        d.addErrback(self.__handleErrors)
                
        return d
    
    def getIndex(self,key_path=None,value_path=None):
        if not (isinstance(key_path,basestring) and 
                isinstance(value_path,basestring)):
            raise XmlIndexCatalogError("No key_path, value_path given.")
            query=None
        else:
            query=GET_INDEX_BY_KEY_QUERY
        
        # callback returning an XmlIndex on success:
        def return_index(res):
            #TODO: Find a way to clearly identify the entries in the result 
            #list with the table columns
            if len(res) == 1 and len(res[0]) == 4: #one proper index found
                index=XmlIndex(key_path = res[0][1],
                               value_path = res[0][2],
                               type = res[0][3])
                # inject the database's internal id into obj:
                index.__id=res[0][0]
            elif len(res) == 0: # no index found
                raise XmlIndexCatalogError("No index found with given id "+\
                                      "or key and value.")
            else: # other error
                raise XmlIndexCatalogError("Unexpected result set length.")
                index=None
            
            return index
        
        # perform query:
        if query:
            str_map={'prefix' : DEFAULT_PREFIX,
                     'table' : INDEX_DEF_TABLE,
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
    
    def updateIndex(self,old_index=None,new_index=None):
        #TODO: updateIndex implementation
        pass
    
    
    # methods from IResourceIndexing:
    
    def indexResource(self,
                      resource, 
                      xml_index=None,
                      key_path=None,
                      value_path=None):
        #TODO: uri instead of resource obj
        #TODO: no specific index
        if not IXmlResource.providedBy(resource):
            raise DoesNotImplement(IXmlResource)
            return None
        
        try:
            key_path=xml_index.getKey_path()
            value_path=xml_index.getValue_path()
        except AttributeError:
            if not (isinstance(key_path,basestring) 
                    and isinstance(value_path,basestring)):
                raise XmlIndexCatalogError("No xml_index or key_path, value_path given.")
                return None
        
        # db transaction
        def _indexResTxn(txn,keyval_list,data_type,index_id):
            get_next_id_query=GET_NEXT_ID_QUERY % (DEFAULT_PREFIX, INDEX_TABLE)
            
            for keyval in keyval_list:
                # get next id available:
                txn.execute(get_next_id_query)
                next_id=txn.fetchall()[0][0]

                # insert into INDEX_TABLE:
                add_query=ADD_INDEX_DATA_QUERY % \
                            {'prefix' : DEFAULT_PREFIX,
                            'table' : INDEX_TABLE,
                            'id' : next_id,
                            'index_id' : index_id,
                            'key' : dbutil.quote(keyval['key'], data_type),
                            'value': dbutil.quote(keyval['value'], "text"),
                            }
                txn.execute(add_query)
                
            return True
        
        # get obj from db even if IXmlIndex obj was provided to ensure consistency
        # with stored index and to retrieve an internal id
        d=self.getIndex(key_path=key_path,value_path=value_path)
        
        # eval index on given resource:
        def _evalIndexCb(idx_obj):
            keyval_dict = idx_obj.eval(xml_resource=resource)
            data_type = idx_obj.getType()
            index_id=idx_obj.__id # _id has been injected by getIndex
            # insert into db:
            if keyval_dict:
                d=self._db.runInteraction(_indexResTxn,keyval_dict,data_type,
                                          index_id)
                return d
            else:
                return None
        d.addCallback(_evalIndexCb)
        
        return d
    
    def flushIndex(self,xml_index=None,key_path=None,value_path=None):
        #decide which arguments to use:
        
        try:
            key_path=xml_index.getKey_path()
            value_path=xml_index.getValue_path()
        except AttributeError:
            if not (isinstance(key_path,basestring) and isinstance(value_path,basestring)):
                raise XmlIndexCatalogError("No xml_index or key_path, value_path given.")
                return None
            
        query=REMOVE_INDEX_DATA_BY_KEY_QUERY
        str_map={'prefix' : DEFAULT_PREFIX,
                 'table' : INDEX_TABLE,
                 'key_path' : dbutil.quote(key_path, "text"),
                 'value_path' : dbutil.quote(value_path,"text"),
                 }
        query%=str_map
        d=self._db.runOperation(query)
        d.addErrback(self.__handleErrors)
            
        return d
    
    # methods from IXmlIndexCatalog:
    
    def query(self, query):
        if not query:
            return None
        
        
        
        
        
        
        
        
        
