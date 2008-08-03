# -*- coding: utf-8 -*-
from zope.interface import implements
from zope.interface.exceptions import DoesNotImplement
from sqlalchemy import select #@UnresolvedImport
from sqlalchemy.sql import and_, or_ #@UnresolvedImport
from sqlalchemy.sql.expression import _BinaryExpression, ClauseList #@UnresolvedImport

from seishub.db.util import DbStorage
from seishub.xmldb.interfaces import IXmlIndexCatalog, IIndexRegistry, \
                                     IResourceIndexing, IXmlIndex, \
                                     IResourceStorage, IXPathQuery
from seishub.xmldb.errors import XmlIndexCatalogError, \
                                 InvalidIndexError
from seishub.xmldb.defaults import index_def_tab, index_tab, \
                                   resource_tab
from seishub.xmldb.index import XmlIndex
from seishub.xmldb.xpath import IndexDefiningXpathExpression


class XmlIndexCatalog(DbStorage):
    implements(IIndexRegistry,
               IResourceIndexing,
               IXmlIndexCatalog)
    
    def __init__(self,db,resource_storage = None):
        super(XmlIndexCatalog, self).__init__(db)
        
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
        try:
            self.store(xml_index)
        except Exception, e:
            raise XmlIndexCatalogError(e)
        return xml_index
    
    def removeIndex(self,value_path=None, key_path=None):
        """@see: L{seishub.xmldb.xmlindexcatalog.interfaces.IIndexRegistry}"""
        if not (isinstance(key_path,basestring) and isinstance(value_path,basestring)):
            raise XmlIndexCatalogError("No key_path and value_path given.")
        if value_path.startswith('/'):
            value_path = value_path[1:]
        # flush index first:
        self.flushIndex(key_path = key_path, value_path = value_path)
        # then remove index definition:
        self.drop(XmlIndex, key_path = key_path, value_path = value_path)
        return True

    def getIndex(self,value_path=None, key_path=None, expr=None):
        """@see: L{seishub.xmldb.xmlindexcatalog.interfaces.IIndexRegistry}"""
        if not (isinstance(key_path,basestring) and 
                isinstance(value_path,basestring)):
            try:
                expr_o = IndexDefiningXpathExpression(expr)
                value_path = expr_o.value_path
                key_path = expr_o.key_path
            except Exception, e:
                raise XmlIndexCatalogError("Invalid index expression: "+\
                                           "%s, %s, %s" %\
                                           (value_path, key_path, expr), e )
        
        index = self.getIndexes(value_path, key_path)
        if len(index) > 1:
            raise XmlIndexCatalogError("Unexpected result set length.")
        elif len(index) == 0:
            raise XmlIndexCatalogError("No index found for: %s, %s" %\
                                       (value_path, key_path))
        
        return index[0]
    
    def getIndexes(self,value_path = None, key_path = None, data_type = None):
        """@see: L{seishub.xmldb.xmlindexcatalog.interfaces.IIndexRegistry}"""
        w = ClauseList(operator = "AND")
        if isinstance(value_path, basestring):
            if value_path.startswith('/'):
                value_path = value_path[1:]
            like_value_path = self.to_sql_like(value_path)
            if like_value_path == value_path:
                w.append(index_def_tab.c.value_path == value_path)
            else:
                w.append(index_def_tab.c.value_path.like(like_value_path))
        if isinstance(key_path, basestring):
            w.append(index_def_tab.c.key_path == key_path)
        if isinstance(data_type, basestring):
            w.append(index_def_tab.c.data_type == data_type)
        query = index_def_tab.select(w)
        
        res = self._db.execute(query)
        try:
            results = res.fetchall()
            res.close()
        except:
            return None    
        
        indexes = list()
        for res in results:
                index = XmlIndex(key_path = res['key_path'],
                                 value_path = res['value_path'],
                                 type = res['data_type'])
                # inject the internal id into obj:
                index._setId(res[0])
                indexes.append(index)

        return indexes

    def updateIndex(self,key_path,value_path,new_index):
        """@see: L{seishub.xmldb.xmlindexcatalog.interfaces.IIndexRegistry}"""
        #TODO: updateIndex implementation
        pass
    
    # methods from IResourceIndexing:
    def indexResource(self, document_id, value_path, key_path):
        """@see: L{seishub.xmldb.xmlindexcatalog.interfaces.IResourceIndexing}"""
