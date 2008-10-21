from StringIO import StringIO

from lxml import etree
from zope.interface import implements, Interface, Attribute
from zope.interface.exceptions import DoesNotImplement

from seishub.core import SeisHubError

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


class LibxmlError(SeisHubError):
    """general libxml error"""
    pass


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
    """XSD document representation"""
    implements(IXmlSchema)
    
    def __init__(self, schema_data):
        f = StringIO(schema_data)
        schema_doc = etree.parse(f)
        self.schema = etree.XMLSchema(schema_doc)
    
    def validate(self,xml_doc):
        if not IXmlDoc.providedBy(xml_doc):
            raise DoesNotImplement(IXmlDoc)
        
        valid = self.schema.validate(xml_doc.getXml_doc())
        if not valid:
            return False
        
        return True


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
        self._xml_doc = etree.parse(data,parser)
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

#class XmlNode(object):
#    """simple wrapper for libxml2.xmlNode"""
#    def __init__(self,node_obj=None):
#        self.setNode_obj(node_obj)
#        
#    def __str__(self):
#        return self.getStrContent()
#            
#    def setNode_obj(self,node_obj):
#        if isinstance(node_obj,libxml2.xmlNode):
#            self._node_obj=node_obj
#        else:
#            self._node_obj=None
#            raise TypeError('setNode_obj: libxml2.xmlNode expected')
#        
#    def getNode_obj(self):
#        return self._node_obj
#        
#    def getStrContent(self):
#        if self._node_obj:
#            return self._node_obj.getContent()
#        else:
#            return None
#        
#
#class XmlSchema(object):
#    """IXmlSchema implementation which makes use of libxml2"""
#    implements(IXmlSchema)
#    
#    def __init__(self,schema_data):
#        parser_ctxt = libxml2.schemaNewMemParserCtxt(schema_data, 
#                                                     len(schema_data))
#        schema = parser_ctxt.schemaParse()
#        self.valid_ctxt  = schema.schemaNewValidCtxt()
#        del parser_ctxt
#        del schema
#        
#    def __del__(self):
#        del self.valid_ctxt
#        libxml2.schemaCleanupTypes() #TODO: not sure what that is for
#    
#    def validate(self,xml_doc):
#        self.valid_ctxt.setValidityErrorHandler(self._handleValidationError, 
#                                                self._handleValidationError,
#                                                xml_doc)
#        err_val=xml_doc.getXml_doc().schemaValidateDoc(self.valid_ctxt)
#        if (err_val == 0):
#            ret=True
#        else:
#            ret=False
#             
#        return ret
#    
#    def _handleValidationError(self,msg,data):
#        data.errors.append({'msg':msg})
#        
#class XmlDoc(object):
#    """IXmlDoc implementation which makes use of libxml2"""
#    implements(IXmlDoc)
#    
#    def __init__(self,xml_doc=None):
#        if xml_doc:
#            self._xml_doc=xml_doc
#            
#    def __del__(self):
#        if hasattr(self,'_xml_doc'):
#            if isinstance(self._xml_doc,libxml2.xmlDoc):
#                self._xml_doc.freeDoc()
#            else:
#                del self._xml_doc
#    
#    def getXml_doc(self):
#        if hasattr(self,'_xml_doc'):
#            return self._xml_doc
#        else:
#            return None
#        
#    def getRootElementName(self):
#        return self._xml_doc.getRootElement().name
#
#class XmlTreeDoc(XmlDoc):
#    """This class parses a document using the libxml2 push parser""" 
#    implements(IXmlTreeDoc)
#    
#    def __init__(self,xml_data=None,resource_name="",blocking=False):
#        XmlDoc.__init__(self)
#        self.errors=list()
#        self.options={'blocking':blocking,}
#        if isinstance(xml_data,basestring):
#            self._xml_data=xml_data
#        else:
#            raise InvalidXmlDataError("No xml data str was given: %s" % xml_data)
#        self._resource_name=resource_name
#        self._parse()
#        
#    def _parse(self):
#        # TODO: some errors aren't caught by error handler
#        parser_ctxt = libxml2.createPushParser(None, "", 0, 
#                                               self._resource_name)
#        parser_ctxt.setErrorHandler(self._handleParserError,None)
#        
#        data = self._xml_data
#        
#        # XXX: this is the only way its working for uploading *and* showing 
#        # in REST - needs fixing!!!
#
##        try:
##            data = self._xml_data.encode("utf-8")
##        except:
##            pass
##        
#        parser_ctxt.parseChunk(data,len(data),1)
#        if self.options['blocking'] and len(self.errors)>0:
#            raise InvalidXmlDataError(self.errors)
#        try:
#            self._xml_doc=parser_ctxt.doc()
#        except:
#            raise InvalidXmlDataError("Xml doc creation failed")
#    
#    def getErrors(self):
#        return self.errors
#        
#    def _handleParserError(self,arg,msg,severity,reserved):
#        self.errors.append({'msg':msg,'severity':severity})
#
#    def evalXPath(self,expr):
#        if not isinstance(self._xml_doc,libxml2.xmlDoc):
#            raise LibxmlError('_xml_doc: libxml2.xmlDoc instance expected')
#            return None
#        
#        if not isinstance(expr,basestring):
#            raise TypeError('String expected: expr')
#            return None
#        
#        #TODO: errors are still reported on stderr
#        xpath_ctxt=self._xml_doc.xpathNewContext()
#        
#        try:
#            res=xpath_ctxt.xpathEval(expr)
#        except libxml2.xpathError:
#            raise InvalidXPathExpression(expr)
#        if res:
#            nodes=[XmlNode(node) for node in res]
#        else:
#            nodes=list()
#        
#        xpath_ctxt.xpathFreeContext()
#        return nodes
#        
#class XmlSaxDoc(XmlDoc):
#    """This class makes use of the libxml2 sax parser"""
#    implements(IXmlSaxDoc)