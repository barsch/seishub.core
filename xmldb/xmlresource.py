# -*- coding: utf-8 -*-

from zope.interface import implements
from zope.interface.exceptions import DoesNotImplement

from seishub.util.xml import IXmlDoc, IXmlSchema
from seishub.util.text import to_unicode
from seishub.xmldb.interfaces import IXmlResource
from seishub.util.xml import XmlTreeDoc
from seishub.xmldb.resource import Resource
from seishub.xmldb.errors import XmlResourceError
from seishub.xmldb.util import Serializable

class XmlResource(Resource, Serializable):
    """auto-parsing xml resource, 
    given xml data gets validated and parsed on resource creation"""
    
    implements (IXmlResource)
    
    def __init__(self,uri=None,xml_data=None):
        self.__xml_doc = None
        Resource.__init__(self, uri, xml_data)
        Serializable.__init__(self)
        
    # overloaded method from Serializable
    def getFields(self):
        return {'_id':self._id,
                'uri':self.uri,
                'data':self.data,
                'resource_type':self.resource_type
                }
    
    # overloaded method setData from Resource
    # gets invoked by Resource's constructor
    def setData(self, xml_data):
        xml_data = str(xml_data)
        # parse and validate xml_data
        # decode raw data to utf-8 unicode string
        if not isinstance(xml_data, unicode) and xml_data:
            xml_data = unicode(xml_data,"utf-8")
            
        try:
            self.__xml_doc = self._validateXml_data(xml_data)
        except Exception, e:
            raise XmlResourceError(e)
        
        # find resource type from xml data
        self._resource_type = self.__xml_doc.getRootElementName()
        return Resource.setData(self,xml_data)
    
    def getData(self):
        # utf-8 encode data
        data = super(XmlResource,self).getData()
        if not data:
            return None
        return data.encode("utf-8")
    
    data = property(getData, setData, 'Raw xml data as a string')
    
    def getResource_type(self):
        if not hasattr(self,'_resource_type'):
            return None
        return self._resource_type
    
    resource_type = property(getResource_type, "Resource type")
    
    def getXml_doc(self):
        return self.__xml_doc
    
    def setXml_doc(self,xml_doc):
        if not IXmlDoc.providedBy(xml_doc):
            raise DoesNotImplement(IXmlDoc)
        else:
            self.__xml_doc = xml_doc
    
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

