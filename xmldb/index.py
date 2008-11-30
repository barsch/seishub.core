# -*- coding: utf-8 -*-

from datetime import datetime

from seishub.core import implements
from seishub.db.util import Serializable, Relation, db_property
from seishub.packages.package import ResourceTypeWrapper
from seishub.xmldb import defaults
from seishub.xmldb.interfaces import IXmlDocument, IXmlIndex
from seishub.xmldb.resource import XmlDocument


TEXT_INDEX = 0
NUMERIC_INDEX = 1
DATETIME_INDEX = 2
BOOLEAN_INDEX = 3
NONETYPE_INDEX = 4

ISO_FORMAT = "%Y%m%dT%H:%M:%S"

class XmlIndex(Serializable):
    """A XML index definition.
    
    @param resourcetype: ReosurcetypeWrapper instance
    @param xpath: path to node in XML tree to be indexed, or any arbitrary 
    xpath expression, that returns a value of correct type
    @param type: TEXT_INDEX | NUMERIC_INDEX | DATETIME_INDEX | BOOLEAN_INDEX |
                 NONETYPE_INDEX
    @param options: additional options for an index
    
    notes:
     - DATETIME_INDEX:
     options may be a format string (see time.strftime() documentation), but 
     note that strftime / strptime does not support microseconds (!)
     
     without a format string, ISO 8601 strings and timestamps are autodetected.
    """
    implements(IXmlIndex)
    
    db_table = defaults.index_def_tab
    db_mapping = {'resourcetype':Relation(ResourceTypeWrapper, 
                                          'resourcetype_id'),
                  'xpath':'xpath',
                  'type':'type',
                  'options':'options'}
    
    def __init__(self, resourcetype = None, xpath = None, type = TEXT_INDEX, 
                 options = None):
        self.resourcetype = resourcetype
        self.xpath = xpath
        self.type = type
        self.options = options
    
    def __str__(self):
        return '/' + self.resourcetype.package.package_id + '/' + \
                self.resourcetype.resourcetype_id + '/' + self.xpath
                
    def getResourceType(self):
        return self._resourcetype
     
    def setResourceType(self, data):
        self._resourcetype = data
        
    resourcetype = db_property(getResourceType, setResourceType, 
                               "Resource type", attr = '_resourcetype')
    
    def getXPath(self):
        return self._xpath
        
    def setXPath(self, xpath):
        self._xpath = xpath
    
    xpath = property(getXPath, setXPath, "XPath expression")
    
    def getType(self):
        return self._type
    
    def setType(self, type):
        self._type = type
        if type == NUMERIC_INDEX:
            self._element_cls = NumericIndexElement
        elif type == DATETIME_INDEX:
            self._element_cls = DateTimeIndexElement
        elif type == BOOLEAN_INDEX:
            self._element_cls = BooleanIndexElement
        elif type == NONETYPE_INDEX:
            self._element_cls = NoneTypeIndexElement
        else:
            self._element_cls = TextIndexElement
    
    type = property(getType, setType, "Data type")
    
    def _getElementCls(self):
        return self._element_cls
    
    def eval(self, xml_doc):
        if not IXmlDocument.providedBy(xml_doc):
            raise TypeError("%s is not an IXmlDocument." % str(xml_doc))
        parsed_doc = xml_doc.getXml_doc()
        nodes = parsed_doc.evalXPath(self.xpath)
        res = list()
        for node in nodes:
            try:
                res.append(self._element_cls(self, node, xml_doc))
            except:
                continue
        return res
    
class KeyIndexElement(Serializable):
    db_mapping = {'index':Relation(XmlIndex, 'index_id'),
                  'key':'key',
                  'document':Relation(XmlDocument, 'document_id')
                  }
    
    def __init__(self, index, key, document):
        self.index = index
        self.key = self._filter_key(key)
        self.document = document
        
    def _filter_key(self, data):
        """Overwritten to do a type specific key handling"""
        return data
        
    def getIndex(self):
        return self._index
     
    def setIndex(self, data):
        self._index = data
        
    index = db_property(getIndex, setIndex, "Index", attr = '_index')
    
    def getDocument(self):
        return self._document
     
    def setDocument(self, data):
        self._document = data
        
    document = db_property(getDocument, setDocument, "XmlDocument", 
                           attr = '_document')
    
    def getKey(self):
        return self._key
    
    def setKey(self, data):
        self._key = data
        
    key = property(getKey, setKey, "Index key")
        
    
