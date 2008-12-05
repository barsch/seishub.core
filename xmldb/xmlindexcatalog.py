# -*- coding: utf-8 -*-
from zope.interface.exceptions import DoesNotImplement
from sqlalchemy import select, sql

from seishub.exceptions import SeisHubError, NotFoundError
from seishub.exceptions import DuplicateObjectError
from seishub.db.util import DbStorage, DbError
from seishub.xmldb.interfaces import IXPathQuery, IResource, IXmlIndex
from seishub.xmldb.defaults import document_tab
from seishub.xmldb.index import XmlIndex
from seishub.xmldb.xpath import PredicateExpression

OPERATORS = {'and':sql.and_,
             'or':sql.or_
             }

class _QueryProcessor(object):
    """Mixin for XMLIndexCatalog providing query processing."""
    
    def _raiseIndexNotFound(self, query_base, expr):
        msg = "Error processing query. No index found for: %s"
        idx_str = '/' + '/'.join(map(str, query_base))
        if expr:
            idx_str += '/' + str(expr)
        raise NotFoundError(msg % idx_str)
    
    def findIndex(self, query_base, expr = None):
        """Tries to find the index fitting best for expr. If no expression is 
        given returns the rootnode index according to query_base."""
        # TODO: caching?
        xpath = '/' + query_base[2] 
        if expr:
            xpath += '/' + expr
        idx = self.getIndexes(query_base[0], query_base[1], xpath)
        if idx:
            return idx[0]
        return None
    
#    def _process_location_step(self, query_base, q):
#        if query_base[2] == '*':
#            # ignore root => simple package/resourcetype query
#            pass
#        else:
#            idx = self.findIndex(query_base)
#            idx_tab = idx._getElementCls().db_table.alias()
#            joins = document_tab.outerjoin(idx_tab, 
#                                     onclause = (idx_tab.c['document_id'] ==\
#                                                 document_tab.c['id']))

    def _join_on_index(self, idx, q, joins = None, op = "and"):
        idx_tab = idx._getElementCls().db_table.alias()
        if not joins:
            joins = document_tab.outerjoin(idx_tab, 
                                     onclause = (idx_tab.c['document_id'] ==\
                                                 document_tab.c['id']))
        else:
            joins = joins.outerjoin(idx_tab, 
                                    onclause = (idx_tab.c['document_id'] ==\
                                                document_tab.c['id']))
        if op == 'or':
            # OR operator...
            raise ("'or' not implemented yet")
        else:
            q = q.where(idx_tab.c['index_id'] == idx._id)
        return q, joins, idx_tab

    def _process_predicates(self, p, query_base, q, joins = None, 
                            prev_op = None):
        left = p._left
        right = p._right
        op = p._op
        left_idx = self.findIndex(query_base, str(left))
        right_idx = None
        if right:
            right_idx = self.findIndex(query_base, str(right))
        if left_idx and right_idx: 
            # - rel op => join
            # - log op => keyless query
            raise ("join not implemented yet")
        elif left_idx: 
            # - rel op => right = Value => key query
            # - log op => right = expr => left: keyless query, right: recursion step
            # - no op => keyless query 
            # left:
            q, joins, idx_tab = self._join_on_index(left_idx, q, joins)
            # right:
            if right and op in PredicateExpression._relational_ops:
                # key query => leaf
                q = q.where(p.applyOperator(idx_tab.c.keyval, 
                                            unicode(str(right))))
                return q, joins
            else:
                left = None
            if not (left or right):
                # no further nodes => leaf  
                return q, joins

        # => recursion step
        if op not in PredicateExpression._logical_ops:
            # still here with no or relational operator => no index found
            self._raiseIndexNotFound(query_base, str(p))
        # logical operator
        if left:
            q, joins = self._process_predicates(left, query_base, q, joins)
        if right:
            q, joins = self._process_predicates(right, query_base, q, 
                                                joins)
        # w = OPERATORS[p._op](l, r)
        return q, joins
    
    def _process_order_by(self, order_by, query_base, q, joins = None):
        for ob, direction in order_by.iteritems():
            # remove rootnode from order_by
            ob = '/'.join(ob.split('/')[2:])
            idx = self.findIndex(query_base, ob)
            if not idx:
                self._raiseIndexNotFound(query_base, ob)
            q, joins, idx_tab = self._join_on_index(idx, q, joins)
            o = idx_tab.c['keyval'].asc()
            if direction.lower() == "desc": 
                o = idx_tab.c['keyval'].desc()
            q = q.order_by(o)
        return q, joins

    def query(self, query):
        """@see: L{seishub.xmldb.interfaces.IXmlIndexCatalog}"""
        if not IXPathQuery.providedBy(query):
            raise DoesNotImplement(IXPathQuery)
        query_base = query.getQueryBase()
        predicates = query.getPredicates() or PredicateExpression()
        order_by = query.getOrderBy()
        limit = query.getLimit()
        offset = query.getOffset()
        q = select([document_tab.c['id']], use_labels = True)
        q, joins = self._process_predicates(predicates, query_base, q)
        q, joins = self._process_order_by(order_by, query_base, q, joins)
        q = q.select_from(joins)
        q = q.group_by(document_tab.c['id'])
        q = q.limit(limit).offset(offset)
        res = self._db.execute(q).fetchall()
        return [result[0] for result in res]
    
