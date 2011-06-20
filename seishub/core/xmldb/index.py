# -*- coding: utf-8 -*-

from datetime import datetime
from seishub.core.core import implements
from seishub.core.db.orm import Serializable, Relation, db_property
from seishub.core.xmldb import defaults
from seishub.core.xmldb.interfaces import IXmlDocument, IXmlIndex
from seishub.core.xmldb.resource import XmlDocument
from twisted.python import log
import sys
from seishub.core.registry.package import ResourceTypeWrapper
from obspy.core import UTCDateTime


TEXT_INDEX = 0
NUMERIC_INDEX = 1
FLOAT_INDEX = 2
DATETIME_INDEX = 3
BOOLEAN_INDEX = 4
TIMESTAMP_INDEX = 5
PROCESSOR_INDEX = 6
DATE_INDEX = 7
INTEGER_INDEX = 8

DATETIME_ISO_FORMAT = "%Y%m%d %H%M%S"
DATE_ISO_FORMAT = "%Y%m%d"
_FALSE_VALUES = ('no', 'false', 'off', '0', 'disabled')

INDEX_TYPES = {
    "text":      TEXT_INDEX,
    "integer":   INTEGER_INDEX,
    "numeric":   NUMERIC_INDEX,
    "float":     FLOAT_INDEX,
    "datetime":  DATETIME_INDEX,
    "date":      DATE_INDEX,
    "timestamp": TIMESTAMP_INDEX,
    "boolean":   BOOLEAN_INDEX,
}


class XmlIndex(Serializable):
    """
    A XML index.
    
    @param resourcetype: ResourcetypeWrapper instance
    @param xpath: path to node in XML tree to be indexed, or any arbitrary 
    xpath expression, that returns a value of correct type
    @param type: TEXT_INDEX | NUMERIC_INDEX | DATETIME_INDEX | BOOLEAN_INDEX |
                 DATE_INDEX | FLOAT_INDEX | INTEGER_INDEX | TIMESTAMP_INDEX
    @param options: additional options for an index
    
    Note:
    DATETIME_INDEX: options may be a format string (see time.strftime() 
    documentation), but note that strftime / strptime does not support 
    microseconds! Without a format string we assume a ISO 8601 string.
    """

    implements(IXmlIndex)

    db_table = defaults.index_def_tab
    db_mapping = {
        'resourcetype':Relation(ResourceTypeWrapper, 'resourcetype_id',
                                lazy=True),
        'xpath':'xpath',
        'group_path':'group_path',
        'type':'type',
        'options':'options',
        'label':'label',
        '_id':'id'
    }

    def __init__(self, resourcetype=None, xpath=None, type=TEXT_INDEX,
                 options=None, group_path=None, label=None):
        self.resourcetype = resourcetype
        self.xpath = xpath
        self.type = type
        self.options = options
        self.group_path = group_path
        self.relative_xpath = None
        self.label = label

    def __str__(self):
        return '/' + self.resourcetype.package.package_id + '/' + \
                self.resourcetype.resourcetype_id + self.xpath

    def getPackage_id(self):
        return self.resourcetype.package.package_id

    package_id = property(getPackage_id)

    def getResourcetype_id(self):
        return self.resourcetype.resourcetype_id

    resourcetype_id = property(getResourcetype_id)

    def getResourceType(self):
        return self._resourcetype

    def setResourceType(self, data):
        self._resourcetype = data

    resourcetype = db_property(getResourceType, setResourceType,
                               "Resource type", attr='_resourcetype')

    def getXPath(self):
        return self._xpath

    def setXPath(self, xpath):
        self._xpath = xpath

    xpath = property(getXPath, setXPath, "XPath expression")

    def getType(self):
        return self._type

    def setType(self, type):
        self._type = type

    type = property(getType, setType, "Data type")

    def getOptions(self):
        return self._options

    def setOptions(self, options):
        self._options = options

    options = property(getOptions, setOptions, "Options")

    def getRelative_xpath(self):
        if self.group_path and not self._relative_xpath:
            self._relative_xpath = self.xpath[len(self.group_path) + 1:]
        return self._relative_xpath

    def setRelative_xpath(self, data):
        self._relative_xpath = data

    relative_xpath = property(getRelative_xpath, setRelative_xpath,
                              "relative xpath")

    def _getElementCls(self):
        """
        Return the correct index element class, according to index type.
        """
        if self.type == PROCESSOR_INDEX:
            return type_classes[self._getProcessorIndex().type]
        return type_classes[self.type]

    def _getProcessorIndex(self):
        if hasattr(self, '_processor_idx'):
            return self._processor_idx
        # import the IProcessorIndex implementer class for this index
        pos = self.options.rfind(u".")
        class_name = self.options[pos + 1:]
        mod_name = self.options[:pos]
        mod = sys.modules[mod_name]
        cls = getattr(mod, class_name)
        # self._processor_idx = cls(env)
        self._processor_idx = cls
        return cls

    def _eval(self, xml_doc):
        if not IXmlDocument.providedBy(xml_doc):
            raise TypeError("%s is not an IXmlDocument." % str(xml_doc))
        parsed_doc = xml_doc.getXml_doc()
        try:
            if self.group_path:
                nodes = parsed_doc.evalXPath(self.group_path)
                return [node.evalXPath(self.relative_xpath) or [None]
                        for node in nodes]
            return [parsed_doc.evalXPath(self.xpath) or [None]]
        except Exception, e:
            log.err(e)
            return list()

    def eval(self, xml_doc, env=None):
        if self.type == PROCESSOR_INDEX:
            pidx = self._getProcessorIndex()(env)
            type = pidx.type
            elements = pidx.eval(xml_doc)
            if not isinstance(elements, list):
                elements = [elements]
            elements = [elements]
        else:
            type = self.type
            elements = self._eval(xml_doc)
        res = list()
        for pos, el_list in enumerate(elements):
            for el in el_list:
                # skip not existing nodes or ProcessorIndex
                if el and not self.type == PROCESSOR_INDEX:
                    el = el.getStrContent()
                try:
                    res.append(self._getElementCls()(self, el, xml_doc, pos))
                except Exception, e:
                    if env:
                        log.msg(e)
                    else:
                        # skip logging for test cases
                        continue
        return res

    def prepareKey(self, data):
        return self._getElementCls()()._prepare_key(data)


