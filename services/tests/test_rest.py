# -*- coding: utf-8 -*-

import unittest
import os
import inspect
import libxml2
from xml.sax.handler import ContentHandler
from xml.sax import make_parser

from seishub.test import SeisHubTestCase


class XMLConformanceTest(SeisHubTestCase):
    """Wrapper class for the XML Conformance Test Suite 20080205 provided by 
    W3C (see http://www.w3.org/XML/Test/)."""
    
    def setUp(self):
        #setup a test
        path = os.path.dirname(inspect.getsourcefile(self.__class__))
        self.test_path = os.path.join(path,'data', 'xmlconf')
        
    def tearDown(self):
        # clean up again
        pass
    
    def test_muh(self):
        #filename = os.path.join(self.test_path, 'xmlconf.xml')
        #fh = open(filename, 'r')
        #data = fh.read()
        #fh.close()
        #doc = XmlTreeDoc(data)
        #print doc.getXml_doc()
        pass

    def test_xmltest(self):
        """Test all xmltest cases."""
        #construct a filename
        path = os.path.join(self.test_path, 'xmltest')
        filename = os.path.join(path, 'xmltest.xml')
        #fetch all test cases
        doc = libxml2.parseFile(filename)
        ctxt = doc.xpathNewContext()
        testcases = ctxt.xpathEval("//TESTCASES//TEST")
        for testcase in testcases:
            test_type = testcase.prop('TYPE')
            test_uri = testcase.prop('URI')
            test_filename = os.path.join(path, test_uri)
            self._xmltest(test_filename, 'xmltest/' + test_uri, test_type)
        doc.freeDoc()
        ctxt.xpathFreeContext()
    
    def _xmltest(self, test_filename, test_uri, test_type):
        
        #check if well formed
        wfd = self._isWellFormedXMLDocument(test_filename)
        if test_type=='not-wf' and not wfd:
            return
        #check if valid
        vd = self._isValidXMLDocument(test_filename)
        if test_type=='invalid' and not vd:
            return

        #here should be only valid documents handled
        if test_type!='valid':
            print test_uri, '-', 'Only valid documents should be left'
            return
        fh = open(test_filename, 'r')
        data = fh.read()
        fh.close()
        try:
            res = self.env.catalog.newXmlResource('/test/'+test_uri, data)
        except Exception, e:
            print test_uri, '-', e
            return
        try:
            self.env.catalog.addResource(res)
        except Exception, e:
            print test_uri, '-', e
    
    def _isValidXMLDocument(self, filename):
        """Validate a XML document."""
        #deactivate error messages from the validation
        def noerr(ctx, str):
            pass
        libxml2.registerErrorHandler(noerr, None)
        
        try: 
            ctxt = libxml2.createFileParserCtxt(filename)
            ctxt.validate(1)
            ctxt.parseDocument()
            doc = ctxt.doc()
        except Exception, e :
            return False
        valid = ctxt.isValid()
        doc.freeDoc()
        return valid
    
    def _isWellFormedXMLDocument(self, filename):
        """Checks if a document is well formed."""
        parser = make_parser()
        parser.setContentHandler(ContentHandler())
        try:
            parser.parse(filename)
        except Exception, e :
            return False
        return True


def suite():
    return unittest.makeSuite(XMLConformanceTest, 'test')

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
