# -*- coding: utf-8 -*-

from zope.interface import implements

from seishub.exceptions import NotFoundError, InvalidObjectError
from seishub.xmldb.interfaces import IXmlCatalog
from seishub.xmldb.xmldbms import XmlDbManager
from seishub.xmldb.xmlindexcatalog import XmlIndexCatalog
from seishub.xmldb.resource import Resource, newXMLDocument
from seishub.xmldb.index import XmlIndex, TEXT_INDEX
from seishub.xmldb import index
from seishub.xmldb.xpath import IndexDefiningXpathExpression, XPathQuery
from seishub.util.xml import applyMacros


INDEX_TYPES = {"text":index.TEXT_INDEX,
               "numeric":index.NUMERIC_INDEX,
               "float":index.FLOAT_INDEX,
               "datetime":index.DATETIME_INDEX,
               "boolean":index.BOOLEAN_INDEX,
               "nonetype":index.NONETYPE_INDEX}

class XmlCatalog(object):
    implements(IXmlCatalog)
    
    def __init__(self, env):
        self.env = env
        self.xmldb = XmlDbManager(env.db)
        self.index_catalog = XmlIndexCatalog(env.db, self.xmldb)
        
    def _to_xpath(self, pid, rid, expr):
        if not expr.startswith('/'):
            expr = '/' + expr
        return '/' + pid + '/' + rid + expr
    
    def _convert_wildcards(self, item):
        if item == '*':
            return None
        return item
        
    # methods from IXmlCatalog
    # xmldbms methods
    def addResource(self, package_id, resourcetype_id, xml_data, uid = None, 
                    name = None):
        """Add a new resource to the database.
        
        @param package_id: package id
        @param resourcetype_id: resourcetype id
        @param xml_data: xml data
        @param uid: user id of creator
        @param name: optional resource name, defaults to unique integer id
        @return: Resource object
        """
        _, resourcetype = self.env.registry.objects_from_id(package_id, 
                                                            resourcetype_id)
        res = Resource(resourcetype, 
                       document = newXMLDocument(xml_data, uid = uid), 
                       name = name)
        self.schemaValidate(res)
        self.xmldb.addResource(res)
        self.indexResource(resource = res)
        return res
    
    def moveResource(self, package_id, resourcetype_id, old_name, new_name):
        """Rename a resource."""
        self.xmldb.moveResource(package_id, resourcetype_id, old_name, 
                                new_name)
    
    def modifyResource(self, package_id, resourcetype_id, name, xml_data):
        """Modify the XML document of an already existing resource.
        In case of a version controlled resource a new revision is created.
        """
        _, resourcetype = self.env.registry.objects_from_id(package_id, 
                                                            resourcetype_id)
        res = Resource(resourcetype, document = newXMLDocument(xml_data),
                       name = name)
        self.schemaValidate(res)
        old_res = self.getResource(package_id, resourcetype_id, name)
        self.xmldb.modifyResource(res, old_res.id)
        
    def deleteResource(self, package_id = None, resourcetype_id = None, 
                       name = None, revision = None, document_id = None):
        """Remove a resource from the database.
        By either (package_id, resourcetype_id, name, revision = None) or
        by document_id.
        
        Note for version controlled resources:
        If no revision is specified all revisions of the resource all deleted;
        otherwise only the specified revision is removed.
        
        If a document_id is specified the resource having that document is 
        deleted, together with all other documents linked to that resource!
        """
        if not ((package_id and resourcetype_id and name and not document_id) \
                or document_id):
            raise TypeError("deleteResource(): invalid number of arguments!")
        # remove indexed data:
        # XXX: workaround!
        res = self.xmldb.getResource(package_id, resourcetype_id, name, 
                                     revision, document_id)
        self.index_catalog.flushIndex(resource = res)
        # END workaround
        if revision:
            return self.xmldb.deleteRevision(package_id, resourcetype_id, name, 
                                             revision = revision)
        res = self.xmldb.deleteResource(package_id, resourcetype_id, name, 
                                        revision, document_id)
        if not res:
            msg = "Error deleting a resource: No resource was found with " + \
                  "the given parameters."
            raise NotFoundError(msg)
        return res
    
    def deleteAllResources(self, package_id, resourcetype_id):
        """Remove all resources of specified package and resourcetype."""
        return self.xmldb.deleteResources(package_id, resourcetype_id)
    
    def deleteRevisions(self, package_id, resourcetype_id, name):
        self.env.log.warn("Deprecation warning: xmlcatalog.deleteRevisions()"+\
                          "is deprecated, use xmlcatalog.deleteResource() "+\
                          "instead")
        return self.deleteResource(package_id, resourcetype_id, name)
    
    def getResource(self, package_id, resourcetype_id, name, revision = None):
        """Get a specific resource from the database.
        
        @param package_id: resourcetype id
        @param: resourcetype_id: package id
        @param name: Name of the resource
        @param revision: revision of related document (if no revision is given,
            newest revision is used, to retrieve all revisions of a document  
            use getResourceHistory(...)
        """
        return self.xmldb.getResource(package_id, resourcetype_id, name, 
                                      revision)
    
    def getResourceHistory(self, package_id, resourcetype_id, name):
        """Get all revisions of the specified resource.
        
        The Resource instance returned will contain a list of documents sorted 
        by revision (accessible as usual via Resource.document).
        Note: In case a resource does not provide multiple revisions, this is 
        the same as a call to XmlCatalog.getResource(...).
        
        @param package_id: package id
        @param resourcetype_id: resourcetype id
        @param name: name of the resource
        @return: Resource object
        """
        return self.xmldb.getResourceHistory(package_id, resourcetype_id, name)
        
    def getResourceList(self, package_id = None, resourcetype_id = None):
        """Get a list of resources for specified package and resourcetype"""
        return self.xmldb.getResourceList(package_id, resourcetype_id)
    
    def revertResource(self, package_id, resourcetype_id, name, revision):
        """Reverts the specified revision for the given resource.
        All revisions newer than the specified one will be removed.
        """
        return self.xmldb.revertResource(package_id, resourcetype_id, name, 
                                         revision)
        
    def schemaValidate(self, resource):
        """Do a schema validation of given resource with all known schemas of
        corresponding resourcetype."""
        pid = resource.package.package_id
        rid = resource.resourcetype.resourcetype_id
        schemas = self.env.registry.schemas.get(pid, rid)
        for schema in schemas:
            if not schema.validate(resource):
                msg = "Validation of a resource against schema '%s' failed."
                raise InvalidObjectError(msg % str(schema))

    # xmlindexcatalog methods
    def registerIndex(self, package_id = None, resourcetype_id = None, 
                      xpath = None, type = "text", options = None):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        type = INDEX_TYPES.get(type.lower(), TEXT_INDEX)
        _, resourcetype = self.env.registry.objects_from_id(package_id, 
                                                            resourcetype_id)
        index = XmlIndex(resourcetype, xpath, type, options)
        index = self.index_catalog.registerIndex(index)
        self.reindex(package_id, resourcetype_id, xpath)
        return index
        
    
    def removeIndex(self, package_id = None, resourcetype_id = None, 
                    xpath = None):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        return self.index_catalog.removeIndex(package_id, resourcetype_id, 
                                              xpath)
        
    def getIndex(self, package_id = None, resourcetype_id = None, 
                 xpath = None, type = "text", options = None):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        type = INDEX_TYPES.get(type.lower(), TEXT_INDEX)
        return self.index_catalog.getIndexes(package_id, resourcetype_id, 
                                             xpath, type, options)
        
    def getIndexData(self, resource):
        """Return all indexed data for the given resource as a dictionary."""
        elmts = self.index_catalog.dumpIndexByDocument(resource.document._id)
        values = {}
        for el in elmts:
            values[el.index.xpath] = el.key
        return values
        
    def flushIndex(self, package_id = None, resourcetype_id = None, 
                   xpath = None):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