class QualifierIndexElement(Serializable):
    db_mapping = {'index':Relation(XmlIndex, 'index_id'),
                  'document':Relation(XmlDocument, 'document_id')
                  }
    
    def __init__(self, index, key, document):
        self.index = index
        # ignore key
        self.key = None
        self.document = document
        
    def getIndex(self):
        return self._index
     
    def setIndex(self, data):
        self._index = data
        
    index = db_property(getIndex, setIndex, "Index", attr = '_index')
    
    def getDocument(self):
        return self._document
     
    def setDocument(self, data):
        self._document = data
        
    document = db_property(getDocument, setDocument, "XmlDocument", 
                           attr = '_document')
    

class TextIndexElement(KeyIndexElement):
    db_table = defaults.index_text_tab
    
    def _filter_key(self, data):
        return unicode(data.getStrContent())
        

class NumericIndexElement(KeyIndexElement):
    db_table = defaults.index_numeric_tab
    
    def _filter_key(self, data):
        return float(data.getStrContent())


class DateTimeIndexElement(KeyIndexElement):
    db_table = defaults.index_datetime_tab
    
    def _filter_key(self, data):
        data = data.getStrContent()
        if self.index.options:
            return datetime.strptime(data, self.index.options)
        try:
            # XXX: this might lead to problems with iso strings that consist of numbers only
            # another solution would be to have a special '%timestamp' option
            return datetime.fromtimestamp(float(data))
        except ValueError:
            data, ms = data.split('.')
            ms = int(ms.ljust(6,'0')[:6]) 
            dt = datetime.strptime(data.replace("-", ""), ISO_FORMAT)
            return dt.replace(microsecond = ms) 


class BooleanIndexElement(KeyIndexElement):
    db_table = defaults.index_boolean_tab
    
    def _filter_key(self, data):
        data = data.getStrContent()
        try:
            return bool(int(data))
        except ValueError:
            pass
        return not data.lower() == "false"


class NoneTypeIndexElement(QualifierIndexElement):
    db_table = defaults.index_keyless_tab


#class IndexBase(Serializable):
#    db_table = index_def_tab
#    db_mapping = {'key_path':'key_path',
#                  'value_path':'value_path',
#                  'type':'data_type'}
#    
#    def __init__(self,value_path=None, key_path=None, type=TEXT_INDEX):
#        super(IndexBase, self).__init__()
#        if not (value_path and key_path):
#            raise TypeError("No index definition given.")
#        self.value_path = value_path
#        self.key_path = key_path
#        if isinstance(type,basestring):
#            self.type = type
#        else:
#            self.type = TEXT_INDEX
#        self._values=list()
#        
#    def __str__(self):
#        return '/' + self.value_path + '/' + self.key_path
#              
#    def getValue_path(self):
#        if hasattr(self,'_value_path'):
#            return self._value_path
#        else:
#            return None
#        
#    def setValue_path(self, value_path):
#        if value_path.startswith('/'):
#            value_path = value_path[1:]
#        self._value_path = value_path
#    
#    value_path = property(getValue_path, setValue_path, "Value path")
#    
#    def getKey_path(self):
#        if hasattr(self,'_key_path'):
#            return self._key_path
#    
#    def setKey_path(self, key_path):
#        self._key_path = key_path
#        
#    key_path = property(getKey_path, setKey_path, "Key path")
#        
#    def getType(self):
#        return self._type
#    
#    def setType(self, type):
#        self._type = type
#    
#    type = property(getType, setType, "Data type")
#    
#    def getValues(self):
#        return self._values
#
#class XmlIndex(IndexBase):
#    implements(IXmlIndex)
#          
#    def __str__(self):
#        return '/' + self.value_path + '/' + self.key_path
#    
#    def _getRootElementName(self):
#        elements = self.value_path.split('/')
#        # last element is root element
#        return elements[len(elements)-1]
#
#    # methods from IXmlIndex:
#    
#    def eval(self, xml_resource):
#        if not IXmlDocument.providedBy(xml_resource):
#            raise TypeError("%s is not an IXmlDocument." % str(xml_resource))
#        
#        xml_doc = xml_resource.getXml_doc()
#        if not xml_doc:
#            raise SeisHubError('Invalid XML document')
#        
#        # build xpath expression to evaluate on xml document
#        xpr = '/' + self._getRootElementName() + '/' + self.getKey_path()
#        nodes = xml_doc.evalXPath(xpr)
#        
#        node_size = len(nodes)
#        if node_size == 0:
#            return None
#        
#        idx_value = xml_resource._id
#        res = [{'key':node.getStrContent(),
#                'value':idx_value} for node in nodes]
#        self._values.append(idx_value)
#        
#        return res
#
#class VirtualIndex(IndexBase):
#    implements(IVirtualIndex)
#    
#    # methods from IVirtualIndex
#    def setValue(self, data):
#        """@see: L{seishub.xmldb.interfaces.IVirtualIndex}"""
#        # TODO: validate type of data
#        self._values.append(data)