# -*- coding: utf-8 -*-
from zope.interface.exceptions import DoesNotImplement
from sqlalchemy import select, sql

from seishub.exceptions import SeisHubError, NotFoundError
from seishub.exceptions import DuplicateObjectError, InvalidParameterError
from seishub.db.util import DbStorage, DbError
from seishub.xmldb.interfaces import IXPathQuery, IResource, IXmlIndex
from seishub.xmldb.defaults import document_tab
from seishub.xmldb.index import XmlIndex, type_classes
from seishub.xmldb import index
from seishub.xmldb.xpath import XPathQuery

INDEX_TYPES = {"text":index.TEXT_INDEX,
               "numeric":index.NUMERIC_INDEX,
               "float":index.FLOAT_INDEX,
               "datetime":index.DATETIME_INDEX,
               "boolean":index.BOOLEAN_INDEX,
               "nonetype":index.NONETYPE_INDEX
               }

class _QueryProcessor(object):
    """Mixin for XMLIndexCatalog providing query processing."""
    
    def _raiseIndexNotFound(self, query_base, expr):
        msg = "Error processing query. No index found for: %s"
        idx_str = '/' + '/'.join(map(str, query_base)) + expr or ''
        raise NotFoundError(msg % idx_str)
    
    def findIndex(self, query_base, expr = None, tolerant = True):
        """Tries to find the index fitting best for expr. If no expression is 
        given returns the rootnode index according to query_base."""
        # XXX: caching!
        if expr:
            expr = '/' + expr
        idx = self.getIndexes(query_base[0], query_base[1], expr)
        if idx:
            return idx[0]
        if not tolerant:
            raise self._raiseIndexNotFound(query_base, expr)
        return None
    
    def _resourceTypeQuery(self, package, resourcetype):
        """overloaded by subclass"""
        return None

    def _isLogOp(self, p):
        return p[1] in XPathQuery._logical_ops
    
    def _isRelOp(self, p):
        return p[1] in XPathQuery._relational_ops
    
    def _applyOp(self, op, left, right):
        # create sqlalchemy clauses from string operators
        if op == '==' or op == '=':
            return left == right
        elif op == '!=':
            return left != right
        elif op == '<':
            return left < right
        elif op == '>':
            return left > right
        elif op == '<=':
            return left <= right
        elif op == '>=':
            return left >= right
        elif op == 'and':
            return sql.and_(left, right)
        elif op == 'or':
            return sql.or_(left, right)
        raise InvalidParameterError("Operator '%s' not specified." % self._op)

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
            w = idx_tab.c['index_id'] == idx._id
            # q = q.where(idx_tab.c['index_id'] == idx._id)
        return q, joins, idx_tab, w
    
    def _process_rootnode(self, lp, q, joins = None):
        idx = self.findIndex(lp)
        q, joins, _, w = self._join_on_index(idx, q, joins)
        q = q.where(w)
        return q, joins
    
    def _process_predicates(self, p, q, joins = None, parent_op = 'and'):
        w = None
        if len(p) == 3:
            # binary expression
            op = p[1]
            l = p[0]
            r = p[2]
            if op in XPathQuery._relational_ops:
                # relational operator, l is a path expression => find an index
                lidx = self.findIndex([l[0], l[1]], l[2], False)
                q, joins, ltab, w = self._join_on_index(lidx, q, joins)
                if isinstance(r, list): # joined path query
                    ridx = self.findIndex([r[0], r[1]], r[2], False)
                    q, joins, rtab, ridxw = self._join_on_index(ridx, q, joins)
                    w = sql.and_(w, ridxw, 
                                 ltab.c['keyval'] == rtab.c['keyval'])
                else: # key / value query
                    w = sql.and_(w, self._applyOp(op, ltab.c['keyval'], 
                                                  lidx.prepareKey(r)))
            else:
                # logical operator
                q, joins, lw = self._process_predicates(l, q, joins)
                q, joins, rw = self._process_predicates(r, q, joins, op)
                q = q.where(self._applyOp(op, lw, rw))
        else:
            # unary expression
            idx = self.findIndex([p[0][0], p[0][1]], p[0][2], False)
            q, joins, _, w = self._join_on_index(idx, q, joins)
        return q, joins, w
    
    def _process_order_by(self, order_by, q, joins = None):
        for ob in order_by:
            # an order_by element is of the form: 
            # [[package, resourcetype, xpath], direction]
            idx = self.findIndex([ob[0][0], ob[0][1]], ob[0][2], False)
            q, joins, idx_tab, w = self._join_on_index(idx, q, joins)
            q = q.where(w)
            o = idx_tab.c['keyval'].asc()
            if ob[1] == "desc": 
                o = idx_tab.c['keyval'].desc()
            q = q.order_by(o)
            # order by columns must show up in the group by clause, too
            q = q.group_by(idx_tab.c['keyval'])
        return q, joins

    def query(self, query):
        """@see: L{seishub.xmldb.interfaces.IXmlIndexCatalog}"""
        if not IXPathQuery.providedBy(query):
            raise DoesNotImplement(IXPathQuery)
        # query_base = query.getQueryBase()
        location_path = query.getLocationPath()
        predicates = query.getPredicates()
        order_by = query.getOrderBy() or list()
        limit = query.getLimit()
        offset = query.getOffset()
        
        q = select([document_tab.c['id']], use_labels = True)
        joins = None
        if not (predicates or order_by):
            if not location_path[2]:
                # index-less query => /package/resourcetype only
                return self._resourceTypeQuery(location_path[0], 
                                               location_path[1])
            else:
                # rootnode was specified => /package/resourcetype/rootnode
                q, joins = self._process_rootnode(location_path, q)
        if predicates:
            q, joins, w = self._process_predicates(predicates, q)
            if w:
                q = q.where(w)
        if order_by:    
            q, joins = self._process_order_by(order_by, q, joins)
        if joins:
            q = q.select_from(joins)
        q = q.group_by(document_tab.c['id'])
        q = q.limit(limit).offset(offset)
