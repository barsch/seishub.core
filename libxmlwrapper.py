import libxml2
from seishub.core import implements

from interfaces.ixml import IXmlSchema,IXmlDoc,IXmlTreeDoc,IXmlSaxDoc

class InvalidXmlDataError(Exception):
    """raised on xml parser errors in blocking mode"""
    pass

class XmlSchema(object):
    """IXmlSchema implementation which makes use of libxml2"""
    implements(IXmlSchema)
    
    def __init__(self,schema_data):
        parser_ctxt = libxml2.schemaNewMemParserCtxt(schema_data, 
                                                     len(schema_data))
        schema = parser_ctxt.schemaParse()
        self.valid_ctxt  = schema.schemaNewValidCtxt()
        del parser_ctxt
        del schema
        
    def __del__(self):
        del self.valid_ctxt
        libxml2.schemaCleanupTypes() #TODO: not sure what that is for
    
    def validate(self,xml_doc):
        self.valid_ctxt.setValidityErrorHandler(self._handleValidationError, 
                                                self._handleValidationError,
                                                xml_doc)
        err_val=xml_doc.getXml_doc().schemaValidateDoc(self.valid_ctxt)
        if (err_val == 0):
             ret=True
        else:
             ret=False
             
        return ret
    
    def _handleValidationError(self,msg,data):
        data.errors.append({'msg':msg})
        
class XmlDoc(object):
    """IXmlDoc implementation which makes use of libxml2"""
    
    implements(IXmlDoc)
    
    def __init__(self,xml_doc):
        self.xml_doc=xml_doc
    
    def getXml_doc(self):
        return self.xml_doc


class XmlTreeDoc(XmlDoc):
    """This class parses a document using the libxml2 push parser""" 
    implements(IXmlTreeDoc)
    
    def __init__(self,xml_data,resource_name="",blocking=False):
        self.errors=list()
        self.options={'blocking':blocking,}
        if xml_data is not None:
            self.xml_data=xml_data
        else:
            raise InvalidXmlDataError("no xml data was given: %s" % xml_data)
        self.resource_name=resource_name
        self._parse()
        
    def __del__(self):
        if hasattr(self,'xml_doc'):
            if isinstance(self.xml_doc,libxml2.xmlDoc):
                self.xml_doc.freeDoc()
        
    def _parse(self):
        parser_ctxt = libxml2.createPushParser(None, "", 0, self.resource_name)
        parser_ctxt.setErrorHandler(self._handleParserError,None)
        parser_ctxt.parseChunk(self.xml_data,len(self.xml_data),1)
        if self.options['blocking'] and len(self.errors)>0:
            raise InvalidXmlDataError(self.errors)
        self.xml_doc=parser_ctxt.doc()
    
    def getErrors(self):
        return self.errors
        
    def _handleParserError(self,arg,msg,severity,reserved):
        self.errors.append({'msg':msg,'severity':severity})
        
        
class XmlSaxDoc(XmlDoc):
    """This class makes use of the libxml2 sax parser"""
    implements(IXmlSaxDoc)

