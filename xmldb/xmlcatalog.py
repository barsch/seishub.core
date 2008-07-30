# -*- coding: utf-8 -*-

from zope.interface import implements

from seishub.xmldb.interfaces import IXmlCatalog
from seishub.xmldb.xmldbms import XmlDbManager
from seishub.xmldb.xmlindexcatalog import XmlIndexCatalog
from seishub.xmldb.resource import XmlResource
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
        
    # methods from IXmlCatalog
    
    # xmldbms methods
    def addResource(self, package_id, resourcetype_id, xml_data):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        package, resourcetype = self.env.registry.\
                                   objects_from_id(package_id, resourcetype_id)
        res = XmlResource(package, resourcetype, xml_data)
        self.xmldb.addResource(res)
        return res
        
    def deleteResource(self, package_id, resourcetype_id, id):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        package, resourcetype = self.env.registry.\
                                   objects_from_id(package_id, resourcetype_id)
        return self.xmldb.deleteResource(package, resourcetype, id)
    
    def getResource(self, package_id, resourcetype_id, id, revision = None):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        package, resourcetype = self.env.registry.\
                                   objects_from_id(package_id, resourcetype_id)
        return self.xmldb.getResource(package, resourcetype, id, revision)
        
    def getResourceList(self, package_id = None, resourcetype_id = None):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        package, resourcetype = self.env.registry.\
                                   objects_from_id(package_id, resourcetype_id)
        return self.xmldb.getResourceList(package, resourcetype)
        
    def resourceExists(self, package_id, resourcetype_id, id):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        package, resourcetype = self.env.registry.\
                                   objects_from_id(package_id, resourcetype_id)
        return self.xmldb.resourceExists(package, resourcetype, id)
    
    def getUriList(self, package_id = None, resourcetype_id = None):
        # XXX: to be removed
        return self.xmldb.getUriList(package_id, resourcetype_id)
    
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
        return self.index_catalog.registerIndex(index)
    
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
                 xpath = None):
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
            self.index_catalog.indexResource(res.resource.resource_id, 
                                             value_path, key_path)
        
        return True
        
    def query(self, query, order_by = None, limit = None):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        # TODO: workaround until indexes support package/resourcetype natively
        try:
            qu = query.get('query')
        except AttributeError:
            qu = query
        qu = qu.split('/')
        package, resourcetype = self.env.registry.\
                                   objects_from_id(qu[1], qu[2])
        qu[1] = str(package._id)
        qu[2] = str(resourcetype._id)
        qu = '/'.join(qu)
        # end workaround
        if isinstance(query,dict):
            query['query'] = qu
            q = XPathQuery(**query)
        else:
            q = XPathQuery(qu, order_by, limit)
        return self.index_catalog.query(q)

