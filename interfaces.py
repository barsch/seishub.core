# -*- coding: utf-8 -*-

from zope.interface import Interface, Attribute


class IResource(Interface):
    """A basic resource consist at least of an unique uri and optionally of
    any kinds of data
    """
    def getUri(self):
        """retrieve the resource's uri """
        
    def setUri(self,newuri):
        """change resource's uri attribute
        a resource cannot be serialized without specifying an uri
        """
        
    def setData(self,newdata):
        """set data attribute"""
        
    def getData(self):
        """retrieve the resource's data"""
        

class IXmlNode(Interface):
    """Basic xml node object"""
    def getStrContent():
        """@return: element content of node as a string"""

class IXmlSchema(Interface):
    """General xml schema representation"""
    def validate(xml_doc):
        """Validate xml_doc against the schema.
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

