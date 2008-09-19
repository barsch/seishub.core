# -*- coding: utf-8 -*-

import re
from StringIO import StringIO

from lxml import etree
from zope.interface import implements, Interface, Attribute
from zope.interface.exceptions import DoesNotImplement

from seishub.core import SeisHubError


# XXX: interfaces should not be defined here - this is a util section :b

class IXmlNode(Interface):
    """Basic xml node object"""
    def getStrContent():
        """@return: element content of node as a string"""


class IXmlStylesheet(Interface):
    """Parsed XML Stylesheet document"""
    def validate(xmltree_doc):
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


class XmlTreeDoc(XmlDoc):
    """XML document using lxml's element tree parser""" 
    implements(IXmlTreeDoc)
    
    def __init__(self,xml_data=None,resource_name="",blocking=False):
        XmlDoc.__init__(self)
        self.errors = list()
        self.options = {'blocking':blocking,}
        if isinstance(xml_data,basestring):
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
        if not isinstance(expr,basestring):
            raise TypeError('String expected: %s' % expr)
        
        try:
            res = self._xml_doc.xpath(expr)
        except Exception, e:
            raise InvalidXPathExpression(e)
        #import pdb; pdb.set_trace()
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
#        #import pdb; pdb.set_trace()
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

def toUnicode(data):
    """Convert XML string to unicode by detecting the encoding."""
    encoding = detectXMLEncoding(data)
    if encoding:
        data = unicode(data, encoding)
    return data


def detectXMLEncoding(data):
    """Attempts to detect the character encoding of the given XML string.
    
    The return value can be:
        - if detection of the BOM succeeds, the codec name of the
        corresponding unicode charset is returned
        
        - if BOM detection fails, the xml declaration is searched for
        the encoding attribute and its value returned. the "<"
        character has to be the very first in the file then (it's xml
        standard after all).
        
        - if BOM and xml declaration fail, None is returned. According
        to xml 1.0 it should be utf_8 then, but it wasn't detected by
        the means offered here. at least one can be pretty sure that a
        character coding including most of ASCII is used :-/
    
    @author: Lars Tiede
    @since: 2005/01/20
    @version: 1.1
    @see: U{http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/363841}
          U{http://www.w3.org/TR/2006/REC-xml-20060816/#sec-guessing}
    """
    ### detection using BOM
    
    ## the BOMs we know, by their pattern
    bomDict={ # bytepattern : name              
             (0x00, 0x00, 0xFE, 0xFF) : "utf-32be",
             (0xFF, 0xFE, 0x00, 0x00) : "utf-32le",
             (0xFE, 0xFF, None, None) : "utf-16be",
             (0xFF, 0xFE, None, None) : "utf-16le",
             (0xEF, 0xBB, 0xBF, None) : "utf-8",
            }
    ## go to beginning of file and get the first 4 bytes
    try:
        (byte1, byte2, byte3, byte4) = tuple(map(ord, data[0:4]))
    except:
        return None
    
    ## try bom detection using 4 bytes, 3 bytes, or 2 bytes
    bomDetection = bomDict.get((byte1, byte2, byte3, byte4))
    if not bomDetection :
        bomDetection = bomDict.get((byte1, byte2, byte3, None))
        if not bomDetection :
            bomDetection = bomDict.get((byte1, byte2, None, None))
    
    ## if BOM detected, we're done :-)
    if bomDetection :
        return bomDetection
    
    
    ## still here? BOM detection failed.
    ##  now that BOM detection has failed we assume one byte character
    ##  encoding behaving ASCII - of course one could think of nice
    ##  algorithms further investigating on that matter, but I won't for now.
    
    
    ### search xml declaration for encoding attribute
    
    ## set up regular expression
    xmlDeclPattern = r"""
    ^<\?xml             # w/o BOM, xmldecl starts with <?xml at the first byte
    .+?                 # some chars (version info), matched minimal
    encoding=           # encoding attribute begins
    ["']                # attribute start delimiter
    (?P<encstr>         # what's matched in the brackets will be named encstr
     [^"']+              # every character not delimiter (not overly exact!)
    )                   # closes the brackets pair for the named group
    ["']                # attribute end delimiter
    .*?                 # some chars optionally (standalone decl or whitespace)
    \?>                 # xmldecl end
    """
    
    xmlDeclRE = re.compile(xmlDeclPattern, re.VERBOSE)
    
    ## search and extract encoding string
    match = xmlDeclRE.search(data)
    if match :
        return match.group("encstr")
    else :
        return None
