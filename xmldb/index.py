# -*- coding: utf-8 -*-
from zope.interface import implements
from zope.interface.exceptions import DoesNotImplement

from seishub.core import SeisHubError
from seishub.db.util import Serializable
from seishub.xmldb.interfaces import IXmlIndex, IVirtualIndex, IXmlResource
from seishub.xmldb.errors import XmlIndexError

__all__ = ['XmlIndex', 'VirtualIndex']

TEXT_INDEX = "text"

class IndexBase(Serializable):
    def __init__(self,value_path=None, key_path=None,
                 type=TEXT_INDEX):
        super(IndexBase, self).__init__()
        if not (value_path and key_path):
            raise XmlIndexError("No index definition given")
        self.setValueKeyPath(value_path,key_path)
        if isinstance(type,basestring):
            self.type = type
        else:
            self.type = TEXT_INDEX
        self._values=list()
    
    # overloaded method from Serializable
    def getFields(self):
        return {'_id':self._id,
                'key_path':self.key_path,
                'value_path':self.value_path,
                'type':self.type
                }
        
    def setValueKeyPath(self,value_path,key_path):
        self.value_path = value_path
        self.key_path = key_path
        self._xpath_expr = self._createXPath()
              
    def getValue_path(self):
        if hasattr(self,'_value_path'):
            return self._value_path
        else:
            return None
        
    def setValue_path(self, value_path):
        self._value_path = value_path
    
    value_path = property(getValue_path, setValue_path, "Value path")
    
    def getKey_path(self):
        if hasattr(self,'_key_path'):
            return self._key_path
    
    def setKey_path(self, key_path):
        self._key_path = key_path
        
    key_path = property(getKey_path, setKey_path, "Key path")
        
    def getType(self):
        return self._type
    
    def setType(self, type):
        self._type = type
    
    type = property(getType, setType, "Data type")
    
    def getValues(self):
        return self._values

class XmlIndex(IndexBase):
    implements(IXmlIndex)
          
    def __str__(self):
        return self.getXpath_expr()
        
    def _createXPath(self):
        if not self._value_path.startswith("/"):
            str="/"
        else:
            str=""
        return str + self.getValue_path() + '/' + self.getKey_path()
    
    def getXpath_expr(self):
        if hasattr(self,'_xpath_expr'):
            return self._xpath_expr
    
    # methods from IXmlIndex:
    
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

class VirtualIndex(IndexBase):
    implements(IVirtualIndex)
    
    # methods from IVirtualIndex
    def setValue(self, data):
        """@see: L{seishub.xmldb.interfaces.IVirtualIndex}"""
        # TODO: validate type of data
        self._values.append(data)