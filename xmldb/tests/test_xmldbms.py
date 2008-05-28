# -*- coding: utf-8 -*-

import unittest

from seishub.test import SeisHubTestCase
from seishub.xmldb.xmldbms import XmlDbManager
from seishub.xmldb.xmlresource import XmlResource, XmlResourceError
from seishub.xmldb.defaults import DEFAULT_PREFIX, RESOURCE_TABLE, \
                                   RESOURCE_META_TABLE


TEST_XML="""<?xml version="1.0"?>
<testml>
<blah1 id="3"><blahblah1>blahblahblah</blahblah1></blah1>
</testml>
"""
TEST_BAD_XML="""<?xml version="1.0"?>
<testml>
<blah1 id="3"></blah1><blahblah1>blahblahblah<foo></blahblah1></foo></blah1>
</testml>
"""
TEST_PACKAGE = 'testpackage'
TEST_RESOURCETYPE = 'testml'


class XmlResourceTest(SeisHubTestCase):
    def testXml_data(self):
        test_res = XmlResource('test','testml', TEST_XML)
        xml_data = test_res.getData()
        self.assertEquals(xml_data,TEST_XML)
        self.assertEquals("testml",test_res.info.resourcetype_id)
        
        self.assertRaises(XmlResourceError,
                          test_res.setData,
                          TEST_BAD_XML)


class XmlDbManagerTest(SeisHubTestCase):
    def setUp(self):
        super(XmlDbManagerTest,self).setUp()
        # set up test env:
        

        self.xmldbm=XmlDbManager(self.db)
        self.test_data = TEST_XML
    

    def testAddGetDeleteResource(self):
        testres = XmlResource(TEST_PACKAGE, TEST_RESOURCETYPE, 
                              xml_data = self.test_data)
        testres2=XmlResource("otherpackage", TEST_RESOURCETYPE,
                             xml_data = self.test_data)
        self.xmldbm.addResource(testres)
        self.xmldbm.addResource(testres2)
        result = self.xmldbm.getResource(testres.uid)
        self.assertEquals(result.data, self.test_data)
        self.assertEquals(result.info.package_id, TEST_PACKAGE)
        self.assertEquals(result.info.resourcetype_id, TEST_RESOURCETYPE)
        self.xmldbm.deleteResource(testres.uid)
        
        result = self.xmldbm.getResource(testres2.uid)
        self.assertEquals(result.data, self.test_data)
        self.assertEquals(result.info.package_id, "otherpackage")
        self.assertEquals(result.info.resourcetype_id, TEST_RESOURCETYPE)
        self.xmldbm.deleteResource(testres2.uid)
    
    def testGetResourceList(self):
        # add some test resources first:
        testres1=XmlResource(TEST_PACKAGE, TEST_RESOURCETYPE, 
                             xml_data=self.test_data)
        testres2=XmlResource(TEST_PACKAGE, TEST_RESOURCETYPE,
                             xml_data=self.test_data)
        self.xmldbm.addResource(testres1)
        self.xmldbm.addResource(testres2)
        
        #print self.xmldbm.getUriList()
        #TODO: check results
        # delete test resource:
        self.xmldbm.deleteResource(testres1._id)
        self.xmldbm.deleteResource(testres2._id)
        
    def testResourceExists(self):
        testres1=XmlResource(TEST_PACKAGE, TEST_RESOURCETYPE,
                             xml_data=self.test_data)
        self.xmldbm.addResource(testres1)
        self.assertEquals(self.xmldbm.resourceExists(TEST_PACKAGE, TEST_RESOURCETYPE,
                                                     testres1._id), True)
        self.assertEquals(self.xmldbm.resourceExists('not', 'there',
                                                     testres1._id), False)
        self.xmldbm.deleteResource(testres1._id)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(XmlResourceTest, 'test'))
    suite.addTest(unittest.makeSuite(XmlDbManagerTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')