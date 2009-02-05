# -*- coding: utf-8 -*-

from seishub.core import implements

from seishub.exceptions import NotFoundError, InvalidObjectError 
from seishub.exceptions import InvalidParameterError
from seishub.xmldb.interfaces import IXmlCatalog, IResource, IXmlDocument
from seishub.xmldb.xmldbms import XmlDbManager
from seishub.xmldb.xmlindexcatalog import XmlIndexCatalog
from seishub.xmldb.resource import Resource, newXMLDocument
from seishub.xmldb.index import XmlIndex, TEXT_INDEX
from seishub.xmldb import index
from seishub.xmldb.xpath import XPathQuery
from seishub.util.xml import applyMacros


INDEX_TYPES = {"text":index.TEXT_INDEX,
               "numeric":index.NUMERIC_INDEX,
               "float":index.FLOAT_INDEX,
               "datetime":index.DATETIME_INDEX,
               "boolean":index.BOOLEAN_INDEX,
               "date":index.DATE_INDEX,
               #"nonetype":index.NONETYPE_INDEX
               }


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
        """
        Add a new resource to the database.
        
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
        # get xml_doc to ensure the document is parsed
        res.document.xml_doc
        self.schemaValidate(res)
        self.xmldb.addResource(res)
        self.indexResource(resource = res)
        return res
    
    def moveResource(self, package_id, resourcetype_id, old_name, new_name):
        """
        Move or rename a resource.
        """
        self.xmldb.moveResource(package_id, resourcetype_id, old_name, 
                                new_name)
    
    def modifyResource(self, package_id, resourcetype_id, xml_data, name):
        """
        Modify the XML document of an already existing resource.
        
        In case of a version controlled resource a new revision is created.
        """
        _, resourcetype = self.env.registry.objects_from_id(package_id, 
                                                            resourcetype_id)
        res = Resource(resourcetype, document = newXMLDocument(xml_data),
                       name = name)
        self.schemaValidate(res)
        old_res = self.getResource(package_id, resourcetype_id, name)
        self.xmldb.modifyResource(res, old_res.id)
        # XXX: this way we only keep indexes for the newest revision, 
        # is that intended?
        self.index_catalog.flushIndex(resource = old_res)
        self.indexResource(resource = res)
    
    def deleteResource(self, package_id = None, resourcetype_id = None, 
                       name = None, revision = None, document_id = None):
        """
        Remove a resource from the database.
        
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
                                        document_id)
        if not res:
            msg = "Error deleting a resource: No resource was found with " + \
                  "the given parameters."
            raise NotFoundError(msg)
        return res
    
    def deleteAllResources(self, package_id, resourcetype_id):
        """
        Remove all resources of specified package and resourcetype.
        """
        return self.xmldb.deleteResources(package_id, resourcetype_id)
    
    def getResource(self, package_id, resourcetype_id, name, revision = None):
        """
        Get a specific resource from the database.
        
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
        """
        Get all revisions of the specified resource.
        
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
        """
        Get a list of resources for specified package and resourcetype.
        """
        return self.xmldb.getResourceList(package_id, resourcetype_id)
    
    def revertResource(self, package_id, resourcetype_id, name, revision):
        """
        Reverts the specified revision for the given resource.
        
        All revisions newer than the specified one will be removed.
        """
        return self.xmldb.revertResource(package_id, resourcetype_id, name, 
                                         revision)
    
    def schemaValidate(self, resource):
        """
        Do a schema validation of a given resource.
        
        This validates against all schemas of the corresponding resourcetype.
        """
        pid = resource.package.package_id
        rid = resource.resourcetype.resourcetype_id
        schemas = self.env.registry.schemas.get(pid, rid)
        for schema in schemas:
            try:
                schema.validate(resource)
            except Exception, e: 
                msg = "Resource-validation against schema '%s' failed. (%s)"
                raise InvalidObjectError(msg % (str(schema.getResource().name), 
                                                e.message))
    
    # xmlindexcatalog methods
    def registerIndex(self, package_id = None, resourcetype_id = None, 
                      xpath = None, type = "text", options = None):
        """
        Register an index.
        
        @param type: "text"|"numeric"|"float"|"datetime"|"boolean"|"date"
        """
        # check for XPath expression
        if not xpath:
            msg = "registerIndex: Empty XPath expression!"
            raise InvalidParameterError(msg)
        # check if valid index type
        if type.lower() not in INDEX_TYPES:
            msg = "registerIndex: Invalid index type '%s'."
            raise InvalidParameterError(msg % type)
        # check for grouping indexes
        xpath = xpath.strip()
        group_path = None
        if '#' in xpath:
            try:
                group_path, temp = xpath.split('#')
            except ValueError, e:
                msg = "registerIndex: Invalid index expression. %s"
                raise InvalidParameterError(msg % str(e))
            xpath = '/'.join([group_path, temp])
        type = INDEX_TYPES.get(type.lower())
        _, resourcetype = self.env.registry.objects_from_id(package_id, 
                                                            resourcetype_id)
        # generate index
        index = XmlIndex(resourcetype, xpath, type, options, group_path)
        index = self.index_catalog.registerIndex(index)
        # reindex
        self.reindex(package_id, resourcetype_id, xpath)
        # create or update view:
        self.index_catalog.createView(package_id, resourcetype_id)
        return index
    
    def removeIndex(self, package_id = None, resourcetype_id = None, 
                    xpath = None):
        """
        Remove an index.
        """
        res = self.index_catalog.removeIndex(package_id, resourcetype_id, 
                                             xpath)
        # create or update view:
        self.index_catalog.createView(package_id, resourcetype_id)
        return res 
    
    def getIndex(self, package_id = None, resourcetype_id = None, 
                 xpath = None, group_path = None, type = "text", 
                 options = None):
        """
        @see: L{seishub.xmldb.interfaces.IXmlCatalog}
        """
        # check for grouping indexes
        if '#' in xpath:
            group_path, temp = xpath.split('#', 1)
            xpath = '/'.join([group_path, temp])
        type = INDEX_TYPES.get(type.lower(), TEXT_INDEX)
        return self.index_catalog.getIndexes(package_id, resourcetype_id, 
                                             xpath, group_path, type, options)
    
    def getIndexData(self, resource):
        """
        Return all indexed data for the given resource as a dictionary.
        
        @param resource: resource or document
        @type resource: L{seishub.xmldb.interfaces.IResource} or
                        L{seishub.xmldb.interfaces.IXmlDocument}
        """
        if IResource.providedBy(resource):
            doc = resource.document
        elif IXmlDocument.providedBy(resource):
            doc = resource
        else:
            msg = "getIndexData: Resource or XmlDocument expected. Got a %s."
            raise TypeError(msg % type(resource))
        # sanity check: document should have an id, else no data can be found
        assert doc._id
        elmts = self.index_catalog.dumpIndexByDocument(doc._id)
        values = {}
        for el in elmts:
            values[el.index.xpath] = el.key
        return values
    
    def flushIndex(self, package_id = None, resourcetype_id = None, 
                   xpath = None):
        """
        @see: L{seishub.xmldb.interfaces.IXmlCatalog}
        """
        return self.index_catalog.flushIndex(package_id, resourcetype_id, 
                                             xpath)
    
    def listIndexes(self, package_id = None, resourcetype_id = None, 
                    type = "text"):
        """
        @see: L{seishub.xmldb.interfaces.IXmlCatalog}
        """
        type = INDEX_TYPES.get(type.lower(), TEXT_INDEX)
        return self.index_catalog.getIndexes(package_id, resourcetype_id, 
                                             type = type)
    
    def indexResource(self, package_id = None, resourcetype_id = None, 
                      name = None, revision = None, resource = None):
        if package_id and resourcetype_id and name:
            resource = self.getResource(package_id, resourcetype_id, name, 
                                        revision)
        elif not resource:
            raise TypeError("indexResource: Invalid number of arguments.")
        return self.index_catalog.indexResource(resource)
    
    def reindex(self, package_id = None, resourcetype_id = None, xpath = None):
        """
        @see: L{seishub.xmldb.interfaces.IXmlCatalog}
        """
        self.flushIndex(package_id, resourcetype_id, xpath)
        reslist = self.getResourceList(package_id, resourcetype_id)
        # reindex
        for res in reslist:
            self.index_catalog.indexResource(res, xpath)
        return True
    
    def query(self, query, full = False):
        """
        Query the catalog via restricted XPath queries.
        
        The values returned depend on the type of query:
        
        Is the location path of a query on resource level, i.e. on rootnode or 
        above (e.g. '/package/resourcetype/*'), ALL indexes known for that 
        resource are requested and returned as a dict.
        
        Does the location path address a node other than the rootnode (e.g.
        '/package/resourcetype/rootnode/node1/node2'), indexed data for that
        node ONLY is returned. 
        Note: The index '/package/resourcetype/rootnode/node1/node2' has to 
        exist, of course. 
        
        The result set is a dict of the form {document_ids : {xpath:value}, 
        ...}. 
        There is an additional key 'ordered' containing an ORDERED list of
        document ids, which is of interest in case there is an order by clause,
        as the dict itself does not preserve order.
        
        For further detail on the restricted XPath query syntax, see 
        L{seishub.xmldb.xpath}
        
        @param query: Restricted XPath query to be executed.
        @type query: basestring
        @param full: If True, picks the resource objects for the results
        @return: Either a list of Resource objects, or a dict
        """
        # XXX: query by metadata?
        query = applyMacros(query)
        q = XPathQuery(query)
        results = self.index_catalog.query(q)
        if not full:
            return results
        return [self.xmldb.getResource(document_id = id) 
                for id in results['ordered']]
