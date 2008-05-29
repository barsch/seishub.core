# -*- coding: utf-8 -*-

from zope.interface import implements

from seishub.xmldb.interfaces import IXmlCatalog
from seishub.xmldb.xmlindexcatalog import XmlIndexCatalog, QueryAliases
from seishub.xmldb.xmldbms import XmlDbManager
from seishub.xmldb.xmlresource import XmlResource
from seishub.xmldb.index import XmlIndex
#from seishub.xmldb.metaresources import SchemaRegistry, StylesheetRegistry
from seishub.xmldb.xpath import IndexDefiningXpathExpression, XPathQuery

class XmlCatalog(XmlDbManager):
    implements(IXmlCatalog)
    
    def __init__(self, db):
        XmlDbManager.__init__(self,db)
        self.index_catalog = XmlIndexCatalog(db, self)
        self.aliases = QueryAliases(db)
        #self.schema_registry = SchemaRegistry(db)
        #self.stylesheet_registry = StylesheetRegistry(db)
    
    # methods from IXmlCatalog:
    def newXmlResource(self,package_id,resourcetype_id,xml_data):
        """
        @see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        return XmlResource(package_id,resourcetype_id,xml_data)
    
    def newXmlIndex(self,xpath_expr,type="text"):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        exp_obj = IndexDefiningXpathExpression(xpath_expr)
        if type=="text":
            return XmlIndex(value_path = exp_obj.value_path,
                            key_path = exp_obj.key_path)
        else:
            return None
    
    def registerIndex(self,xml_index):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        return self.index_catalog.registerIndex(xml_index)
    
    def removeIndex(self,xpath_expr):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        exp_obj = IndexDefiningXpathExpression(xpath_expr)
        return self.index_catalog.removeIndex(value_path = exp_obj.value_path,
                                              key_path = exp_obj.key_path)
        
    def getIndex(self,xpath_expr):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        return self.index_catalog.getIndex(expr = xpath_expr)
        
    def flushIndex(self,xpath_expr):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        exp_obj=IndexDefiningXpathExpression(xpath_expr)
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
        
    def reindex(self,xpath_expr):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        # get index
        index = self.index_catalog.getIndex(expr = xpath_expr)
        
        # flush index
        self.flushIndex(xpath_expr)
        
        # find all resources the index applies to by resource type
        value_path = index.value_path
        key_path = index.key_path
        if value_path.startswith('/'):
            value_path = value_path[1:]
        package, type, rootnode  = value_path.split('/')
        reslist = self.getResourceList(package_id = package, 
                                       resourcetype_id = type)
        # reindex
        for res in reslist:
            self.index_catalog.indexResource(res[0], value_path, key_path)
        
        return True
        
    def query(self, query, order_by = None, limit = None):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        if isinstance(query,dict):
            q = XPathQuery(**query)
        else:
            q = XPathQuery(query, order_by, limit)
        return self.index_catalog.query(q)

