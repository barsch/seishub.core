# -*- coding: utf-8 -*-

from StringIO import StringIO
from lxml import etree
from seishub.exceptions import SeisHubError
from zope.interface import implements, Interface, Attribute
from zope.interface.exceptions import DoesNotImplement


class IXmlNode(Interface):
    """Basic xml node object"""
    def getStrContent():
        """@return: element content of node as a string"""


class IXmlStylesheet(Interface):
    """Parsed XML Stylesheet document"""
    def transform(xmltree_doc):
        """Transform given xmltree_doc with the stylesheet.
        @param xml_doc: XML Tree Document
        @type xml_doc: IXmlDoc 
        @return: XML Document"""


class IXmlSchema(Interface):
    """parsed XML Schema document"""
    def setSchemaDoc(self, schema_doc):
        """@param schema_doc: XML Schema document as plain text
        @type schema_doc: string"""
        
    def getSchemaDoc(self):
        """@return: XML Schema document as plain text
        @rtype: string"""
    
    def validate(xml_doc):
        """Validate xml_doc against the schema.
        @param xml_doc: XML Document
        @type xml_doc: IXmlDoc 
        @return: boolean"""


class IXmlDoc(Interface):
    """General xml document"""
    def getXml_doc():
        """return an internal representation of the parsed xml_document"""


class IXmlTreeDoc(IXmlDoc):
    """parses a document into a tree representation"""
    options=Attribute("""dictionary specifying some options:
                     'blocking' : True|False : raises an Exception on parser 
                                               error and stops parser if set 
                                               to True
                      """)
    
    def getErrors():
        """return error messages, that occured during parsing"""
    
    def evalXPath(expr):
        """Evaluate an XPath expression
        @param expr: string
        @return: array of resulting nodes"""


class IXmlSaxDoc(IXmlDoc):
    """parses a document using an event based sax parser"""


class InvalidXmlDataError(SeisHubError):
    """raised on xml parser errors in blocking mode"""
    pass


class InvalidXPathExpression(SeisHubError):
    pass


class XmlNode(object):
    """simple wrapper for libxml2.xmlNode"""
    encoding = "utf-8"
    
    def __init__(self,node_obj=None):
        self.setNode_obj(node_obj)
        
    def __str__(self):
        return self.getStrContent()
            
    def setNode_obj(self,node_obj):
        self._node_obj = node_obj
        
    def getNode_obj(self):
        return self._node_obj
        
    def getStrContent(self):
        if isinstance(self._node_obj, basestring):
            str = self._node_obj
        elif len(self._node_obj.getchildren()) == 0:
            str = self._node_obj.text
        else:
            str = etree.tostring(self._node_obj, 
                                 encoding = self.encoding)
        return str


class XmlStylesheet(object):
    """XSLT document representation"""
    implements(IXmlStylesheet)
    
    def __init__(self, stylesheet_data):
        f = StringIO(stylesheet_data)
        xslt_doc = etree.parse(f)
        self.transform_func = etree.XSLT(xslt_doc)
        # fetch any included media type
        root = xslt_doc.getroot()
        self.content_type = root.xpath('.//xsl:output/@media-type', 
                                       namespaces=root.nsmap)
    
    def transform(self, xmltree_doc):
        if not IXmlDoc.providedBy(xmltree_doc):
            raise DoesNotImplement(IXmlDoc)
        result_tree = self.transform_func(xmltree_doc.getXml_doc())
        return result_tree


class XmlSchema(object):
    """
    Schema representation.
    
    Internally we use one class of the supported schemas classes of L{lxml}, so
    far either XMLSchema, RelaxNG or Schematron.
    """
    implements(IXmlSchema)
    
    def __init__(self, schema_data, schema_type='XMLSchema'):
        f = StringIO(schema_data)
        schema_doc = etree.parse(f)
        if schema_type not in ['XMLSchema', 'RelaxNG', 'Schematron']:
            raise SeisHubError("Invalid schema type: %s" % schema_type)
        try:
            func = getattr(etree, schema_type)
            self.schema = func(schema_doc)
        except Exception, e:
            msg = "Could not parse a schema %s"
            raise SeisHubError(msg % (e.message))
    
    def validate(self,xml_doc):
        if not IXmlDoc.providedBy(xml_doc):
            raise DoesNotImplement(IXmlDoc)
        doc = xml_doc.getXml_doc()
        try:
            self.schema.assertValid(doc)
        except AttributeError:
            valid = self.schema.validate(doc)
            if not valid:
                msg = "Could not validate document."
                raise SeisHubError(msg)
        except etree.DocumentInvalid, e:
            msg = "Could not validate document. (%s)"
            raise InvalidXmlDataError(msg % e.message)


class XmlDoc(object):
    """XML document"""
    implements(IXmlDoc)
    
    def __init__(self,xml_doc=None):
        if xml_doc:
            self._xml_doc=xml_doc
    
    def getXml_doc(self):
        if hasattr(self,'_xml_doc'):
            return self._xml_doc
        return None
        
    def getRootElementName(self):
        return self._xml_doc.getroot().tag
    
    def getRoot(self):
        return self._xml_doc.getroot()


class XmlTreeDoc(XmlDoc):
    """XML document using lxml's element tree parser""" 
    implements(IXmlTreeDoc)
    
    def __init__(self, xml_data=None, resource_name="", blocking=False):
        XmlDoc.__init__(self)
        self.errors = list()
        self.options = {'blocking':blocking,}
        if isinstance(xml_data, basestring):
            self._xml_data = xml_data
        else:
            raise InvalidXmlDataError("No xml data str was given: %s" % xml_data)
        self._resource_name = resource_name
        self._parse()
        
    def _parse(self):
        parser = etree.XMLParser()
        data = StringIO(self._xml_data)
        try:
            self._xml_doc = etree.parse(data, parser)
        except Exception, e:
            raise InvalidXmlDataError("Invalid XML data.", e)
        self.errors = parser.error_log
        if self.options['blocking'] and len(self.errors) > 0:
            raise InvalidXmlDataError(self.errors)
        return True
    
    def getErrors(self):
        return self.errors

    def evalXPath(self,expr):
        #import pdb;pdb.set_trace()
        if not isinstance(expr,basestring):
            raise TypeError('String expected: %s' % expr)
        root = self.getRoot()
        try:
            res = self._xml_doc.xpath(expr, namespaces = root.nsmap)
        except Exception, e:
            raise InvalidXPathExpression(("Error evaluating a XPath " +\
                                         "expression: %s") % str(expr), e)
        if res:
            nodes = [XmlNode(node) for node in res]
        else:
            nodes = list()
        return nodes
