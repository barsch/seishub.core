# -*- coding: utf-8 -*-
from zope.interface import implements
from zope.interface.exceptions import DoesNotImplement
from sqlalchemy import select
from sqlalchemy.sql.expression import ClauseList
from sqlalchemy.sql import and_

from seishub.core import SeisHubError
from seishub.xmldb.interfaces import IXmlIndexCatalog, IIndexRegistry, \
                                     IResourceIndexing, IXmlIndex, \
                                     IResourceStorage
from seishub.xmldb.xmlindex import XmlIndex
from seishub.xmldb.defaults import index_def_tab, index_tab
from seishub.xmldb.errors import InvalidUriError, XmlIndexCatalogError, \
                                 InvalidIndexError


class XmlIndexCatalog(object):
    #TODO: check args in a more central manner
    implements(IIndexRegistry,
               IResourceIndexing,
               IXmlIndexCatalog)
    
    def __init__(self,db, resource_storage = None):
        self._db = db.engine
        
        if resource_storage:
            if not IResourceStorage.providedBy(resource_storage):
                raise DoesNotImplement(IResourceStorage)
            self._storage = resource_storage
            
    def _parse_xpath_query(expr):
        pass
    _parse_xpath_query=staticmethod(_parse_xpath_query)
            
    # methods from IIndexRegistry:
        
    def registerIndex(self, xml_index):
        """@see: L{seishub.xmldb.xmlindexcatalog.interfaces.IIndexRegistry}"""
        if not IXmlIndex.providedBy(xml_index):
            raise DoesNotImplement(IXmlIndex)
        
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
    
    def removeIndex(self,value_path=None, key_path=None):
        """@see: L{seishub.xmldb.xmlindexcatalog.interfaces.IIndexRegistry}"""
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
        """@see: L{seishub.xmldb.xmlindexcatalog.interfaces.IIndexRegistry}"""
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
        """@see: L{seishub.xmldb.xmlindexcatalog.interfaces.IIndexRegistry}"""
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
        """@see: L{seishub.xmldb.xmlindexcatalog.interfaces.IIndexRegistry}"""
        #TODO: updateIndex implementation
        pass
    
    
    # methods from IResourceIndexing:
    
    def indexResource(self, uri, value_path, key_path):
        """@see: L{seishub.xmldb.xmlindexcatalog.interfaces.IResourceIndexing}"""
#        #TODO: no specific index

        if not isinstance(uri, basestring):
            raise InvalidUriError("String expected.")
        if not (isinstance(key_path,basestring) and 
                isinstance(value_path,basestring)):
                raise XmlIndexCatalogError("Invalid key path or value path")
        
        #get objs and evaluate index on resource:
        try:
            resource = self._storage.getResource(uri)
        except AttributeError:
            raise XmlIndexCatalogError("No resource storage.")
        index = self.getIndex(value_path, key_path)
        if not index:
            raise InvalidIndexError("No index found for (%s,%s)" % 
                                    (value_path, key_path))
        keysvals = index.eval(resource)
        #data_type = index.getType()
        index_id = index.__id
        if not keysvals: # index does not apply
            return
        
        conn = self._db.connect()
        # begin transaction:
        txn = conn.begin()
        try:
            for keyval in keysvals:
                res = conn.execute(index_tab.insert(),
                                   index_id = index_id,
                                   key = keyval['key'],
                                   value = keyval['value'])
            txn.commit()
        except Exception, e:
            txn.rollback()
            raise XmlIndexCatalogError(e)
        
        return True

    def flushIndex(self,value_path, key_path):
        """@see: L{seishub.xmldb.xmlindexcatalog.interfaces.IResourceIndexing}""" 
        if not (isinstance(key_path,basestring) and isinstance(value_path,basestring)):
            raise XmlIndexCatalogError("No key_path, value_path given.")

        self._db.execute(index_tab.delete(
                         index_tab.c.index_id.in_
                           (select([index_def_tab.c.id],
                                   and_ 
                                   (index_def_tab.c.key_path == key_path,
                                   index_def_tab.c.value_path == value_path))
                            )
                         ))
    
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
        
        
        
        
        
        
        
        
        
