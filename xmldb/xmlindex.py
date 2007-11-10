# -*- coding: utf-8 -*-
#from seishub.core import implements
from zope.interface import implements
from zope.interface.exceptions import DoesNotImplement

from seishub.core import SeishubError
from seishub.xmldb.interfaces import IXmlIndex, IXmlResource

__all__=['XmlIndex']

class XmlIndex(object):
    implements(IXmlIndex)
    
    def __init__(self,value_path="",key_path=""):
        self.setValue_path(value_path)
        self.setKey_path(key_path)
        
    def setValue_path(self,path):
        self.__value_path=path
        
    def setKey_path(self,path):
        self.__key_path=path
           
    def getValue_path(self):
        return self.__value_path
    
    def getKey_path(self):
        return self.__key_path
    
    def eval(self,xml_resource):
        if not IXmlResource.providedBy(xml_resource):
            raise DoesNotImplement(IXmlResource)
            return None
        
        xml_doc=xml_resource.getXml_doc()
        if not xml_doc:
            raise SeishubError('Xml resource does not contain data')
            return None
        
        #create xpath expression:
        xml_doc.evalXPath('/station/*')
        
        return self
        
        
        