# -*- coding: utf-8 -*-

from zope.interface import implements

from seishub.exceptions import NotFoundError
from seishub.xmldb.interfaces import IXmlCatalog
from seishub.xmldb.xmldbms import XmlDbManager
from seishub.xmldb.xmlindexcatalog import XmlIndexCatalog
from seishub.xmldb.resource import Resource, newXMLDocument
from seishub.xmldb.index import XmlIndex
from seishub.xmldb.xpath import IndexDefiningXpathExpression, XPathQuery

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
        self.xmldb.addResource(res)
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
        old_res = self.getResource(package_id, resourcetype_id, name)
        res = Resource(resourcetype, document = newXMLDocument(xml_data),
                       name = name)
        self.xmldb.modifyResource(res, old_res.id)
        
    def deleteResource(self, package_id, resourcetype_id, name, revision=None):
        """Remove a resource from the database.
        
        Note for version controlled resources:
        If no revision is specified all revisions of the resource all deleted;
        otherwise only the specified revision is removed.
        """
        if revision:
            return self.xmldb.deleteRevision(package_id, resourcetype_id, name, 
                                             revision = revision)
        res = self.xmldb.deleteResource(package_id, resourcetype_id, name, 
                                        revision)
        if not res:
            msg = "Error deleting a resource: No resource was found with " + \
                  "the given parameters. (%s/%s/%s)"
            raise NotFoundError(msg % (package_id, resourcetype_id, name))
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
        
#    def resourceExists(self, package_id, resourcetype_id, name):
#        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
#        raise NotImplementedError("resourceExists not implemented")
    
    # xmlindexcatalog methods
    def registerIndex(self, package_id = None, resourcetype_id = None, 
                      xpath = None, type = "text"):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        if package_id and resourcetype_id:
            expr = self._to_xpath(package_id, resourcetype_id, xpath)
        else:
            # assume that xpath starts with '/package_id/resourcetype_id'
            expr = xpath
        exp_obj = IndexDefiningXpathExpression(expr)
        index = XmlIndex(value_path = exp_obj.value_path, 
                         key_path = exp_obj.key_path)
        index = self.index_catalog.registerIndex(index)
        self.reindex(package_id, resourcetype_id, xpath)
        return index
        
    
    def removeIndex(self,package_id = None, resourcetype_id = None, 
                    xpath = None):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        if package_id and resourcetype_id:
            expr = self._to_xpath(package_id, resourcetype_id, xpath)
        else:
            # assume that xpath starts with '/package_id/resourcetype_id'
            expr = xpath
        exp_obj = IndexDefiningXpathExpression(expr)
        return self.index_catalog.removeIndex(value_path = exp_obj.value_path,
                                              key_path = exp_obj.key_path)
        
    def getIndex(self, package_id = None, resourcetype_id = None, 
                 xpath = None, type = None):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        if package_id and resourcetype_id:
            expr = self._to_xpath(package_id, resourcetype_id, xpath)
        else:
            # assume that xpath starts with '/package_id/resourcetype_id'
            expr = xpath
        return self.index_catalog.getIndex(expr = expr)
        
    def flushIndex(self, package_id = None, resourcetype_id = None, 
                   xpath = None):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        if package_id and resourcetype_id:
            expr = self._to_xpath(package_id, resourcetype_id, xpath)
        else:
            # assume that xpath starts with '/package_id/resourcetype_id'
            expr = xpath
        exp_obj = IndexDefiningXpathExpression(expr)
        return self.index_catalog.flushIndex(value_path = exp_obj.value_path,
                                             key_path = exp_obj.key_path)
        
    def listIndexes(self,package_id = None, resourcetype_id = None, 
                    data_type = None):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        if not (package_id or resourcetype_id):
            return self.index_catalog.getIndexes(data_type = data_type)
        
        # value path has the following form /package_id/resourcetype_id/rootnode
        # XXX: rootnode to be removed 
        value_path = ''
        if package_id:
            value_path += package_id + '/'
        else:
            value_path += '*/'
        if resourcetype_id:
            value_path += resourcetype_id + '/'
        else:
            value_path += '*/'
        value_path += '*'
        return self.index_catalog.getIndexes(value_path,
                                             data_type = data_type)
        
    def indexResource(self, package_id, resourcetype_id, name, revision = None,
                      resource = None):
        if package_id and resourcetype_id and name:
            resource = self.getResource(package_id, resourcetype_id, name, 
                                        revision)
        elif not resource:
            raise TypeError("Invalid number of arguments.")
        indexes = self.listIndexes(package_id, resourcetype_id)
        for idx in indexes:
            self.index_catalog.indexResource(resource.document._id, 
                                             idx.value_path, 
                                             idx.key_path)
        
    def reindex(self, package_id = None, resourcetype_id = None, xpath = None):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        if package_id and resourcetype_id:
            expr = self._to_xpath(package_id, resourcetype_id, xpath)
        else:
            # assume that xpath starts with '/package_id/resourcetype_id'
            expr = xpath
            
        # get index
        index = self.index_catalog.getIndex(expr = expr)
        
        # flush index
        self.flushIndex(xpath = expr)
        
        # find all resources the index applies to by resource type
        value_path = index.value_path
        key_path = index.key_path
        if value_path.startswith('/'):
            value_path = value_path[1:]
        #XXX: rootnode to be removed
        package, type, rootnode  = value_path.split('/')
        reslist = self.getResourceList(package_id = package, 
                                       resourcetype_id = type)
        # reindex
        for res in reslist:
            self.index_catalog.indexResource(res.document._id, 
                                             value_path, key_path)
        
        return True
        
    def query(self, query, order_by = None, limit = None):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        # XXX: query by creator, size, hash, timestamp
        # TODO: workaround until indexes support package/resourcetype natively
        try:
            qu = query.get('query')
        except AttributeError:
            qu = query
        qu = qu.split('/')
        qu_wk = map(self._convert_wildcards, qu)
        package, resourcetype = self.env.registry.\
                                   objects_from_id(qu_wk[1], qu_wk[2])
        if package:
            qu[1] = str(package._id)
        if resourcetype:
            qu[2] = str(resourcetype._id)
        qu = '/'.join(qu)
        # end workaround
        if isinstance(query,dict):
            query['query'] = qu
            q = XPathQuery(**query)
        else:
            q = XPathQuery(qu, order_by, limit)
        return self.index_catalog.query(q)

