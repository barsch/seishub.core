# -*- coding: utf-8 -*-

from zope.interface import implements

from seishub.xmldb.interfaces import IXmlCatalog
from seishub.xmldb.xmlindexcatalog import XmlIndexCatalog, QueryAliases
from seishub.xmldb.xmldbms import XmlDbManager
from seishub.xmldb.xmlresource import XmlResource
from seishub.xmldb.xmlindex import XmlIndex
from seishub.xmldb.metaresources import SchemaRegistry, StylesheetRegistry
from seishub.xmldb.xpath import IndexDefiningXpathExpression, XPathQuery

class XmlCatalog(XmlDbManager):
    implements(IXmlCatalog)
    
    def __init__(self, db):
        XmlDbManager.__init__(self,db)
        self.index_catalog = XmlIndexCatalog(db, self)
        self.aliases = QueryAliases(db)
        self.schema_registry = SchemaRegistry(db)
        self.stylesheet_registry = StylesheetRegistry(db)
    
    # methods from IXmlCatalog:
    def newXmlResource(self,uri,xml_data):
        """
        @see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        return XmlResource(uri,xml_data)
    
    def newXmlIndex(self,xpath_expr,type="text"):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        exp_obj=IndexDefiningXpathExpression(xpath_expr)
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
        exp_obj=IndexDefiningXpathExpression(xpath_expr)
        return self.index_catalog.removeIndex(value_path = exp_obj.value_path,
                                              key_path = exp_obj.key_path)
        
    def getIndex(self,xpath_expr):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        exp_obj=IndexDefiningXpathExpression(xpath_expr)
        return self.index_catalog.getIndex(value_path = exp_obj.value_path,
                                           key_path = exp_obj.key_path)
        
    def flushIndex(self,xpath_expr):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        exp_obj=IndexDefiningXpathExpression(xpath_expr)
        return self.index_catalog.flushIndex(value_path = exp_obj.value_path,
                                           key_path = exp_obj.key_path)
        
    def listIndexes(self,res_type = None, data_type = None):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        return self.index_catalog.getIndexes(value_path = res_type,
                                             data_type = data_type)
        
    def reindex(self,xpath_expr):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        exp_obj = IndexDefiningXpathExpression(xpath_expr)
        if not exp_obj:
            return
        key_path = exp_obj.key_path
        value_path = exp_obj.value_path
        
        # get index from db
        self.index_catalog.getIndex(key_path, value_path)
        
        # flush index
        self.flushIndex(xpath_expr)
        
        # find all resources the index applies to by resource type
        if value_path.startswith('/'):
            type = value_path[1:]
        else:
            type = value_path
        uris = self.getUriList(type)
        
        # reindex
        for uri in uris:
            self.index_catalog.indexResource(uri, value_path, key_path)
        
        return True
    
    def registerAlias(self, uri, query, order_by = None, limit = None):
        self.aliases[uri] = {'query':query,
                             'order_by':order_by,
                             'limit':limit}
        
    def query(self, query, order_by = None, limit = None):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        if isinstance(query,dict):
            q = XPathQuery(**query)
        else:
            q = XPathQuery(query, order_by, limit)
        return self.index_catalog.query(q)
    
    def registerSchema(self, xml_resource, package_id):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        self.addResource(xml_resource)
        return self.schema_registry.registerSchema(xml_resource.getUri(), package_id)
        
    def unregisterSchema(self, uri):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        self.schema_registry.unregisterSchema(uri)
        return self.deleteResource(uri)
        
    def getSchemata(self, package_id = None):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        res = self.schema_registry.getSchemata(package_id)
        return [uri[0] for uri in res]
        
    def registerStylesheet(self, xml_resource, package_id, output_format):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        self.addResource(xml_resource)
        return self.stylesheet_registry.registerStylesheet(xml_resource.uri, 
                                                    package_id, 
                                                    output_format)
        
    def unregisterStylesheet(self, uri):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        self.stylesheet_registry.unregisterStylesheet(uri)
        return self.deleteResource(uri)
    
    def getStylesheets(self, package_id = None, output_format = None):
        """@see: L{seishub.xmldb.interfaces.IXmlCatalog}"""
        res = self.stylesheet_registry.getStylesheets(package_id, output_format)
        return [uri[0] for uri in res]