#        if query.has_predicates(): 
#            # query w/ key path expression(s)
#            value_col = index_tab.c.value
#            q = self._to_sql(query)
#            q = select([value_col],w)
#        else:
#            # all resources with specified resourcetype / package having the 
#            # specified rootnode
#            id_col = resource_tab.c['id']
#            q = select([id_col])
#            # w = ClauseList(operator = 'AND')
#            q = q.join(resourcetypes_tab, 
#                       resourcetypes_tab.c['resourcetype_id'] ==\
#                       resource_tab.c['resourcetype_id'])
#            q = q.join(packages_tab, 
#                       resourcetypes_tab.c['package_id'] ==\
#                       packages_tab.c['id'])
#            if query.package_id:
#                q = q.where(packages_tab.c['name'] == query.package_id)
#            if query.resourcetype_id:
#                q = q.where(resourcetypes_tab.c['name'] ==\
#                            query.resourcetype_id)
#        q = q.group_by(id_col)
#        # order by
#        alias_id = 0
#        limit = query.getLimit()
#        for ob in query.getOrder_by():
#            # find appropriate index
#            idx = self.getIndex(ob[0].value_path, ob[0].key_path)
#            if not idx:
#                msg = "Error processing query %s: No Index found for %s."
#                raise NotFoundError(msg % (str(query), str(ob[0])))
#            alias = idx._getElementCls().db_table.alias("idx_" + str(alias_id))
#            alias_id += 1
#            q = q.where(and_(alias.c.index_id == idx._getId(), 
#                             alias.c.value == value_col)) \
#                 .group_by(alias.c.key)
#            if ob[1].lower() == "desc": 
#                q = q.order_by(alias.c.key.desc())
#            else:
#                q = q.order_by(alias.c.key.asc())
#        if limit:
#            q = q.limit(limit)
#        res = self._db.execute(q).fetchall()
#        results = [result[0] for result in res]
#        return results

#    def _to_sql(self, xpq, q = None):
#        """translate query predicates to SQL where clause"""
#        # value_path = q.getValue_path()
#        # node_test = q.node_test
#        predicates = xpq.getPredicates()
#        idx_aliases = list()
#        
#        def _walk(p):
#            # recursively walk through predicate tree and convert to sql 
#            if p._op == 'and':
#                return and_(_walk(p._left),_walk(p._right))
#            elif p._op == 'or':
#                return or_(_walk(p._left),_walk(p._right))
#            else:
#                # find appropriate index:
#                idx = self.getIndex(value_path, str(p._left))
#                if not idx:
#                    msg = "Error processing query %s: No Index found for %s/%s"
#                    raise NotFoundError(msg % (str(q), value_path, 
#                                               str(p._left)))
#                idx_id = idx._getId()
#                # XXX: maybe simple counter instead of hash
#                alias_id = abs(hash(str(idx_id) + str(p._right)))
#                alias = index_tab.alias("idx_" + str(alias_id))
#                print alias_cnt
#                idx_aliases.append(alias)
#
#                if p._op == '':
#                    return _BinaryExpression(alias.c.index_id, idx_id,'=')
#
#                return and_(_BinaryExpression(alias.c.index_id, idx_id,'='),
#                            _BinaryExpression(alias.c.key, 
#                                              '\'' + str(p._right) + '\'',
#                                              p._op))
#                
#        w = _walk(predicates)
#        
#        for alias in idx_aliases:
#            w = and_(w,alias.c.value == index_tab.c.value)
#            
#        return w


class XmlIndexCatalog(DbStorage, _QueryProcessor):
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
    
    def indexResource(self, resource, xpath = None):
        """Index the given resource."""
        if not IResource.providedBy(resource):
            raise TypeError("%s is not an IResource." % str(resource))
        idx_list = self.getIndexes(resource.package.package_id, 
                                   resource.resourcetype.resourcetype_id,
                                   xpath)
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
    
    
