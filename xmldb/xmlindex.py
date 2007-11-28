# -*- coding: utf-8 -*-
#from seishub.core import implements
from zope.interface import implements
from zope.interface.exceptions import DoesNotImplement

from seishub.core import SeishubError
from seishub.xmldb.interfaces import IXmlIndex, IXmlResource

__all__=['XmlIndex']

class XmlIndexError(SeishubError):
    pass

class XmlIndex(object):
    implements(IXmlIndex)
    
    def __init__(self,value_path="",key_path="",xpath_expr=""):
        if not ((value_path and key_path) or xpath_expr):
            raise XmlIndexError("No key given")
        if xpath_expr:
            self.setXpath_expr(xpath_expr)
        else:
            self.setValue_path(value_path)
            self.setKey_path(key_path)
        self._value=None
        
    def setValue_path(self,path):
        self._value_path=path
        
    def setKey_path(self,path):
        self._key_path=path
        
    def setXpath_expr(self,expr):
        self._xpath_expr=expr
           
    def getValue_path(self):
        if hasattr(self,'_value_path'):
            return self._value_path
        else:
            return None
    
    def getKey_path(self):
        if hasattr(self,'_key_path'):
            return self._key_path
        else:
            return None
        
    def getXpath_expr(self):
        if hasattr(self,'_xpath_expr'):
            return self._xpath_expr
        else:
            return None
    
    def getValue(self):
        return self._value
    
    def _createXPath(self):
        return self.getKey_path() + '/' + self.getValue_path()
    
    def eval(self,xml_resource):
        if not IXmlResource.providedBy(xml_resource):
            raise DoesNotImplement(IXmlResource)
            return None
        
        xml_doc=xml_resource.getXml_doc()
        if not xml_doc:
            raise SeishubError('Xml resource does not contain data')
            return None
        
        #eval xpath expression:
        xpr=self.getXpath_expr()
        if not xpr:
            xpr=self._createXPath()
        nodes = xml_doc.evalXPath(xpr)
        if len(nodes) == 1:
            self._value=nodes[0].getStrContent()
        return self
    
    