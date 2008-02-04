# -*- coding: utf-8 -*-
from zope.interface import implements
from zope.interface.exceptions import DoesNotImplement
from twisted.enterprise import util as dbutil
from sqlalchemy import select
from sqlalchemy.sql import and_, ClauseList

from seishub.core import SeisHubError
from seishub.xmldb.interfaces import IXmlIndexCatalog, IIndexRegistry, \
                                     IResourceIndexing, IXmlIndex, IXmlResource
from seishub.xmldb.xmlindex import XmlIndex
from seishub.xmldb.defaults import index_def_tab, index_tab, metadata

class XmlIndexCatalogError(SeisHubError):
    pass

class XmlIndexCatalog(object):
    #TODO: check args in a more central manner
    implements(IIndexRegistry,
               IResourceIndexing,
               IXmlIndexCatalog)
    
    def __init__(self,db, resource_storage = None):
        self._db = db.engine
        self._storage = resource_storage       
                
#    def __handleErrors(self,error):
#        # wrap an exception thrown by the db driver in one of our own
#        raise XmlIndexCatalogError(error.getErrorMessage())
##        if error.check(OperationalError):
##            raise XmlIndexCatalogError(error.getErrorMessage())
##        else:
##            error.raiseException()
            
    def _parse_xpath_query(expr):
        pass
    _parse_xpath_query=staticmethod(_parse_xpath_query)
            
    # methods from IIndexRegistry:
        
    def registerIndex(self, xml_index):
        if not IXmlIndex.providedBy(xml_index):
            raise DoesNotImplement(IXmlIndex)
            return
        
        conn = self._db.connect()
        
        # begin transaction:
        txn = conn.begin()
        try:
            res = conn.execute(index_def_tab.insert(),
                               key_path = xml_index.getKey_path(),
                               value_path = xml_index.getValue_path(),
                               data_type = xml_index.getType())
            xml_index.__id = res.last_inserted_ids()[0]
            txn.commit()
        except Exception, e:
            txn.rollback()
            raise XmlIndexCatalogError(e)

        return xml_index
    
    def removeIndex(self,key_path=None,value_path=None):
        if not (isinstance(key_path,basestring) and isinstance(value_path,basestring)):
            raise XmlIndexCatalogError("No key_path and value_path given.")
        
        # flush index first:
        self.flushIndex(key_path=key_path,value_path=value_path)
        
        # then remove index definition:
        self._db.execute(index_def_tab.delete(
                         and_(
                              index_def_tab.c.key_path == key_path,
                              index_def_tab.c.value_path == value_path
                              ))
                         )
        
        return True

    def getIndex(self,value_path, key_path):
        if not (isinstance(key_path,basestring) and 
                isinstance(value_path,basestring)):
            raise XmlIndexCatalogError("No key_path and value_path given.")
        
        index = self.getIndexes(value_path, key_path)
        if len(index) > 1:
            raise XmlIndexCatalogError("Unexpected result set length.")
        elif len(index) == 0:
            return None
        
        return index[0]
    
    def getIndexes(self,value_path = None, key_path = None, data_type = None):
        w = ClauseList(operator = "AND")
        if isinstance(value_path,basestring):
            w.append(index_def_tab.c.value_path == value_path)
        if isinstance(key_path,basestring):
            w.append(index_def_tab.c.key_path == key_path)
        if isinstance(data_type,basestring):
            w.append(index_def_tab.c.data_type == data_type)
        query = index_def_tab.select(w)
        
        results = self._db.execute(query)
        try:
            results = results.fetchall()
        except:
            return None
        
        indexes = list()
        for res in results:
                index=XmlIndex(key_path = res[1],
                               value_path = res[2],
                               type = res[3])
                # inject the internal id into obj:
                index.__id=res[0]
                indexes.append(index)

        return indexes

    def updateIndex(self,key_path,value_path,new_index):
        #TODO: updateIndex implementation
        pass
    
    
    # methods from IResourceIndexing:
    
#    def indexResource(self,
#                      resource, 
#                      xml_index=None,
#                      key_path=None,
#                      value_path=None):
#        #TODO: uri instead of resource obj
#        #TODO: no specific index
#        if not IXmlResource.providedBy(resource):
#            raise DoesNotImplement(IXmlResource)
#            return None
#        
#        try:
#            key_path=xml_index.getKey_path()
#            value_path=xml_index.getValue_path()
#        except AttributeError:
#            if not (isinstance(key_path,basestring) 
#                    and isinstance(value_path,basestring)):
#                raise XmlIndexCatalogError("No xml_index or key_path, value_path given.")
#                return None
#        
#        # db transaction
#        def _indexResTxn(txn,keyval_list,data_type,index_id):
#            get_next_id_query=GET_NEXT_ID_QUERY % (DEFAULT_PREFIX, INDEX_TABLE)
#            
#            for keyval in keyval_list:
#                # get next id available:
#                txn.execute(get_next_id_query)
#                next_id=txn.fetchall()[0][0]
#
#                # insert into INDEX_TABLE:
#                add_query=ADD_INDEX_DATA_QUERY % \
#                            {'prefix' : DEFAULT_PREFIX,
#                            'table' : INDEX_TABLE,
#                            'id' : next_id,
#                            'index_id' : index_id,
#                            'key' : dbutil.quote(keyval['key'], data_type),
#                            'value': dbutil.quote(keyval['value'], "text"),
#                            }
#                txn.execute(add_query)
#                
#            return True
#        
#        # get obj from db even if IXmlIndex obj was provided to ensure consistency
#        # with stored index and to retrieve an internal id
#        d=self.getIndex(key_path=key_path,value_path=value_path)
#        
#        # eval index on given resource:
#        def _evalIndexCb(idx_obj):
#            keyval_dict = idx_obj.eval(xml_resource=resource)
#            data_type = idx_obj.getType()
#            index_id=idx_obj.__id # _id has been injected by getIndex
#            # insert into db:
#            if keyval_dict:
#                d=self._db.runInteraction(_indexResTxn,keyval_dict,data_type,
#                                          index_id)
#                return d
#            else:
#                return None
#        d.addCallback(_evalIndexCb)
#        
#        return d
#    
    def flushIndex(self,key_path,value_path):
        return 
#        if not (isinstance(key_path,basestring) and isinstance(value_path,basestring)):
#            raise XmlIndexCatalogError("No xml_index or key_path, value_path given.")
#            return None
#            
#        query=REMOVE_INDEX_DATA_BY_KEY_QUERY
#        str_map={'prefix' : DEFAULT_PREFIX,
#                 'table' : INDEX_TABLE,
#                 'key_path' : dbutil.quote(key_path, "text"),
#                 'value_path' : dbutil.quote(value_path,"text"),
#                 }
#        query%=str_map
#        d=self._db.runOperation(query)
#        d.addErrback(self.__handleErrors)
#            
#        return d
    
#    def reindex(self,key_path,value_path):
#        if not (isinstance(key_path,basestring) and isinstance(value_path,basestring)):
#            raise XmlIndexCatalogError("No xml_index or key_path, value_path given.")
#            return None
#        
#        # first get index to make sure it is persistent in db and to get its id
#        d = self.getIndex(key_path, value_path)
#        d.addErrback(self.__handleErrors)
#        
#        d.addCallback()
        
        
    # methods from IXmlIndexCatalog:
    
    def query(self, query):
        if not query:
            return None
        
        
        
        
        
        
        
        
        
