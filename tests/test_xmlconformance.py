# -*- coding: utf-8 -*-

import unittest
import os
import inspect
import libxml2

from seishub.test import SeisHubTestCase
from seishub.util.text import checkXMLWellFormed


class XMLConformanceTestCase(SeisHubTestCase):
    """Wrapper class for the XML Conformance Test Suite 20080205 provided by 
    W3C (see http://www.w3.org/XML/Test/)."""
    
    def setUp(self):
        #setup a test
        path = os.path.dirname(inspect.getsourcefile(self.__class__))
        self.test_path = os.path.join(path,'data', 'xmlconf')
        
    def tearDown(self):
        # clean up again
        pass
    
    def testXmltest(self):
        path = self.test_path
        testcase = 'xmltest'
        filename = 'xmltest.xml'
        self._runXMLTestCase(path, testcase, filename)
    
    def testJapanese(self):
        path = self.test_path
        testcase = 'japanese'
        filename = 'japanese.xml'
        self._runXMLTestCase(path, testcase, filename)
    
    def _runXMLTestCase(self, path, testcase, filename):
        """Parse and evaluate a given test case."""
        testcase_file = os.path.join(path, testcase, filename)
        doc = libxml2.parseFile(testcase_file)
        ctxt = doc.xpathNewContext()
        tests = ctxt.xpathEval("//TESTCASES//TEST")
        for test in tests:
            props = {}
            props['type'] = test.prop('TYPE')
            props['entities'] = test.prop('ENTITIES')
            props['output'] = test.prop('OUTPUT')
            filename = props['uri'] = test.prop('URI')
            self._runXMLTest(path, testcase, filename, props)
        doc.freeDoc()
        ctxt.xpathFreeContext()
    
    def _runXMLTest(self, path, testcase, filename, props):
        test_file = os.path.join(path, testcase, filename)
        test_id = os.path.join(testcase, filename)
        
        #check if well formed
        nwfd = checkXMLWellFormed(test_file)
        if props['type'] in ('not-wf', 'error') and nwfd:
            return
        if props['type'] in ('not-wf', 'error') or nwfd:
            print 'NOTWELLFORMED', test_id, '-', nwfd
        
        #check if valid
        vd = self._isValidXMLDocument(test_file)
        if props['type']=='invalid':
            if vd:
                print 'INVALID', test_id, '-', 'Should not be marked as valid!'
            return
        
        fh = open(test_file, 'r')
        data = fh.read()
        fh.close()
        try:
            res = self.env.catalog.newXmlResource('/test/'+props['uri'], data)
        except Exception, e:
            print test_id, '-', e
            return
        try:
            self.env.catalog.addResource(res)
        except Exception, e:
            print test_id, '-', e
    
    def _isValidXMLDocument(self, filename):
        """Validates a XML document."""
        
        #deactivate error messages from the validation
        def noerr(ctx, str):
            pass
        libxml2.registerErrorHandler(noerr, None)
        
        try: 
            ctxt = libxml2.createFileParserCtxt(filename)
            ctxt.validate(1)
            ctxt.parseDocument()
            doc = ctxt.doc()
        except:
            return False
        valid = ctxt.isValid()
        doc.freeDoc()
        return valid


def suite():
    return unittest.makeSuite(XMLConformanceTestCase, 'test')

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
