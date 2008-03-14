# -*- coding: utf-8 -*-

from zope.interface import implements
from zope.interface.exceptions import DoesNotImplement

from seishub.core import SeisHubError
from seishub.util.libxmlwrapper import IXmlDoc, IXmlSchema
from seishub.xmldb.interfaces import IXmlResource
from seishub.util.libxmlwrapper import XmlTreeDoc
from seishub.xmldb.resource import Resource
from seishub.xmldb.errors import XmlResourceError

class XmlResource(Resource):
    """auto-parsing xml resource, 
    given xml data gets validated and parsed on resource creation"""
    implements (IXmlResource)
    def __init__(self,uri=None,xml_data=None):
        """overloaded __init__ to encode utf8 if needed"""
        self.__xml_doc = None
        if not isinstance(xml_data, unicode) and xml_data:
            xml_data = unicode(xml_data,"utf-8")
        Resource.__init__(self, uri, xml_data)
    
    # overloaded method setData from Resource
    # this gets invoked by baseclass's constructor
    def setData(self,xml_data):
        """validate and set xml_data"""
        try:
            self.__xml_doc = self._validateXml_data(xml_data)
        except Exception, e:
            raise XmlResourceError(e)
        
        self._resource_type = self.__xml_doc.getRootElementName()
        return Resource.setData(self,xml_data)
    
    def getXml_doc(self):
        return self.__xml_doc
    
    def setXml_doc(self,xml_doc):
        if not IXmlDoc.providedBy(xml_doc):
            raise DoesNotImplement(IXmlDoc)
        else:
            self.__xml_doc = xml_doc
            
    def getResource_type(self):
        return self._resource_type
    
    def _validateXml_data(self,value):
        return self._parseXml_data(value)
    
    def _parseXml_data(self,xml_data):
        #import pdb; pdb.set_trace()
        # encode before handing it to parser:
        xml_data = xml_data.encode("utf-8")
        return XmlTreeDoc(xml_data=xml_data, blocking=True)
    
class XmlSchemaResource(XmlResource):
    """XmlResource providing validation against given XML Schema"""
    
    def __init__(self, uri=None, xml_data=None, xml_schema=None):
        super(XmlSchemaResource,self).__init__(uri, xml_data)
        if not IXmlSchema.providedBy(xml_schema):
            raise DoesNotImplement(IXmlSchema)
        self._schema = xml_schema
        
    def _validate(self):
        self._schema.validate(self.__xml_doc)
        
    