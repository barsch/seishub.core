# -*- coding: utf-8 -*-

from seishub.db.orm import DbStorage, DbError, DB_LIKE
from seishub.exceptions import DuplicateObjectError, InvalidParameterError, \
    SeisHubError, NotFoundError
from seishub.registry.defaults import resourcetypes_tab, packages_tab
from seishub.xmldb.defaults import document_tab, resource_tab
from seishub.xmldb.index import XmlIndex, type_classes
from seishub.xmldb.interfaces import IXPathQuery, IResource, IXmlIndex
from seishub.xmldb.xpath import XPathQuery
from sqlalchemy import select, sql
from zope.interface.exceptions import DoesNotImplement


class _IndexViewer(object):
    """
    Mixin for XMLIndexCatalog providing "horizontal" views on the indexed data
    per resourcetype.
    """
    
    def createView(self, package, resourcetype, name = None):
        """
        Create a view for the given package and resourcetype.
        """
        name = name or '/%s/%s' % (package, resourcetype)
        q = select([document_tab.c['id'].label("document_id")])
        location_path = [package, resourcetype, None]
        q, joins = self._process_location_path(location_path, q)
        q = q.select_from(joins)
        self._db_manager.createView(name, q)
    
    def dropView(self, package, resourcetype, name = None):
        """
        Remove specified view.
        """
        name = name or '/%s/%s' % (package, resourcetype)
        self._db_manager.dropView(name)


