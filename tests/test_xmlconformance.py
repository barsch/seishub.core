# -*- coding: utf-8 -*-

import unittest
import os
import inspect

from lxml import etree

from seishub.test import SeisHubEnvironmentTestCase


class XMLConformanceTestCase(SeisHubEnvironmentTestCase):
    """Wrapper class for the XML Conformance Test Suite 20080205 provided by 
    W3C (see http://www.w3.org/XML/Test/)."""
    
    def setUp(self):
        #setup a test
        path = os.path.dirname(inspect.getsourcefile(self.__class__))
        self.test_path = os.path.join(path,'data', 'xmlconf')
        self.env.registry.db_registerPackage('test')
        self.env.registry.db_registerResourceType('test', 'xml')
        
    def tearDown(self):
        # clean up again
        self.env.registry.db_deleteResourceType('test', 'xml')
        self.env.registry.db_deletePackage('test')
        
    def test_IBMInvalid(self):
        path = self.test_path
        testcase = 'ibm'
        filename = 'ibm_oasis_invalid.xml'
        self._runXMLTestCase(path, testcase, filename)
    
#    def test_Xmltest(self):
#        path = self.test_path
#        testcase = 'xmltest'
#        filename = 'xmltest.xml'
#        self._runXMLTestCase(path, testcase, filename)
#    
#    def test_Japanese(self):
#        path = self.test_path
#        testcase = 'japanese'
#        filename = 'japanese.xml'
#        self._runXMLTestCase(path, testcase, filename)
#    
#    def test_Oasis(self):
#        path = self.test_path
#        testcase = 'oasis'
#        filename = 'oasis.xml'
#        self._runXMLTestCase(path, testcase, filename)
#    
#    def test_EduniXML11(self):
#        path = self.test_path
#        testcase = os.path.join('eduni', 'xml-1.1')
#        filename = 'xml11.xml'
#        self._runXMLTestCase(path, testcase, filename)
#    
#    def test_EduniErrata4e(self):
#        path = self.test_path
#        testcase = os.path.join('eduni', 'errata-4e')
#        filename = 'errata4e.xml'
#        self._runXMLTestCase(path, testcase, filename)
    
    def _runXMLTestCase(self, path, testcase, filename):
        """Parse and evaluate a given test case."""
        testcase_file = os.path.join(path, testcase, filename)
        xml_doc = etree.parse(testcase_file) 
        tests = xml_doc.xpath('/TESTCASES/TEST') or []
        subtests = xml_doc.xpath('/TESTCASES/TESTCASES/TEST') or []
        tests.extend(subtests)
        for test in tests:
            # skip not standalone documents
            if test.get('ENTITIES') not in ['none', 'parameter']:
                continue
            props = {}
            props['type'] = test.get('TYPE')
            props['entities'] = test.get('ENTITIES')
            props['output'] = test.get('OUTPUT')
            filename = props['uri'] = test.get('URI')
            self._runXMLTest(path, testcase, filename, props)
    
    def _runXMLTest(self, path, testcase, filename, props):
        # skip invalid or not well-formed files
        if props['type'] not in ['valid', 'invalid']:
            return
        test_file = os.path.join(path, testcase, filename)
        data = file(test_file, 'rb').read()
        # XXX: raise invalid
        res = self.env.catalog.addResource('test', 'xml', data)
        self.assertTrue(isinstance(res.document.data, unicode))


def suite():
    return unittest.makeSuite(XMLConformanceTestCase, 'test')

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
