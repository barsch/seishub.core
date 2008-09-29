# -*- coding: utf-8 -*-

import sha
from zope.interface import implements

from seishub.db.util import Serializable, Relation, db_property
from seishub.util.xmlwrapper import IXmlDoc, IXmlStylesheet, IXmlSchema, \
                                    XmlTreeDoc
from seishub.packages.package import PackageWrapper, ResourceTypeWrapper
from seishub.xmldb.defaults import resource_tab, data_tab
from seishub.xmldb.errors import XmlResourceError
from seishub.xmldb.interfaces import IResource,\
                                     IXmlDocument
from seishub.xmldb.package import PackageSpecific
   

class XmlDocument(Serializable):
    """auto-parsing xml resource, 
    given xml data gets validated and parsed on resource creation"""
    
    implements (IXmlDocument)
    
    db_table = data_tab
    db_mapping = {'data':'data',
                  '_id':'id',
                  'uid':'uid',
                  'datetime':'datetime',
                  'size':'size',
                  'hash':'hash'
                  }
    
    def __init__(self, data = None, id = None, uid = None):
        self._xml_doc = None
        self.data = data
        self.uid = uid
        self.datetime = None
        Serializable.__init__(self)
    
    def setData(self, data):
        # parse and validate xml_data
        # decode raw data to utf-8 unicode string
        if not data or data == "":
            self._data = None
            return
        if not isinstance(data, basestring):
            data = str(data)
        if not isinstance(data, unicode):
            data = unicode(data, "utf-8")
        self._data = data
        try:
            self._xml_doc = self._validateXml_data(self._data)
        except Exception, e:
            raise XmlResourceError(e)
    
    def getData(self):
        data = self._data
        if not data:
            return None
        return data.encode("utf-8")
    
    data = property(getData, setData, 'Raw xml data as a string')
    
    
    def getUID(self):
        return self._uid
    
    def setUID(self, value):
        if value and not isinstance(value, int):
            raise TypeError('User id has to be integer.')
        self._uid = value
    
    uid = property(getUID, setUID, 'User id of document creator')
    
    def getDatetime(self):
        return self._datetime
    
    def setDatetime(self, value):
        self._datetime = value
    
    datetime = property(getDatetime, setDatetime, 
                        'Last modification date')
    
    def getSize(self):
        return len(self.data)
    
    def setSize(self, value):
        pass
    
    size = property(getSize, setSize, 'Size of xml document (read-only)')
    
    
    def getHash(self):
        return sha.sha(self.data).hexdigest()
    
    def setHash(self, value):
        pass
    
    hash = property(getHash, setHash, 'Document hash (read-only)')
    
    def getXml_doc(self):
        return self._xml_doc
    
    def setXml_doc(self,xml_doc):
        if not IXmlDoc.providedBy(xml_doc):
            raise TypeError("%s is not an IXmlDoc" % str(xml_doc))
        else:
            self._xml_doc = xml_doc
    
    xml_doc = property(getXml_doc, setXml_doc, 'Parsed xml document (IXmlDoc)')
    
    def _validateXml_data(self,value):
        return self._parseXml_data(value)
    
    def _parseXml_data(self,xml_data):
        #import pdb; pdb.set_trace()
        # encode before handing it to parser:
        xml_data = xml_data.encode("utf-8")
        return XmlTreeDoc(xml_data=xml_data, blocking=True)


#class XmlStylesheetDocument(XmlDocument):
#    def getXml_doc(self):
#        return self._xml_doc
#    
#    def setXml_doc(self,xml_doc):
#        if not IXmlStylesheet.providedBy(xml_doc):
#            raise TypeError("%s is not an IXmlStylesheet" % str(xml_doc))
#        else:
#            self._xml_doc = xml_doc
#    
#    xml_doc = property(getXml_doc, setXml_doc, 
#                       'Parsed xml document (IXmlStylesheet)')
#    
#    def transform(self, document):
#        return self.xml_doc.transform(document.xml_doc)
#    
#
#class XmlSchemaDocument(XmlDocument):
#    def getXml_doc(self):
#        return self._xml_doc
#    
#    def setXml_doc(self,xml_doc):
#        if not IXmlSchema.providedBy(xml_doc):
#            raise TypeError("%s is not an IXmlSchema" % str(xml_doc))
#        else:
#            self._xml_doc = xml_doc
#    
#    xml_doc = property(getXml_doc, setXml_doc, 
#                       'Parsed xml document (IXmlSchema)')
#    
#    def validate(self, document):
#        return self.xml_doc.validate(document.xml_doc)


class Resource(Serializable, PackageSpecific):
    
    implements(IResource)
    
    db_table = resource_tab
    db_mapping = {'id':'id',  # external id
                  'revision':'revision',
                  'document':Relation(XmlDocument, 'resource_id'),
                  'package':Relation(PackageWrapper,'package_id'),
                  'resourcetype':Relation(ResourceTypeWrapper,
                                          'resourcetype_id')
                  }
    
    def __init__(self, package = PackageWrapper(), 
                 resourcetype = ResourceTypeWrapper(), id = None, 
                 revision = None, document = None):
        self.id = id
        self.revision = revision
        self.document = document
        self.package = package
        self.resourcetype = resourcetype
        
    def __str__(self):
        return '/' + self.package.package_id + '/' +\
               self.resourcetype.resourcetype_id + '/' + str(self.id)
    
    # auto update id when _Serializable__id is changed:
    def _setId(self, id):
        Serializable._setId(self, id)
        self.id = id
        
    def getResourceType(self):
        return self._resourcetype
     
    def setResourceType(self, data):
        self._resourcetype = data
        
    resourcetype = db_property(getResourceType, setResourceType, 
                               "Resource type", attr = '_resourcetype')
    
    def getPackage(self):
        return self._package
    
    def setPackage(self, data):
        self._package = data
        
    package = db_property(getPackage, setPackage, "Package", attr = '_package')
    
    def getDocument(self):
        return self._document
    
    def setDocument(self, data):
        if data and not IXmlDocument.providedBy(data):
            raise TypeError("%s is not an IXmlDocument." % str(data))
        self._document = data
    
    document = db_property(getDocument, setDocument, "xml document", 
                            attr = '_document')
    
    def getRevision(self):
        return self._revision
    
    def setRevision(self, data):
        self._revision = 1
        if hasattr(self, 'resourcetype') and self.resourcetype.version_control:
            self._revision = data
         
    revision = property(getRevision, setRevision, "revision")
    
    def getId(self):
        return self._id
    
    def setId(self, data):
        self._id = data
        
    id = property(getId, setId, "Integer identification number (external id)")
