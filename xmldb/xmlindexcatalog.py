# -*- coding: utf-8 -*-

from seishub.db import util
from seishub.db.orm import DbStorage, DbError, DB_LIKE
from seishub.exceptions import InvalidParameterError, SeisHubError, \
    NotFoundError, InvalidObjectError, DuplicateObjectError
from seishub.registry.defaults import resourcetypes_tab, packages_tab
from seishub.xmldb.defaults import document_tab, resource_tab
from seishub.xmldb.index import XmlIndex, type_classes
from seishub.xmldb.interfaces import IXPathQuery, IResource, IXmlIndex
from seishub.xmldb.xpath import XPathQuery
from sqlalchemy import select, sql
from zope.interface.exceptions import DoesNotImplement


class _IndexView(object):
    """
    Mixin for XMLIndexCatalog providing "horizontal" SQL views on the indexed 
    data per resource type.
    """
    
    def createIndexView(self, xmlindex):
        """
        Create a index view using the given XMLIndex.
        """
        package_id = xmlindex.resourcetype.package.package_id
        resourcetype_id = xmlindex.resourcetype.resourcetype_id 
        name = '/%s/%s' % (package_id, resourcetype_id)
        q = select([document_tab.c['id'].label("document_id"),
                    packages_tab.c['name'].label("package_id"),
                    resourcetypes_tab.c['name'].label("resourcetype_id"),
                    resource_tab.c['name'].label("resource_name")])
        location_path = [package_id, resourcetype_id, None]
        q, joins = self._process_location_path(location_path, q)
        q = q.select_from(joins)
        self._db_manager.createView(name, util.compileStatement(q))
    
    def dropIndexView(self, xmlindex):
        """
        Removes a index view from the database using a given XMLIndex.
        """
        package_id = xmlindex.resourcetype.package.package_id
        resourcetype_id = xmlindex.resourcetype.resourcetype_id 
        name = '/%s/%s' % (package_id, resourcetype_id)
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
    
    def findIndex(self, query_base, expr = None):
        """
        Tries to find a fitting index for [package, resourcetype] and
        the given xpath expr or label.
        """
        idx = None
        # try via label if only one single node is given:
        if not '/' in expr:
            idx = self.getIndexes(query_base[0], query_base[1], label = expr)
            if idx:
                return idx[0]
        # still there: multiple nodes or no label found
        if expr:
            expr = '/' + expr
        if '*' in expr:
            # XXX: workaround until the cache supports wildcard expressions
            idx = self.pickup(XmlIndex, 
                        resourcetype = {'package':{'package_id':query_base[0]}, 
                                        'resourcetype_id':query_base[1]}, 
                        xpath = DB_LIKE(self._replace_wildcards(expr)))
            if idx:
                return idx[0]
        idx = self.getIndexes(query_base[0], query_base[1], xpath = expr)
        if idx:
            return idx[0]
        # still there: no index found
        if hasattr(expr, 'value'):
            expr = expr.value
        raise self._raiseIndexNotFound(query_base, expr)
    
    def _isLogOp(self, p):
        return p[1] in XPathQuery._logical_ops
    
    def _isRelOp(self, p):
        return p[1] in XPathQuery._relational_ops
    
    def _applyOp(self, op, left, right, complement = False):
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
            if complement:
                return sql.or_(left, right)
            return sql.and_(left, right)
        elif op == 'or':
            if complement:
                return sql.and_(left, right)
            return sql.or_(left, right)
        raise InvalidParameterError("Operator '%s' not specified." % op)
    
    def _applyFunc(self, func, expr, q, joins):
        if func == 'not':
            # select the complementary result set
            return self._process_predicates(expr, q, joins, complement = True)
        raise InvalidParameterError("Function '%s' not specified." % func)
    
    def _join_on_index(self, idx, joins = None, method = "outerjoin", 
                       complement = False):
        join = getattr(joins or document_tab, method)
        idx_tab = idx._getElementCls().db_table.alias()
        if complement:
            # if complement is set, return all rows NOT corresponding to the
            # selected rows via where clause! 
            doc_clause = idx_tab.c['document_id'] != document_tab.c['id']
        else:
            # select all rows of a document, if one row fits the where clause
            doc_clause = idx_tab.c['document_id'] == document_tab.c['id']
        oncl = sql.and_(doc_clause, idx_tab.c['index_id'] == idx._id)
        joins = join(idx_tab, onclause = oncl)
        return joins, idx_tab
    
    def _join_on_resourcetype(self, package, resourcetype, joins = None):
        oncl = (resource_tab.c['id'] == document_tab.c['resource_id'])
        if not joins:
            joins = document_tab.join(resource_tab, onclause = oncl)
        else:
            joins = joins.join(resource_tab, onclause = oncl)
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
        if len(location_path)<=3:
            # location path is on resource level
            # select *all* known indexes for that resourcetype
            indexes = self.getIndexes(pkg, rt)
        else:
            # find all indexes which fit to query
            xpath = '/'.join(location_path[2:])
            indexes = [self.findIndex([pkg, rt], xpath)]
        # join indexes
        group_paths = {}
        for idx in indexes:
            idx_tab = idx._getElementCls().db_table.alias()
            idx_gp = idx.group_path
            idx_id = int(idx._id)
            # add keyval to selected columns
            keyval_label = idx.label
            q.append_column(idx_tab.c['keyval'].label(keyval_label))
            join = getattr(joins or document_tab, "outerjoin")
            if idx_gp not in group_paths:
                # first time we meet a grouping element
                oncl = sql.and_(idx_tab.c['document_id'] == document_tab.c['id'],
                                idx_tab.c['index_id'] == idx_id)
                group_paths[idx_gp]=idx_tab
            else:
                # here we know the grouping element
                oncl = sql.and_(idx_tab.c['document_id'] == document_tab.c['id'],
                                idx_tab.c['index_id'] == idx_id,
                                idx_tab.c['group_pos'] == group_paths[idx_gp].c['group_pos'])
            joins = join(idx_tab, onclause = oncl)
        joins = self._join_on_resourcetype(pkg, rt, joins)
        return q, joins
    
    def _process_predicates(self, p, q, joins = None, complement = False):
        w = None
        if len(p) == 3:
            # binary expression
            op = p[1]
            l = p[0]
            r = p[2]
            if op in XPathQuery._relational_ops:
                # relational operator, l is a path expression => find an index
                lidx = self.findIndex([l[0], l[1]], l[2])
                joins, ltab = self._join_on_index(lidx, joins, 
                                                  complement = complement)
                if isinstance(r, list): # joined path query
                    ridx = self.findIndex([r[0], r[1]], r[2])
                    joins, rtab = self._join_on_index(ridx, joins, 
                                                      complement = complement)
                    w = ltab.c['keyval'] == rtab.c['keyval']
                else: # key / value query
                    w = self._applyOp(op, ltab.c['keyval'], lidx.prepareKey(r))
            else:
                # logical operator
                q, joins, lw = self._process_predicates(l, q, joins, 
                                                       complement = complement)
                q, joins, rw = self._process_predicates(r, q, joins, 
                                                       complement = complement)
                w = self._applyOp(op, lw, rw, complement)
        elif len(p) == 2:
            # function
            func = p[0]
            expr = p[1]
            q, joins, w = self._applyFunc(func, expr, q, joins)
        else:
            # unary expression => require node existence
            idx = self.findIndex([p[0][0], p[0][1]], p[0][2])
            joins, idx_tab = self._join_on_index(idx, joins, 
                                                 complement = complement)
            w = (idx_tab.c['keyval'] != None)
        return q, joins, w
    
    def _process_order_by(self, order_by, q, joins = None):
        for ob in order_by:
            # an order_by element is of the form: 
            # [[package, resourcetype, xpath], direction]
            idx = self.findIndex([ob[0][0], ob[0][1]], ob[0][2])
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
        q = select([document_tab.c['id'].label("document_id"),
                    packages_tab.c['name'].label("package_id"),
                    resourcetypes_tab.c['name'].label("resourcetype_id"),
                    resource_tab.c['name'].label("resource_name")], 
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


class XmlIndexCatalog(DbStorage, _QueryProcessor, _IndexView):
    """
    A catalog of indexes.
    
    Most methods use XMLIndex objects as input parameters. You may use the
    getIndexes methods to query for valid XMLIndex objects.
    """
    def __init__(self, db, resource_storage = None):
        DbStorage.__init__(self, db)
        self._db_manager = db
        self._storage = resource_storage
        self.refreshIndexCache()
    
    def refreshIndexCache(self):
        """
        Refreshs the index cache.
        """
        self._cache = {'package_id':{}, 'resourcetype_id':{}, 'xpath':{},
                       'group_path':{}, 'type':{}, 'options':{}, '_id':{},
                       'label':{}
                       }
        # get all indexes
        indexes = self.pickup(XmlIndex)
        for idx in indexes:
            self._addToCache(idx)
    
    def _addToCache(self, xmlindex):
        """
        Adds a given XMLIndex to the index cache.
        """
        for attr in self._cache:
            key = getattr(xmlindex, attr)
            if not key:
                continue
            if not key in self._cache[attr]:
                self._cache[attr][key] = set([xmlindex])
            else:
                self._cache[attr][key].add(xmlindex)
    
    def _deleteFromCache(self, xmlindex):
        """
        Deletes a given XMLIndex from the index cache.
        """
        for attr in self._cache:
            key = getattr(xmlindex, attr)
            if key in self._cache[attr]:
                self._cache[attr][key].discard(xmlindex)
    
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
        #self._addToCache(xmlindex)
        return xmlindex
    
    def deleteIndex(self, xmlindex):
        """
        Delete an XMLIndex and all related indexed data from the catalog.
        """
        if not xmlindex._id:
            msg = "DeleteIndex: an XmlIndex has no id."
            raise InvalidObjectError(msg)
        self.flushIndex(xmlindex)
        self.drop(XmlIndex, _id = xmlindex._id)
        #self._deleteFromCache(xmlindex)
    
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
#        index_sets = list()
#        arglist = {'package_id':package_id, 
#                   'resourcetype_id':resourcetype_id, 'xpath':xpath, 
#                   'group_path':group_path, 'type':type, 'options':options, 
#                   '_id':index_id, 'label':label}
#        for key, value in arglist.iteritems():
#            if not value:
#                continue
#            idx = self._cache[key].get(value, set())
#            if not idx:
#                return list()
#            index_sets.append(idx)
#        if not index_sets:
#            # return all
#            try:
#                return [list(val)[0] for val in self._cache['_id'].values()]
#            except:
#                b=1
#                import pdb;pdb.set_trace()
#                a=1
#        indexes = index_sets.pop(0).copy()
#        for idxs in index_sets:
#            indexes.intersection_update(idxs)
#        return list(indexes)
    
    def indexResource(self, resource, xmlindex = None):
        """
        Index the given resource using either all or a given XMLIndex.
        """
        if not IResource.providedBy(resource):
            raise TypeError("%s is not an IResource." % str(resource))
        package_id = resource.package.package_id
        resourcetype_id = resource.resourcetype.resourcetype_id
        if xmlindex:
            xmlindex_list = [xmlindex]
        else:
            xmlindex_list = self.getIndexes(package_id = package_id, 
                                            resourcetype_id = resourcetype_id)
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
    
    def flushIndex(self, xmlindex):
        """
        Remove all indexed data for given XMLIndex object.
        """
        element_cls = xmlindex._getElementCls()
        self.drop(element_cls, index = xmlindex)
    
    def flushResource(self, resource):
        """
        Remove all indexed data for given Resource object.
        """
        for element_cls in type_classes.values():
            self.drop(element_cls, 
                      document = {'_id':resource.document._id})
        return
    
###############
    
#    def reindexPackage(self, package_id, resourcetype_id=None):
#        """
#        Reindex all resources within a given package_id and resourcetype_id.
#        """
#        xmlindex_list = self.getIndexes(package_id = package_id,
#                                        resourcetype_id = resourcetype_id)
#        # clear all package/resource type specific indexes
#        for xmlindex in xmlindex_list:
#            self.flushIndex(xmlindex)
#        # create a dictionary of resourcetype specific indexes
#        resourcetype_ids = 
    
    def reindexIndex(self, xmlindex):
        """
        Reindex all resources by a given XMLIndex object.
        """
        if not IXmlIndex.providedBy(xmlindex):
            raise TypeError("%s is not an IXmlIndex." % str(xmlindex))
        # clear index
        self.flushIndex(xmlindex)
        # fetch all document_id with highest revision for this resource type
        query = sql.select([document_tab.c['id'], 
                            sql.func.max(document_tab.c['revision'])])
        query = query.where(
            sql.and_(
                document_tab.c['resource_id'] == resource_tab.c['id'], 
                resource_tab.c['resourcetype_id'] == xmlindex.resourcetype._id
            ))
        query = query.group_by(document_tab.c['id'])
        result = self._db.execute(query)
        # iterate over all document IDs and reindex
        for item in result:
            res = self._storage.getResource(document_id=item.id)
            self.indexResource(res, xmlindex)
        return True