class _QueryProcessor(object):
    """
    Mixin for XMLIndexCatalog providing query processing.
    """
    
    def _raiseIndexNotFound(self, query_base, expr):
        msg = "Error processing query. No index found for: %s"
        idx_str = '/' + '/'.join(map(str, query_base)) + expr or ''
        raise NotFoundError(msg % idx_str)
    
    def _replace_wildcards(self, expr):
        """
        Replace the xpath wildcards '*' with SQL wildcards '%'
        """
        return expr.replace('*', '%')
    
    def findIndex(self, query_base, expr = None, tolerant = True):
        """
        Tries to find the index fitting best for [package, resourcetype], expr.
        """
        # XXX: caching!
        if expr:
            expr = '/' + expr
            if '*' in expr:
                expr = DB_LIKE(self._replace_wildcards(expr))
        idx = self.pickup(XmlIndex, 
                          resourcetype = {'package':
                                          {'package_id':query_base[0]}, 
                                          'resourcetype_id':query_base[1]}, 
                          xpath = expr)
        # idx = self.getIndexes(query_base[0], , expr)
        if idx:
            return idx[0]
        if not tolerant:
            raise self._raiseIndexNotFound(query_base, expr)
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
    
    def _join_on_index(self, idx, joins = None, method = "outerjoin"):
        join = getattr(joins or document_tab, method)
        idx_tab = idx._getElementCls().db_table.alias()
        oncl = sql.and_(idx_tab.c['document_id'] == document_tab.c['id'],
                        idx_tab.c['index_id'] == idx._id)
        joins = join(idx_tab, onclause = oncl)
        return joins, idx_tab
    
    def _join_on_resourcetype(self, package, resourcetype, joins = None):
        oncl = (resource_tab.c['id'] == document_tab.c['resource_id']) 
        joins = document_tab.join(resource_tab, onclause = oncl)
        oncl = resourcetypes_tab.c['id'] == resource_tab.c['resourcetype_id']
        if resourcetype:
            oncl = sql.and_(oncl, resourcetypes_tab.c['name'] == resourcetype)
        joins = joins.join(resourcetypes_tab, onclause = oncl)
        oncl = resourcetypes_tab.c['package_id'] == packages_tab.c['id']
        if package:
            oncl = sql.and_(oncl, packages_tab.c['name'] == package)
        joins = joins.join(packages_tab, onclause = oncl)
        return joins
    
    def _process_location_path(self, location_path, q, joins = None):
        """
        Select all data indexed for the current location path, if only 
        /package/resourcetype/* is given, select all indexes for the given
        resourcetype.
        
        The column names in the selection correspond to the id of the XMLIndex.
        """
        pkg, rt = location_path[0:2]
        joins = self._join_on_resourcetype(pkg, rt)
        if len(location_path) == 3:
            # location path is on resource level
            # select *all* known indexes for that resourcetype
            indexes = self.getIndexes(pkg, rt)
        else:
            # find all indexes which fit to query
            xpath = '/'.join(location_path[2:])
            indexes = [self.findIndex([pkg, rt], xpath, False)]
        # join indexes
        for idx in indexes:
            joins, idx_tab = self._join_on_index(idx, joins)
            # also add the index keyval and group_pos to selected columns
            keyval_label = idx.label
            q.append_column(idx_tab.c['keyval'].label(keyval_label))
            if idx.group_path:
                group_pos_label = "#%s" % keyval_label
                q.append_column(idx_tab.c['group_pos'].label(group_pos_label))
        return q, joins
    
    def _process_predicates(self, p, q, joins = None):
        w = None
        if len(p) == 3:
            # binary expression
            op = p[1]
            l = p[0]
            r = p[2]
            if op in XPathQuery._relational_ops:
                # relational operator, l is a path expression => find an index
                lidx = self.findIndex([l[0], l[1]], l[2], False)
                joins, ltab = self._join_on_index(lidx, joins)
                if isinstance(r, list): # joined path query
                    ridx = self.findIndex([r[0], r[1]], r[2], False)
                    joins, rtab = self._join_on_index(ridx, joins)
                    w = ltab.c['keyval'] == rtab.c['keyval']
                else: # key / value query
                    w = self._applyOp(op, ltab.c['keyval'], lidx.prepareKey(r))
            else:
                # logical operator
                q, joins, lw = self._process_predicates(l, q, joins)
                q, joins, rw = self._process_predicates(r, q, joins)
                w = self._applyOp(op, lw, rw)
                #q = q.where(self._applyOp(op, lw, rw))
        else:
            # unary expression => require node existence
            idx = self.findIndex([p[0][0], p[0][1]], p[0][2], False)
            joins, idx_tab = self._join_on_index(idx, joins)
            w = (idx_tab.c['keyval'] != None)
        return q, joins, w
    
    def _process_order_by(self, order_by, q, joins = None):
        for ob in order_by:
            # an order_by element is of the form: 
            # [[package, resourcetype, xpath], direction]
            idx = self.findIndex([ob[0][0], ob[0][1]], ob[0][2], False)
            idx_name = str(idx)
            # if idx is already in selected columns, no need to join
            if not idx_name in q.columns:
                joins, idx_tab = self._join_on_index(idx, joins)
                col = idx_tab.c['keyval']
                q.append_column(col)
            else:
                col = q.columns[idx_name]
            o = col.asc()
            if ob[1] == "desc": 
                o = col.desc()
            q = q.order_by(o)
        return q, joins
    
    def _process_results(self, res):
        ordered = list()
        results = dict()
        for row in res:
            id = row["document_id"]
            idx_values = dict(row)
            if not id in ordered:
                ordered.append(id)
                results[id] = idx_values
            else:
                # cycle through results and reformat output to avoid duplicates
                for key, val in idx_values.iteritems():
                    # check if list; append new element, but ignore duplicates
                    if isinstance(results[id][key], list):
                        if not val in results[id][key]:
                            results[id][key].append(val)
                    else:
                        if not results[id][key] == val:
                            results[id][key] = [results[id][key]]
                            results[id][key].append(val)
        results['ordered'] = ordered
        return results
    
    def query(self, query):
        """
        Query the catalog.
        
        @param query: xpath query to be performed
        @type query: L{seishub.xmldb.interfaces.IXPathQuery}
        @return: result set containing uris of resources this query applies to
        @rtype: list of strings
        """
        if not IXPathQuery.providedBy(query):
            raise DoesNotImplement(IXPathQuery)
        location_path = query.getLocationPath()
        predicates = query.getPredicates()
        order_by = query.getOrderBy() or list()
        limit = query.getLimit()
        offset = query.getOffset()
        q = select([document_tab.c['id'].label("document_id")], 
                   use_labels = True).distinct()
        q, joins = self._process_location_path(location_path, q)
        if predicates:
            q, joins, w = self._process_predicates(predicates, q, joins)
            if w:
                q = q.where(w)
        if order_by:
            q, joins = self._process_order_by(order_by, q, joins)
        else:
            q = q.order_by(document_tab.c['id'])
        if joins:
            q = q.select_from(joins)
        q = q.limit(limit).offset(offset)
        res = self._db.execute(q)
        results = self._process_results(res)
        res.close()
        return results


