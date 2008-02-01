# -*- coding: utf-8 -*-

from zope.interface import implements
from zope.interface.exceptions import DoesNotImplement

from seishub.core import SeisHubError
from seishub.interfaces import IXmlDoc
from seishub.xmldb.interfaces import IXmlResource
from seishub.util.libxmlwrapper import XmlTreeDoc
from seishub.resource import Resource

class XmlResourceError(SeisHubError):
    pass

class XmlResource(Resource):
    """auto-parsing xml resource, 
    given xml data gets validated and parsed on resource creation"""
    implements (IXmlResource)
    def __init__(self,uri=None,xml_data=None):
        self.__xml_doc=None    
        #call parent constructor last, because it calls: self.setData()
        Resource.__init__(self,uri,xml_data)
    
    # overloaded method setData from Resource
    # this gets invoked by baseclass's constructor
    def setData(self,xml_data):
        """validate and set xml_data"""
        try:
            self.__xml_doc=self._validateXml_data(xml_data)
        except:
            raise XmlResourceError("Invalid xml data.")
            return False
        
        self._resource_type=self.__xml_doc.getRootElementName()
        return Resource.setData(self,xml_data)
    

    def getXml_doc(self):
        return self.__xml_doc
    
    def setXml_doc(self,xml_doc):
        if not IXmlDoc.providedBy(xml_doc):
            raise DoesNotImplement(IXmlDoc)
        else:
            self.__xml_doc=xml_doc
            
    def getResource_type(self):
        return self._resource_type
    
    def _validateXml_data(self,value):
        return self._parseXml_data(value)
    
    def _parseXml_data(self,xml_data):
        return XmlTreeDoc(xml_data=xml_data,blocking=True)