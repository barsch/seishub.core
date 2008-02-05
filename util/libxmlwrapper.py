# -*- coding: utf-8 -*-

import libxml2
from zope.interface import implements
from seishub.core import SeisHubError

from seishub.interfaces import IXmlSchema,IXmlDoc,IXmlTreeDoc,IXmlSaxDoc

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
    def __init__(self,node_obj=None):
        self.setNode_obj(node_obj)
        
    def __str__(self):
        return self.getStrContent()
            
    def setNode_obj(self,node_obj):
        if isinstance(node_obj,libxml2.xmlNode):
            self._node_obj=node_obj
        else:
            self._node_obj=None
            raise TypeError('setNode_obj: libxml2.xmlNode expected')
        
    def getNode_obj(self):
        return self._node_obj
        
    def getStrContent(self):
        if self._node_obj:
            return self._node_obj.getContent()
        else:
            return None
        

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
    
    def __init__(self,xml_doc=None):
        if xml_doc:
            self._xml_doc=xml_doc
            
    def __del__(self):
        #import pdb; pdb.set_trace()
        if hasattr(self,'_xml_doc'):
            if isinstance(self._xml_doc,libxml2.xmlDoc):
                self._xml_doc.freeDoc()
            else:
                del self._xml_doc
    
    def getXml_doc(self):
        if hasattr(self,'_xml_doc'):
            return self._xml_doc
        else:
            return None
        
    def getRootElementName(self):
        return self._xml_doc.getRootElement().name

class XmlTreeDoc(XmlDoc):
    """This class parses a document using the libxml2 push parser""" 
    implements(IXmlTreeDoc)
    
    def __init__(self,xml_data=None,resource_name="",blocking=False):
        XmlDoc.__init__(self)
        self.errors=list()
        self.options={'blocking':blocking,}
        if isinstance(xml_data,basestring):
            self._xml_data=xml_data
        else:
            raise InvalidXmlDataError("No xml data str was given: %s" % xml_data)
        self._resource_name=resource_name
        self._parse()
        
    def _parse(self):
        # TODO: some errors aren't caught by error handler
        parser_ctxt = libxml2.createPushParser(None, "", 0, 
                                               self._resource_name)
        parser_ctxt.setErrorHandler(self._handleParserError,None)
        data = self._xml_data.encode("utf-8")
        parser_ctxt.parseChunk(data,len(data),1)
        if self.options['blocking'] and len(self.errors)>0:
            raise InvalidXmlDataError(self.errors)
        try:
            self._xml_doc=parser_ctxt.doc()
        except:
            raise InvalidXmlDataError("Xml doc creation failed")
    
    def getErrors(self):
        return self.errors
        
    def _handleParserError(self,arg,msg,severity,reserved):
        self.errors.append({'msg':msg,'severity':severity})

    def evalXPath(self,expr):
        if not isinstance(self._xml_doc,libxml2.xmlDoc):
            raise LibxmlError('_xml_doc: libxml2.xmlDoc instance expected')
            return None
        
        if not isinstance(expr,basestring):
            raise TypeError('String expected: expr')
            return None
        
        #TODO: errors are still reported on stderr
        xpath_ctxt=self._xml_doc.xpathNewContext()
        
        try:
            res=xpath_ctxt.xpathEval(expr)
        except libxml2.xpathError:
            raise InvalidXPathExpression(expr)
        if res:
            nodes=[XmlNode(node) for node in res]
        else:
            nodes=list()
        
        xpath_ctxt.xpathFreeContext()
        return nodes
        
class XmlSaxDoc(XmlDoc):
    """This class makes use of the libxml2 sax parser"""
    implements(IXmlSaxDoc)