#        if package_id and resourcetype_id:
#            expr = self._to_xpath(package_id, resourcetype_id, xpath)
#        else:
#            # assume that xpath starts with '/package_id/resourcetype_id'
#            expr = xpath
        # exp_obj = IndexDefiningXpathExpression(expr)
        return self.index_catalog.flushIndex(package_id, resourcetype_id, 
                                             xpath)
        
    def listIndexes(self, package_id = None, resourcetype_id = None, 
                    type = "text"):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
#        if not (package_id or resourcetype_id):
#            return self.index_catalog.getIndexes(data_type = data_type)
        
        # value path has the following form /package_id/resourcetype_id/rootnode
        # XXX: rootnode to be removed 
#        value_path = ''
#        if package_id:
#            value_path += package_id + '/'
#        else:
#            value_path += '*/'
#        if resourcetype_id:
#            value_path += resourcetype_id + '/'
#        else:
#            value_path += '*/'
#        value_path += '*'
        type = INDEX_TYPES.get(type.lower(), TEXT_INDEX)
        return self.index_catalog.getIndexes(package_id, resourcetype_id, 
                                             type = type)
        
    def indexResource(self, package_id = None, resourcetype_id = None, 
                      name = None, revision = None, resource = None):
        if package_id and resourcetype_id and name:
            resource = self.getResource(package_id, resourcetype_id, name, 
                                        revision)
        elif not resource:
            raise TypeError("Invalid number of arguments.")
        return self.index_catalog.indexResource(resource)
        
        
#        indexes = self.listIndexes(package_id, resourcetype_id)
#        for idx in indexes:
#            self.index_catalog.indexResource(resource.document._id, 
#                                             idx.value_path, 
#                                             idx.key_path)
        
    def reindex(self, package_id = None, resourcetype_id = None, xpath = None):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
#        if package_id and resourcetype_id:
#            expr = self._to_xpath(package_id, resourcetype_id, xpath)
#        else:
#            # assume that xpath starts with '/package_id/resourcetype_id'
#            expr = xpath
            
#        # get index
#        index = self.index_catalog.getIndexes(package_id, resourcetype_id, 
#                                              xpath)
#        
#        # flush index
        
#        
#        # find all resources the index applies to by resource type
#        # value_path = index.value_path
#        # key_path = index.key_path
#        xpath = index.xpath
##        if value_path.startswith('/'):
##            value_path = value_path[1:]
#        #XXX: rootnode ??
#        # package, type, rootnode  = value_path.split('/')
        self.flushIndex(package_id, resourcetype_id, xpath)
        reslist = self.getResourceList(package_id, resourcetype_id)
        # reindex
        for res in reslist:
            self.index_catalog.indexResource(res, xpath)
        return True
        
    def query(self, query, order_by = None, limit = None):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        # XXX: query by metadata
        if isinstance(query, dict):
            order_by = query.get('order_by', None)
            limit = query.get('limit', None)
            query = query.get('query', '')
        # remove line breaks and apply macros
        query = applyMacros(query)
        qu = map(self._convert_wildcards, query.split('/'))
        if len(qu) == 4 and not qu[3]:
            # XXX: this is not an index query ,but this should be handled by 
            # the index catalog as well in case an order by clause is present
            return self.getResourceList(qu[1], qu[2])
        q = XPathQuery(query, order_by, limit)
        doc_ids = self.index_catalog.query(q)
        # XXX: this is really bad, what information is really needed in the first place?
        return [self.xmldb.getResource(document_id = id) for id in doc_ids]
            
        
