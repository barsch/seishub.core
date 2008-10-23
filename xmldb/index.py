# -*- coding: utf-8 -*-
from zope.interface import implements

from seishub.exceptions import SeisHubError
from seishub.db.util import Serializable
from seishub.xmldb.defaults import index_def_tab
from seishub.xmldb.interfaces import IXmlIndex, IVirtualIndex, IXmlDocument

__all__ = ['XmlIndex', 'VirtualIndex']

TEXT_INDEX = "text"

class IndexBase(Serializable):
    db_table = index_def_tab
    db_mapping = {'key_path':'key_path',
                  'value_path':'value_path',
                  'type':'data_type'}
    
    def __init__(self,value_path=None, key_path=None, type=TEXT_INDEX):
        super(IndexBase, self).__init__()
        if not (value_path and key_path):
            raise TypeError("No index definition given.")
        self.value_path = value_path
        self.key_path = key_path
        if isinstance(type,basestring):
            self.type = type
        else:
            self.type = TEXT_INDEX
        self._values=list()
        
    def __str__(self):
        return '/' + self.value_path + '/' + self.key_path
              
    def getValue_path(self):
        if hasattr(self,'_value_path'):
            return self._value_path
        else:
            return None
        
    def setValue_path(self, value_path):
        if value_path.startswith('/'):
            value_path = value_path[1:]
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
        return '/' + self.value_path + '/' + self.key_path
    
    def _getRootElementName(self):
        elements = self.value_path.split('/')
        # last element is root element
        return elements[len(elements)-1]

    # methods from IXmlIndex:
    
    def eval(self, xml_resource):
        if not IXmlDocument.providedBy(xml_resource):
            raise TypeError("%s is not an IXmlDocument." % str(xml_resource))
        
        xml_doc = xml_resource.getXml_doc()
        if not xml_doc:
            raise SeisHubError('Invalid XML document')
        
        # build xpath expression to evaluate on xml document
        xpr = '/' + self._getRootElementName() + '/' + self.getKey_path()
        nodes = xml_doc.evalXPath(xpr)
        
        node_size = len(nodes)
        if node_size == 0:
            return None
        
        idx_value = xml_resource._id
        res = [{'key':node.getStrContent(),
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