#        #TODO: do this not index specific but resource type specific

        if not (isinstance(key_path,basestring) and 
                isinstance(value_path,basestring)):
                raise XmlIndexCatalogError("Invalid key path or value path")
        
        #get objs and evaluate index on resource:
        try:
            resource = self._storage.getResource(document_id = document_id)
        except AttributeError:
            raise XmlIndexCatalogError("No resource storage.")
        index = self.getIndex(value_path, key_path)
        if not index:
            raise InvalidIndexError("No index found for (%s,%s)" % 
                                    (value_path, key_path))
        keysvals = index.eval(resource.document)
        #data_type = index.getType()
        index_id = index._getId()
        if not keysvals: # index does not apply
            return
        
        conn = self._db.connect()
        # begin transaction:
        txn = conn.begin()
        try:
            for keyval in keysvals:
                conn.execute(index_tab.insert(),
                             index_id = index_id,
                             key = str(keyval['key']),
                             value = str(keyval['value']))
            txn.commit()
        except Exception, e:
            txn.rollback()
            raise XmlIndexCatalogError(e)
        finally:
            conn.close()
        
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
                idx_id = idx._getId()
                # XXX: maybe simple counter instead of hash
                alias_id = abs(hash(str(idx_id) + str(p._right)))
                alias = index_tab.alias("idx_" + str(alias_id))
                #print alias_cnt
                idx_aliases.append(alias)

                if p._op == '':
                    return _BinaryExpression(alias.c.index_id, idx_id,'=')

                return and_(_BinaryExpression(alias.c.index_id, idx_id,'='),
                            _BinaryExpression(alias.c.key, 
                                              '\'' + str(p._right) + '\'',
                                              p._op))
                
        w = _walk(predicates)
        
        for alias in idx_aliases:
            w = and_(w,alias.c.value == index_tab.c.value)
            
        return w
        
    def query(self, query):
        """@see: L{seishub.xmldb.interfaces.IXmlIndexCatalog}"""
        # XXX: query should return ResourceInformation objects
        if not IXPathQuery.providedBy(query):
            raise DoesNotImplement(IXPathQuery)
        
        if query.has_predicates(): 
            # query w/ key path expression(s)
            value_col = index_tab.c.value
            w = self._to_sql(query)
            q = select([value_col],w)
        else:
            # value path only: => resource type query
            value_col = resource_tab.c.resource_id
            q = select([value_col], 
                       and_( 
                           resource_tab.c.package_id == query.package_id,
                           resource_tab.c.resourcetype_id == query.resourcetype_id
                       )
                )
        q = q.group_by(value_col)
        
        # order by
        alias_id = 0
        limit = query.getLimit()
        for ob in query.getOrder_by():
            # find appropriate index
            idx = self.getIndex(ob[0].value_path, ob[0].key_path)
            if not idx:
                raise XmlIndexCatalogError("No Index found for %s" % str(ob[0]))
            alias = index_tab.alias("idx_" + str(alias_id))
            alias_id += 1
            q = q.where(and_(alias.c.index_id == idx._getId(), 
                             alias.c.value == value_col)) \
                 .group_by(alias.c.key)
            if ob[1].lower() == "desc": 
                q = q.order_by(alias.c.key.desc())
            else:
                q = q.order_by(alias.c.key.asc())
        if limit:
            q = q.limit(limit)
        res = self._db.execute(q).fetchall()
        results = [result[0] for result in res]
        return results
