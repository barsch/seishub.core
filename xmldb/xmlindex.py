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
    
    def __init__(self,value_path=None, key_path=None,
                 type=TEXT_INDEX):
        if not (value_path and key_path):
            raise XmlIndexError("No index definition given")
        
        self.setValueKeyPath(value_path,key_path)
        
        if isinstance(type,basestring):
            self._type=type
        else:
            self._type=TEXT_INDEX
            
        self._values=list()
        
    def _createXPath(self):
        if not self._value_path.startswith("/"):
            str="/"
        else:
            str=""
        return str + self.getValue_path() + '/' + self.getKey_path()
        
    # methods from IXmlIndex:
    
    def setValueKeyPath(self,value_path,key_path):
        self._value_path=value_path
        self._key_path=key_path
        self._xpath_expr=self._createXPath()
              
    def getValue_path(self):
        if hasattr(self,'_value_path'):
            return self._value_path
        else:
            return None
    
    def getKey_path(self):
        if hasattr(self,'_key_path'):
            return self._key_path
        
    def getXpath_expr(self):
        if hasattr(self,'_xpath_expr'):
            return self._xpath_expr
        
    def getType(self):
        return self._type
    
    def getValues(self):
        return self._values
    
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
