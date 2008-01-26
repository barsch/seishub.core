# -*- coding: utf-8 -*-
from zope.interface import implements
from zope.interface.exceptions import DoesNotImplement

from seishub.core import SeisHubError
from seishub.xmldb.interfaces import IXmlIndex, IXmlResource

__all__=['XmlIndex']

TEXT_INDEX="text"

class XmlIndexError(SeisHubError):
    pass

class XmlIndex(object):
    implements(IXmlIndex)
    
    def __init__(self,value_path="",key_path="",xpath_expr="", type=TEXT_INDEX):
        # do not use 'xpath_expr' argument, not fully implemented till now!
        # use value_path and key_path instead
        if not ((value_path and key_path) or xpath_expr):
            raise XmlIndexError("No key given")
        if xpath_expr:
            self.setXpath_expr(xpath_expr)
        else:
            self.setValue_path(value_path)
            self.setKey_path(key_path)
        
        if isinstance(type,basestring):
            self._type=type
        else:
            raise TypeError("type: basestring expected")
            self._type=""
            
        self._values=list()
        
    # methods from IXmlIndex:
        
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
        
    def getType(self):
        return self._type
    
    def getValues(self):
        return self._values
    
    def _createXPath(self):
        return self.getValue_path() + '/' + self.getKey_path()
    
    def eval(self,xml_resource):
        if not IXmlResource.providedBy(xml_resource):
            raise DoesNotImplement(IXmlResource)
            return None
        
        xml_doc=xml_resource.getXml_doc()
        if not xml_doc:
            raise SeisHubError('Xml resource does not contain data')
            return None
        
        #eval xpath expression:
        xpr=self.getXpath_expr()
        if not xpr:
            xpr=self._createXPath()
        nodes = xml_doc.evalXPath(xpr)
        
        node_size=len(nodes)
        if node_size == 0:
            res=None
        else:
            idx_value=xml_resource.getUri()
            res=[{'key':node.getStrContent(),
                  'value':idx_value} for node in nodes]
            self._values.append(idx_value)
        
        return res
