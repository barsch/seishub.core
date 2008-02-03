# -*- coding: utf-8 -*-

from zope.interface import implements

from twisted.internet.defer import DeferredList

from seishub.xmldb.interfaces import IXmlCatalog
from seishub.xmldb.xmlindexcatalog import XmlIndexCatalog
from seishub.xmldb.xmldbms import XmlDbManager
from seishub.xmldb.xmlresource import XmlResource
from seishub.xmldb.xmlindex import XmlIndex
from seishub.xmldb.xpath import RestrictedXpathExpression


class XmlCatalog(XmlDbManager):
    implements(IXmlCatalog)
    
    def __init__(self, db):
        XmlDbManager.__init__(self,db)
        self.index_catalog=XmlIndexCatalog(db)
    
    # methods from IXmlCatalog:
    def newXmlResource(self,uri,xml_data):
        return XmlResource(uri,xml_data)
    
    def newXmlIndex(self,xpath_expr,type="text"):
        exp_obj=RestrictedXpathExpression(xpath_expr)
        if type=="text":
            return XmlIndex(value_path = exp_obj.node_test,
                            key_path = exp_obj.predicates)
        else:
            return None
    
    def registerIndex(self,xml_index):
        return self.index_catalog.registerIndex(xml_index)
    
    def removeIndex(self,xpath_expr):
        exp_obj=RestrictedXpathExpression(xpath_expr)
        return self.index_catalog.removeIndex(value_path = exp_obj.node_test,
                                              key_path = exp_obj.predicates)
        
    def getIndex(self,xpath_expr):
        exp_obj=RestrictedXpathExpression(xpath_expr)
        return self.index_catalog.getIndex(value_path = exp_obj.node_test,
                                           key_path = exp_obj.predicates)
        
    def flushIndex(self,xpath_expr):
        exp_obj=RestrictedXpathExpression(xpath_expr)
        return self.index_catalog.flushIndex(value_path = exp_obj.node_test,
                                           key_path = exp_obj.predicates)
        
    def listIndexes(self,res_type = None, data_type = None):
        return self.index_catalog.getIndexes(res_type = res_type,
                                             data_type = data_type)
        
    def reindex(self,xpath_expr):
        exp_obj=RestrictedXpathExpression(xpath_expr)
        if not exp_obj:
            return
        key_path=exp_obj.predicates
        value_path=exp_obj.node_test
        
        # get index from db
        d = self.index_catalog.getIndex(key_path, value_path)
        
        # flush index
        d.addCallback(lambda f: self.flushIndex(xpath_expr))
        
        # find all resources our index applies to by resource type
        if value_path.startswith('/'):
            type=value_path[1:]
        else:
            type=value_path
            
        d.addCallback(lambda f: self.getUriList(type))
        
        # get and reindex every resource:
        def _indexRes(res):
            return self.index_catalog.indexResource(res, 
                                                    key_path=key_path, 
                                                    value_path=value_path)
        
        def _reindexResources(uri_list):
            d_list=list()
            for uri in uri_list:
                d=self.getResource(uri)
                d.addCallback(_indexRes)
                d_list.append(d)
            return DeferredList(d_list)
                
        d.addCallback(_reindexResources)
        
        return d