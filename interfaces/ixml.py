# -*- coding: utf-8 -*-

from zope.interface import Interface, Attribute


class IXmlSchema(Interface):
    """General xml schema representation"""
    def validate(self,xml_doc):
        """Validate xml_doc against the schema.
        
        return true or false"""


class IXmlDoc(Interface):
    """General xml document"""
    def getXml_doc(self):
        """return an internal representation of the parsed xml_document"""


class IXmlTreeDoc(IXmlDoc):
    """parses a document into a tree representation"""
    options=Attribute("""dictionary specifying some options:
                     'blocking' : True|False : raises an Exception on parser 
                                                error and stops parser if set 
                                                to True
                      """)
    
    def getErrors(self):
        """return error messages, that occured during parsing"""


class IXmlSaxDoc(IXmlDoc):
    """parses a document using an event based sax parser"""