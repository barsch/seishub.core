# -*- coding: utf-8 -*-

import unittest
import os
import inspect
from xml.dom import minidom

from lxml import etree

from seishub.test import SeisHubEnvironmentTestCase
from seishub.util.text import detectXMLEncoding, toUnicode


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
            props = {}
            props['type'] = test.get('TYPE')
            props['entities'] = test.get('ENTITIES')
            props['output'] = test.get('OUTPUT')
            filename = props['uri'] = test.get('URI')
            self._runXMLTest(path, testcase, filename, props)
    
    def _runXMLTest(self, path, testcase, filename, props):
        test_file = os.path.join(path, testcase, filename)
        test_id = os.path.join(testcase, filename)
        
        data = file(test_file, 'r').read()
        
        
        encoding = detectXMLEncoding(data)
        if not encoding:
            encoding = 'utf-8'
        
        try:
            doc = minidom.parseString(data)
        except Exception, e:
            if props['type']!='valid':
                return
            print test_file, e
        
        
#        #check if well formed and valid
#        print encoding
#        parser = etree.XMLParser(encoding=encoding)
#        try:
#            etree.parse(test_file, parser)
#            if props['type']=='valid':
#                return
#            print test_file, props['type']
#        except Exception, e:
#            #if props['type']!='valid':
#            #    return
#            print test_file, props['type'], e
#        #    print 'INVALID:', test_id, '-', e
#        #    return
        
        #test if still invalid or error doc exists at this point
        #if props['type']!='valid':
            #print 'VALID:', test_id, '-',
            #print 'document should not be marked valid:', props['type']
        #    return
        
        # try to add resources
        #try:
        #    res = self.env.catalog.addResource('test', 'xml', toUnicode(data))
        #    if props['type']!='valid':
        #        print test_file, props['type']
        #except Exception, e:
        #    #if props['type']!='valid':
        #    #    return
        #    #print 'ADD RESOURCE:', test_id, '-', e, props['type']
        #    return
        
        
        data = file(test_file, 'r').read()
        try:
            _ = self.env.catalog.addResource('test', 'xml', data)
        except Exception, e:
            print 'ADD RESOURCE:', test_id, '-', e
            return


def suite():
    return unittest.makeSuite(XMLConformanceTestCase, 'test')

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
