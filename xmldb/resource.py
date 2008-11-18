# -*- coding: utf-8 -*-

from zope.interface import implements

from seishub.exceptions import InvalidObjectError, InvalidParameterError
from seishub.db.util import Serializable, Relation, db_property, LazyAttribute
from seishub.util.xmlwrapper import IXmlDoc, XmlTreeDoc, InvalidXmlDataError
from seishub.util.text import validate_id
from seishub.util.xml import toUnicode, parseXMLDeclaration, addXMLDeclaration 
from seishub.util.text import hash
from seishub.packages.package import PackageWrapper, ResourceTypeWrapper
from seishub.xmldb.defaults import resource_tab, document_tab, document_meta_tab
from seishub.xmldb.interfaces import IResource, IXmlDocument, IDocumentMeta


XML_DECLARATION_LENGTH = len(addXMLDeclaration(""))


class DocumentMeta(Serializable):
    """contains document specific metadata;
    such as: size, datetime, hash, user_id
    """
    
    implements (IDocumentMeta)
    
    db_table = document_meta_tab
    
    db_mapping = {'_id':'id',
                  'uid':'uid',
                  'datetime':'datetime',
                  'size':'size',
                  'hash':'hash'
                  }
    
    def __init__(self, uid = None, datetime = None, size = None, hash = None):
        self.uid = uid
        self.datetime = datetime
        self.size = size
        self.hash = hash
    
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
        return self._size
    
    def setSize(self, value):
        self._size = value
    
    size = property(getSize, setSize, 'Size of xml document (read-only)')
    
    def getHash(self):
        return self._hash
        #return sha.sha(self.data).hexdigest()
    
    def setHash(self, value):
        self._hash = value
    
    hash = property(getHash, setHash, 'Document hash (read-only)')


class XmlDocument(Serializable):
    """auto-parsing xml resource, 
    given xml data gets validated and parsed on resource creation"""
    
    implements (IXmlDocument)
    
    db_table = document_tab
    db_mapping = {'_id':'id',
                  'revision':'revision',
                  'data':LazyAttribute('data'),
                  'meta':Relation(DocumentMeta, 'id', cascading_delete = True,
                                  lazy = False)
                  }
    
    def __init__(self, data = None, revision = None, uid = None):
        self._xml_doc = None
        self.meta = DocumentMeta(uid = uid)
        self.data = data
        # self.datetime = None
        Serializable.__init__(self)
    
    def setData(self, data):
        """set data, convert to unicode and remove XML declaration"""
        if not data or data == "":
            self._data = None
            return
        if not isinstance(data, unicode):
            raise TypeError("Data has to be unicode!")
        # encode "utf-8" to determine hash and size
        raw_data = data.encode("utf-8")
        self._data = data
        self.meta._size = len(raw_data) + XML_DECLARATION_LENGTH
        self.meta._hash = hash(raw_data)
    
    def getData(self):
        """Returns data as unicode object."""
        data = self._data
        assert not data or isinstance(data, unicode)
        return data
    
    data = db_property(getData, setData, 'Raw xml data as a string', 
                       attr = '_data')
    
    def getXml_doc(self):
        if not self._xml_doc:
            self._xml_doc = self._validateXml_data(self.data)
        return self._xml_doc
    
    def setXml_doc(self,xml_doc):
        if not IXmlDoc.providedBy(xml_doc):
            raise TypeError("%s is not an IXmlDoc" % str(xml_doc))
        self._xml_doc = xml_doc
    
    xml_doc = property(getXml_doc, setXml_doc, 'Parsed xml document (IXmlDoc)')
    
    def getMeta(self):
        return self._meta
    
    def setMeta(self, meta):
        if meta and not IDocumentMeta.providedBy(meta):
            raise TypeError("%s is not an IDocumentMeta" % str(meta))
        self._meta = meta
    
    meta = db_property(getMeta, setMeta, "Document metadata", attr = '_meta')
    
    def getRevision(self):
        return self._revision
    
    def setRevision(self, revision):
        self._revision = revision
    
    revision = property(getRevision, setRevision, "Document revision")
    
    def _validateXml_data(self,value):
        return self._parseXml_data(value)
    
    def _parseXml_data(self,xml_data):
        # encode before handing it to parser:
        # xml_data = xml_data.encode("utf-8")
        try:
            return XmlTreeDoc(xml_data=xml_data, blocking=True)
        except InvalidXmlDataError, e:
            raise InvalidObjectError("Invalid XML document.", e)


class Resource(Serializable):
    
    implements(IResource)
    
    db_table = resource_tab
    db_mapping = {'_id':'id',  # external id
                  'resourcetype':Relation(ResourceTypeWrapper, 
                                          'resourcetype_id'),
                  'name':'name',
                  'document':Relation(XmlDocument, 'resource_id', 
                                      lazy = False, relation_type = 'to-many',
                                      cascading_delete = True),
                  }
    
    def __init__(self, resourcetype = ResourceTypeWrapper(), id = None, 
                 document = None, name = None):
        self.document = document
        self._id = id
        self.resourcetype = resourcetype
        self.name = name
        
    def __str__(self):
        return "/%s/xml/%s/%s" % (self.package.package_id, 
                                  self.resourcetype.resourcetype_id, 
                                  str(self.name))

    def getId(self):
        return self._getId()
    
    def setId(self, id):
        return self._setId(id)
        
    id = property(getId, setId, "Unique resource id (integer)")
        
    def getResourceType(self):
        return self._resourcetype
     
    def setResourceType(self, data):
        self._resourcetype = data
        
    resourcetype = db_property(getResourceType, setResourceType, 
                               "Resource type", attr = '_resourcetype')
    
    def getPackage(self):
        return self.resourcetype.package
    
    def setPackage(self, data):
        pass
        
    package = property(getPackage, setPackage, "Package")
    
    def getDocument(self):
        # return document as a list only if multiple revisions are present
        if len(self._document) == 1:
            return self._document[0]
        else:
            return self._document
    
    def setDocument(self, data):
        if not isinstance(data, list):
            data = [data]
        self._document = data
    
    document = db_property(getDocument, setDocument, "xml document", 
                           attr = '_document')
    
    def getName(self):
        if not self._name:
            return self.id
        return self._name
    
    def setName(self, data):
        try:
            data = validate_id(data)
        except ValueError:
            msg = "Invalid resource name: %s"
            raise InvalidParameterError(msg % str(data))
        self._name = data
        
    name = property(getName, setName, "Alphanumeric name (optional)")


def _prepare_xml_data(data):
    """Prepare xml data for use with the database"""
    # convert data to unicode and remove xml declaration
    if isinstance(data, unicode):
        data, _ = parseXMLDeclaration(data, remove_decl = True)
    else:
        data, _ = toUnicode(data, remove_decl = True)
    return data

def newXMLDocument(data, id = None, uid = None):
    """Return a new XmlDocument. 
    Data will be converted to unicode and a possible XML declaration will be 
    removed. 
    Use this method whenever you wish to create a XmlDocument manually!
    """
    if len(data) == 0:
        raise InvalidParameterError("Xml data is empty.")
    data = _prepare_xml_data(data)
    return XmlDocument(data, id, uid)