class XmlIndexCatalog(DbStorage, _QueryProcessor, _IndexViewer):
    """
    A catalog of indexes.
    
    Most methods use XMLIndex objects as input parameters. You may use the
    getIndexes methods to query for valid XMLIndex objects.
    """
    def __init__(self, db, resource_storage = None):
        DbStorage.__init__(self, db)
        self._db_manager = db
        self._storage = resource_storage
    
    def registerIndex(self, xmlindex):
        """
        Register a given XMLIndex object into the XMLIndexCatalog.
        """
        if not IXmlIndex.providedBy(xmlindex):
            raise DoesNotImplement(IXmlIndex)
        try:
            self.store(xmlindex)
        except DbError, e:
            msg = "Error registering an index: Index '%s' already exists."
            raise DuplicateObjectError(msg % str(xmlindex), e)
        except Exception, e:
            msg = "Error registering an index: %s"
            raise SeisHubError(msg % str(xmlindex), e)
        return xmlindex
    
    def deleteIndex(self, xmlindex):
        """
        Delete an XMLIndex and all related indexed data from the catalog.
        """
        self.flushIndex(xmlindex)
        self.drop(XmlIndex, _id = xmlindex._id)
    
    def deleteAllIndexes(self, package_id=None, resourcetype_id=None):
        """
        Removes all indexes related to a given package_id and resourcetype_id.
        """
        pass
    
    def getIndexes(self, package_id = None, resourcetype_id = None, 
                  xpath = None, group_path = None, type = None, 
                   options = None, index_id = None, label = None):
        """
        Return a list of all applicable XMLIndex objects.
        """
        res = self.pickup(XmlIndex, 
                          resourcetype = {'package':{'package_id':package_id}, 
                                          'resourcetype_id':resourcetype_id}, 
                          label = label,
                          xpath = xpath,
                          group_path = group_path,
                          type = type,
                          options = options,
                          _id = index_id)
        return res
    
    def indexResource(self, resource, xmlindex = None, index_id = None):
        """
        Index the given resource using either all or a given XMLIndex.
        """
        if not IResource.providedBy(resource):
            raise TypeError("%s is not an IResource." % str(resource))
        package_id = resource.package.package_id
        resourcetype_id = resource.resourcetype.resourcetype_id
        index_id = (xmlindex and xmlindex._id) or index_id or None
        xmlindex_list = self.getIndexes(package_id = package_id, 
                                        resourcetype_id = resourcetype_id,
                                        index_id = index_id)
        
        elements = []
        for xmlindex in xmlindex_list:
            elements.extend(xmlindex.eval(resource.document))
        for el in elements:
            try:
                self.store(el)
            except DbError:
                # tried to store an index element with same parameters as one
                # indexed before => ignore
                pass
        return elements
    
    def dumpIndex(self, xmlindex):
        """
        Return all indexed values for a given XMLIndex.
        """
        return self.pickup(xmlindex._getElementCls(), index = xmlindex)
    
    def dumpIndexByDocument(self, document_id):
        """
        Return all IndexElements indexed for the specified document.
        """
        elements = list()
        for cls in type_classes.values():
            el = self.pickup(cls, document = {'_id':document_id})
            elements.extend(el)
        return elements
    
    def flushIndex(self, xmlindex = None, resource = None):
        """
        Remove all indexed data for given XMLIndex or Resource object.
        """
        if resource:
            for element_cls in type_classes.values():
                self.drop(element_cls, 
                          document = {'_id':resource.document._id})
            return
        element_cls = xmlindex._getElementCls()
        self.drop(element_cls, index = xmlindex)
