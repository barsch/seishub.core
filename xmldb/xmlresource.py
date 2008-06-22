# -*- coding: utf-8 -*-

from zope.interface import implements
from zope.interface.exceptions import DoesNotImplement

from seishub.util.xml import IXmlDoc
from seishub.xmldb.interfaces import IXmlResource
from seishub.util.xml import XmlTreeDoc
from seishub.xmldb.resource import Resource, ResourceInformation
from seishub.xmldb.errors import XmlResourceError
from seishub.db.util import Serializable

class XmlResource(Resource, Serializable):
    """auto-parsing xml resource, 
    given xml data gets validated and parsed on resource creation"""
    
    implements (IXmlResource)
    
    def __init__(self, package_id = None, resourcetype_id = None, data = None,
                 id = None, version_control = False):
        self.__xml_doc = None
        info = ResourceInformation(package_id, resourcetype_id, id,
                                   version_control = version_control)
        Resource.__init__(self, None, data, info)
        Serializable.__init__(self)
        
    # auto update resource id when Serializable id is changed:
    def _setId(self, id):
        Serializable._setId(self, id)
        self.resource_id = id
    
    # pass ResourceInformation.id to XmlResource.id for easy access (read-only)
    def getId(self):
        return self.info.id
    
    id = property(getId, "Integer identification number (external id)")
    
    # overloaded method setData from Resource
    # gets invoked by Resource's constructor
    def setData(self, xml_data):
        # parse and validate xml_data
        # decode raw data to utf-8 unicode string
        if xml_data is None or len(xml_data) == 0:
            return Resource.setData(self, xml_data)
            #raise XmlResourceError("No xml data given")
        xml_data = str(xml_data)
        if not isinstance(xml_data, unicode) and xml_data:
            xml_data = unicode(xml_data, "utf-8")
            
        try:
            self.__xml_doc = self._validateXml_data(xml_data)
        except Exception, e:
            raise XmlResourceError(e)
        
        return Resource.setData(self, xml_data)
    
    def getData(self):
        data = super(XmlResource,self).getData()
        if not data:
            return None
        # XXX: use encoded byte strings or unicode strings internally?
        return data.encode("utf-8")
        #return data
    
    data = property(getData, setData, 'Raw xml data as a string')
    
    
    def getXml_doc(self):
        return self.__xml_doc
    
    def setXml_doc(self,xml_doc):
        if not IXmlDoc.providedBy(xml_doc):
            raise DoesNotImplement(IXmlDoc)
        else:
            self.__xml_doc = xml_doc

            
#    def getUri(self):
##         XXX: remove this method or handle non existing self._id properly
#        return '/' + self.info.package_id + '/' + self.info.resourcetype_id + '/' +\
#               str(self._id)
    
    def _validateXml_data(self,value):
        return self._parseXml_data(value)
    
    def _parseXml_data(self,xml_data):
        #import pdb; pdb.set_trace()
        # encode before handing it to parser:
        xml_data = xml_data.encode("utf-8")
        return XmlTreeDoc(xml_data=xml_data, blocking=True)

#class XmlSchemaResource(XmlResource):
#    """XmlResource providing validation against given XML Schema"""
#    
#    def __init__(self, uri=None, xml_data=None, xml_schema=None):
#        super(XmlSchemaResource,self).__init__(uri, xml_data)
#        if not IXmlSchema.providedBy(xml_schema):
#            raise DoesNotImplement(IXmlSchema)
#        self._schema = xml_schema
#        
#    def _validate(self):
#        self._schema.validate(self.__xml_doc)

