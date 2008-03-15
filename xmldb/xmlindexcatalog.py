# -*- coding: utf-8 -*-
from zope.interface import implements
from zope.interface.exceptions import DoesNotImplement
from sqlalchemy import select
from sqlalchemy.sql import and_, or_, not_
from sqlalchemy.sql.expression import _BinaryExpression, ClauseList

from seishub.util import unique
from seishub.xmldb.interfaces import IXmlIndexCatalog, IIndexRegistry, \
                                     IResourceIndexing, IXmlIndex, \
                                     IResourceStorage, IXPathQuery
from seishub.xmldb.xmlindex import XmlIndex
from seishub.xmldb.defaults import index_def_tab, index_tab, uri_tab, \
                                   query_aliases_tab
from seishub.xmldb.xpath import RestrictedXpathExpression, XPathQuery
from seishub.xmldb.errors import InvalidUriError, XmlIndexCatalogError, \
                                 InvalidIndexError, InvalidXpathQuery, \
                                 RestrictedXpathError, QueryAliasError

class XmlIndexCatalog(object):
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
        """@see: L{seishub.xmldb.interfaces.IResourceIndexing}""" 
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
    
    def _to_sql(self, q):
        """translate query predicates to SQL where clause"""
        value_path = q.getValue_path()
        predicates = q.getPredicates()
        idx_aliases = list()
        
        def _walk(p):
            # recursively walk through predicate tree and convert to sql 
            if p._op == 'and':
                return and_(_walk(p._left),_walk(p._right))
            elif p._op == 'or':
                return or_(_walk(p._left),_walk(p._right))
            else:
                # find appropriate index:
                idx = self.getIndex(value_path, str(p._left))
                if not idx:
                    raise XmlIndexCatalogError("No Index found for %s/%s" % \
                                               (value_path, str(p._left)))
                idx_id = idx.__id
                alias = index_tab.alias("idx_" + str(idx_id))
                idx_aliases.append(alias)

                if p._op == '':
                    return _BinaryExpression(alias.c.index_id, idx_id,'=')

                return and_(_BinaryExpression(alias.c.index_id, idx_id,'='),
                            _BinaryExpression(alias.c.key, str(p._right),p._op))
                
        w = _walk(predicates)
        
        for alias in idx_aliases:
            w = and_(w,alias.c.value == index_tab.c.value)
            
        return w
        
    def query(self, query):
        """@see: L{seishub.xmldb.interfaces.IXmlIndexCatalog}"""
        if not IXPathQuery.providedBy(query):
            raise DoesNotImplement(IXPathQuery)
        
        if query.has_predicates(): 
            # query w/ key path expression(s)
            w = self._to_sql(query)
            q = select([index_tab.c.value],w)
        else:
            # only value path given: value path <=> resource type
            q = select([uri_tab.c.uri], 
                       uri_tab.c.res_type == query.getValue_path()
                )
        
        results = self._db.execute(q).fetchall()
        results = [result[0] for result in results]
        return unique(results)

class QueryAliases(object):
    def __init__(self, db):
        self._db = db.engine
        self.aliases = self.listAliases() 
        
    def __getitem__(self, key):
        return self.aliases[key]
    
    def __contains__(self, key):
        return key in self.aliases
    
    def __setitem__(self, key, value):
        try:
            self.removeAlias(key)
        except KeyError:
            pass
        self.addAlias(key, value)
        
    def __delitem__(self, key):
        self.removeAlias(key)
        
    def __iter__(self):
        return self.aliases.__iter__()
    
    def addAlias(self, name, expr):
        self.aliases[name] = expr
        ins = query_aliases_tab.insert()
        try:
            self._db.execute(ins, {'name':name, 'expr':expr})
        except Exception, e:
            raise QueryAliasError(e)
    
    def getAlias(self, name):
        w = (query_aliases_tab.c.name == name)
        query = query_aliases_tab.select(w)
        results = self._db.execute(query)
        try:
            results = results.fetchall()[0]
        except:
            return None
        return results[1]
    
    def removeAlias(self, name):
        del self.aliases[name]
        w = (query_aliases_tab.c.name == name)
        self._db.execute(query_aliases_tab.delete(w))
    
    def listAliases(self):
        query = select([query_aliases_tab.c.name, query_aliases_tab.c.expr])
        try:
            res = self._db.execute(query)
            aliases = res.fetchall()
            #import pdb; pdb.set_trace()
        except:
            return dict()
        return dict(aliases)
    
    
    