#        from sqlalchemy.ext.serializer import dumps, loads
#        from seishub.db.dbmanager import meta
#        blah = dumps(q)
#        print "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
#        print len(blah)
#        blah = 'huihui' + blah + 'huhuhhuh'
#        muh = loads(blah, meta)
#        blah = q.params()
#        bluh = q.compile()
#        from sqlalchemy.sql import text
#        sql = text(str(q))
        # import pdb;pdb.set_trace() 
        res = self._db.execute(q).fetchall()
        return [result[0] for result in res]


class XmlIndexCatalog(DbStorage, _QueryProcessor):
    def __init__(self, db, resource_storage = None):
        DbStorage.__init__(self, db)
        self._storage = resource_storage
    
#    def _parse_xpath_query(expr):
#        pass
#    _parse_xpath_query=staticmethod(_parse_xpath_query)

    def _resourceTypeQuery(self, package_id, resourcetype_id):
        """Returns the document ids of all documents belonging to specified 
        package and resourcetype."""
        # XXX: older revisions are ignored!
        res = self._storage.getResourceList(package_id, resourcetype_id)
        return [r.document._id for r in res]

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
                   xpath = None, type = None, options = None):
        """Return a list of all applicable indexes."""
        res = self.pickup(XmlIndex, 
                          resourcetype = {'package':{'package_id':package_id}, 
                                          'resourcetype_id':resourcetype_id}, 
                          xpath = xpath,
                          type = type,
                          options = options)
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
        for el in elements:
            try:
                self.store(el)
            except DbError:
                # tried to store an index element with same parameters as one
                # indexed before => ignore
                # XXX: generate debug message
                pass
        return elements
    
    def dumpIndex(self, package_id, resourcetype_id, xpath):
        """Return all indexed values for the given index."""
        xmlindex = self.getIndexes(package_id, resourcetype_id, xpath)[0]
        return self.pickup(xmlindex._getElementCls(), index = xmlindex)
    
    def dumpIndexByDocument(self, document_id):
        """Return all IndexElements indexed for the specified document."""
        elements = list()
        for cls in type_classes.values():
            el = self.pickup(cls, document = {'_id':document_id})
            elements.extend(el)
        return elements

    def flushIndex(self, package_id = None, resourcetype_id = None, 
                   xpath = None, xmlindex = None, resource = None):
        """Remove all indexed data for given index."""
        if not ((package_id and resourcetype_id and xpath) or xmlindex or resource):
            raise TypeError("flushIndex: invalid number of arguments.")
        if resource:
            for element_cls in type_classes.values():
                self.drop(element_cls, 
                          document = {'_id':resource.document._id})
            return
        if not xmlindex:
            xmlindex = self.getIndexes(package_id, resourcetype_id, xpath)[0]
        element_cls = xmlindex._getElementCls()
        self.drop(element_cls, index = xmlindex)
    
    
