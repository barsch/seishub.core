# -*- coding: utf-8 -*-
from zope.interface.exceptions import DoesNotImplement
from sqlalchemy import select #@UnresolvedImport
from sqlalchemy.sql import and_, or_ #@UnresolvedImport
from sqlalchemy.sql.expression import _BinaryExpression, ClauseList #@UnresolvedImport

from seishub.core import implements
from seishub.exceptions import SeisHubError, NotFoundError
from seishub.exceptions import InvalidParameterError
from seishub.exceptions import DuplicateObjectError
from seishub.db.util import DbStorage, DbError
from seishub.xmldb.interfaces import IXmlIndexCatalog, IIndexRegistry, \
                                     IResourceIndexing, IXmlIndex, \
                                     IResourceStorage, IXPathQuery, IResource
from seishub.xmldb.defaults import index_def_tab, \
                                   resource_tab
from seishub.xmldb.index import XmlIndex
from seishub.xmldb.xpath import IndexDefiningXpathExpression


class XmlIndexCatalog(DbStorage):
    def __init__(self, db, resource_storage = None):
        DbStorage.__init__(self, db)
        self._storage = resource_storage
    
#    def _parse_xpath_query(expr):
#        pass
#    _parse_xpath_query=staticmethod(_parse_xpath_query)

    def registerIndex(self, xml_index):
        """Register given index in the catalog."""
        if not IXmlIndex.providedBy(xml_index):
            raise DoesNotImplement(IXmlIndex)
        try:
            self.store(xml_index)
        except DbError, e:
            msg = "Error registering an index: Index '%s' already exists."
            raise DuplicateObjectError(msg % str(xml_index), e)
        except Exception, e:
            msg = "Error registering an index: %s"
            raise SeisHubError(msg % str(xml_index), e)
        return xml_index
    
    def removeIndex(self, package_id, resourcetype_id, xpath):
        """Remove an index and all indexed data."""
        self.flushIndex(package_id, resourcetype_id, xpath)
        self.drop(XmlIndex, 
                  resourcetype = {'package':{'package_id':package_id}, 
                                  'resourcetype_id':resourcetype_id}, 
                  xpath = xpath)
    
    def getIndexes(self, package_id = None, resourcetype_id = None, 
                   xpath = None, type = None):
        """Return a list of all applicable indexes."""
        res = self.pickup(XmlIndex, 
                          resourcetype = {'package':{'package_id':package_id}, 
                                          'resourcetype_id':resourcetype_id}, 
                          xpath = xpath,
                          type = type)
        return res

#    def updateIndex(self,key_path,value_path,new_index):
#        """Update index."""
#        #TODO: updateIndex implementation
#        pass
    
    def indexResource(self, resource):
        """Index the given resource."""
        if not IResource.providedBy(resource):
            raise TypeError("%s is not an IResource." % str(resource))
        idx_list = self.getIndexes(resource.package.package_id, 
                                   resource.resourcetype.resourcetype_id)
        elements = []
        for idx in idx_list:
            elements.extend(idx.eval(resource.document))
        self.store(*elements)
        return elements
    
    def dumpIndex(self, package_id, resourcetype_id, xpath):
        """Return all indexed values for the given index."""
        xmlindex = self.getIndexes(package_id, resourcetype_id, xpath)[0]
        return self.pickup(xmlindex._getElementCls(), index = xmlindex)

    def flushIndex(self, package_id = None, resourcetype_id = None, 
                   xpath = None, xmlindex = None):
        """Remove all indexed data for given index."""
        if not (package_id and resourcetype_id and xpath) or xmlindex:
            raise TypeError("flushIndex: invalid number of arguments.")
        if not xmlindex:
            xmlindex = self.getIndexes(package_id, resourcetype_id, xpath)[0]
        element_cls = xmlindex._getElementCls()
        self.drop(element_cls, index = xmlindex)
        
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
                    msg = "Error processing query %s: No Index found for %s/%s"
                    raise NotFoundError(msg % (str(q), value_path, 
                                               str(p._left)))
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
            w = ClauseList(operator = 'AND')
            if query.package_id:
                w.append(resource_tab.c.package_id==query.package_id)
            if query.resourcetype_id:
                w.append(resource_tab.c.resourcetype_id==query.resourcetype_id)
            q = select([value_col], w)
        q = q.group_by(value_col)
        
        # order by
        alias_id = 0
        limit = query.getLimit()
        for ob in query.getOrder_by():
            # find appropriate index
            idx = self.getIndex(ob[0].value_path, ob[0].key_path)
            if not idx:
                msg = "Error processing query %s: No Index found for %s."
                raise NotFoundError(msg % (str(query), str(ob[0])))
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
