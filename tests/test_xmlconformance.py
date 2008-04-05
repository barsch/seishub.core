# -*- coding: utf-8 -*-

import unittest
import os
import inspect

from lxml import etree

from seishub.test import SeisHubTestCase


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
    
    def testOasis(self):
        path = self.test_path
        testcase = 'oasis'
        filename = 'oasis.xml'
        self._runXMLTestCase(path, testcase, filename)
    
    def testEduniXML11(self):
        path = self.test_path
        testcase = os.path.join('eduni', 'xml-1.1')
        filename = 'xml11.xml'
        self._runXMLTestCase(path, testcase, filename)
    
    def testEduniErrata4e(self):
        path = self.test_path
        testcase = os.path.join('eduni', 'errata-4e')
        filename = 'errata4e.xml'
        self._runXMLTestCase(path, testcase, filename)
    
    def _runXMLTestCase(self, path, testcase, filename):
        """Parse and evaluate a given test case."""
        testcase_file = os.path.join(path, testcase, filename)
        xml_doc = etree.parse(testcase_file) 
        tests = xml_doc.xpath('/TESTCASES/TEST')
        for test in tests:
            # skip not standalone documents
            if test.get('ENTITIES') not in ['none', 'parameter']:
                continue
            # skip invalid documents
            if test.get('TYPE')!='valid':
                continue
            props = {}
            props['type'] = test.get('TYPE')
            props['entities'] = test.get('ENTITIES')
            props['output'] = test.get('OUTPUT')
            filename = props['uri'] = test.get('URI')
            self._runXMLTest(path, testcase, filename, props)
    
    def _runXMLTest(self, path, testcase, filename, props):
        test_file = os.path.join(path, testcase, filename)
        test_id = os.path.join(testcase, filename)
        
        #check if well formed and valid
        parser = etree.XMLParser(dtd_validation=True)
        try:
            etree.parse(test_file, parser)
        except etree.XMLSyntaxError, e:
            if props['type']!='valid':
                return
            #print 'INVALID:', test_id, '-', e
            return
        
        #test if still invalid or error doc exists at this point
        if props['type']!='valid':
            #print 'VALID:', test_id, '-',
            #print 'document should not be marked valid:', props['type']
            return
        
        # try to add resources
        data = file(test_file, 'r').read()
        try:
            res = self.env.catalog.newXmlResource('/test/'+props['uri'], data)
        except Exception, e:
            print 'CREATE RESOURCE:', test_id, '-', e
            return
        try:
            self.env.catalog.addResource(res)
        except Exception, e:
            print 'ADD RESOURCE:', test_id, '-', e
            return


def suite():
    return unittest.makeSuite(XMLConformanceTestCase, 'test')

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
