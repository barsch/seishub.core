# -*- coding: utf-8 -*-

from zope.interface import implements

from seishub.xmldb.interfaces import IXmlResource
from seishub.libxmlwrapper import XmlTreeDoc,InvalidXmlDataError
from seishub.resource import Resource

class XmlResource(Resource):
    implements (IXmlResource)
    def __init__(self,uri=None,xml_data=None):
        Resource.__init__(self,uri,xml_data)
    
    def setData(self,xml_data):
        """validate and set xml_data"""
        if self._validateXml_data(xml_data):
            Resource.setData(self,xml_data)
        else:
            raise InvalidXmlDataError
        
    def getXml_doc(self):
        return self.xml_doc
    
    def setXml_doc(self,xml_doc):
        self.xml_doc=xml_doc
    
    def _validateXml_data(self,value):
        # TODO: validation
        # should xml validation be done here?
        # maybe not, as this gets invoked every time we create a xml resource,
        # even when restoring a resource from db for example (which has already 
        # been through the validation process on db update or insert); on the 
        # other hand, it shouldn't be possible to create a XmlResource containing
        # something else than well-formed xml...
        return self._parseXml_data(value)
    
    def _parseXml_data(self,xml_data):
        self.xml_doc=XmlTreeDoc(xml_data=xml_data,blocking=True)
        return True