class KeyIndexElement(Serializable):
    """
    Base class for all indexes.
    """
    db_mapping = {
        '_id':'id',
        'index':Relation(XmlIndex, 'index_id'),
        'key':'keyval',
        'group_pos':'group_pos',
        'document':Relation(XmlDocument, 'document_id')
    }

    def __init__(self, index=None, key=None, document=None,
                 group_pos=None):
        self.index = index
        if key:
            self.key = self._filter_key(key)
        else:
            self.key = None
        self.document = document
        self.group_pos = group_pos

    def _filter_key(self, data):
        """
        Overwrite to do a type specific key handling.
        """
        return data

    def _prepare_key(self, data):
        return str(data)

    def getIndex(self):
        return self._index

    def setIndex(self, data):
        self._index = data

    index = db_property(getIndex, setIndex, "Index", attr='_index')

    def getDocument(self):
        return self._document

    def setDocument(self, data):
        self._document = data

    document = db_property(getDocument, setDocument, "XmlDocument",
                           attr='_document')

    def getKey(self):
        return self._key

    def setKey(self, data):
        self._key = data

    key = property(getKey, setKey, "Index key")


class TextIndexElement(KeyIndexElement):
    db_table = defaults.index_text_tab

    def _filter_key(self, data):
        return unicode(data)

    def _prepare_key(self, data):
        return unicode(data)


class NumericIndexElement(KeyIndexElement):
    db_table = defaults.index_numeric_tab

    def _filter_key(self, data):
        # don't pass floats directly to db
        # check if data has correct type
        float(data)
        return data


class FloatIndexElement(KeyIndexElement):
    db_table = defaults.index_float_tab

    def _filter_key(self, data):
        # check if data has correct type
        # but don't pass floats to db as string
        float(data)
        return data


class DateTimeIndexElement(KeyIndexElement):
    db_table = defaults.index_datetime_tab

    def _filter_key(self, data):
        if isinstance(data, UTCDateTime):
            return data.datetime
        elif isinstance(data, datetime):
            return data
        else:
            data = data.strip()
            if self.index.options:
                return datetime.strptime(data, self.index.options)
        return self._prepare_key(data)

    def _prepare_key(self, data):
        dt = UTCDateTime(data)
        return dt.datetime


class DateIndexElement(KeyIndexElement):
    db_table = defaults.index_date_tab

    def _filter_key(self, data):
        data = data.strip()
        if self.index.options:
            return datetime.strptime(data, self.index.options).date()
        return self._prepare_key(data)

    def _prepare_key(self, data):
        data = data.replace("-", "")
        return datetime.strptime(data, DATE_ISO_FORMAT).date()


class BooleanIndexElement(KeyIndexElement):
    db_table = defaults.index_boolean_tab

    def _filter_key(self, data):
        data = data.strip()
        if data.lower() in _FALSE_VALUES:
            return False
        return bool(data)


class IntegerIndexElement(KeyIndexElement):
    db_table = defaults.index_integer_tab

    def _filter_key(self, data):
        return int(data)


class TimestampIndexElement(KeyIndexElement):
    db_table = defaults.index_datetime_tab

    def _filter_key(self, data):
        data = data.strip()
        return UTCDateTime(float(data)).datetime


type_classes = {
    TEXT_INDEX:      TextIndexElement,
    NUMERIC_INDEX:   NumericIndexElement,
    FLOAT_INDEX:     FloatIndexElement,
    DATETIME_INDEX:  DateTimeIndexElement,
    BOOLEAN_INDEX:   BooleanIndexElement,
    DATE_INDEX:      DateIndexElement,
    INTEGER_INDEX:   IntegerIndexElement,
    TIMESTAMP_INDEX: TimestampIndexElement
}
