# -*- coding: utf-8 -*-

import unittest

from seishub.test import SeisHubEnvironmentTestCase
from seishub.packages.package import PackageWrapper, ResourceTypeWrapper
from seishub.xmldb.errors import AddResourceError, XmlResourceError,\
                                 GetResourceError, ResourceDeletedError
from seishub.xmldb.xmldbms import XmlDbManager
from seishub.xmldb.resource import XmlResource


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

class XmlResourceTest(SeisHubEnvironmentTestCase):
    def testXml_data(self):
        testpackage = PackageWrapper('test')
        testresourcetype = ResourceTypeWrapper('testml', testpackage)
        test_res = XmlResource(testpackage, testresourcetype, TEST_XML)
        xml_data = test_res.getData()
        self.assertEquals(xml_data, TEST_XML)
        self.assertEquals("testml", test_res.info.resourcetype.resourcetype_id)
        
        self.assertRaises(XmlResourceError,
                          test_res.setData,
                          TEST_BAD_XML)


class XmlDbManagerTest(SeisHubEnvironmentTestCase):
    def __init__(self, *args, **kwargs):
        super(XmlDbManagerTest,self).__init__(*args, **kwargs)
        # set up test env:
        self.xmldbm = XmlDbManager(self.db)
        self.test_data = TEST_XML
        
    def setUp(self):
        self.test_package = self.env.registry.db_registerPackage('test')
        self.test_resourcetype = self.env.registry.db_registerResourceType(
                                                              'testml', 'test')

    def tearDown(self):
        self.env.registry.db_deleteResourceType(self.test_package.package_id,
                                       self.test_resourcetype.resourcetype_id)
        self.env.registry.db_deletePackage(self.test_package.package_id)
            
    def testUnversionedResource(self):
        # add empty resource
        empty = XmlResource(self.test_package, self.test_resourcetype,
                            data = "")
        self.assertRaises(AddResourceError, self.xmldbm.addResource, empty)
        
        testres = XmlResource(self.test_package, self.test_resourcetype, 
                              data = self.test_data)
        otherpackage = self.env.registry.db_registerPackage("otherpackage")
        othertype = self.env.registry.db_registerResourceType("testml",
                                                              "otherpackage")
        testres2 = XmlResource(otherpackage, 
                               othertype,
                               data = self.test_data)
        self.xmldbm.addResource(testres)
        self.xmldbm.addResource(testres2)
        result = self.xmldbm.getResource(testres.info.package, 
                                         testres.info.resourcetype, 
                                         testres.info.id)
        self.assertEquals(result.data, self.test_data)
        self.assertEquals(result.info.package.package_id, 
                          self.test_package.package_id)
        self.assertEquals(result.info.resourcetype.resourcetype_id, 
                          self.test_resourcetype.resourcetype_id)
        self.assertEquals(result.info.version_control, False)
        self.xmldbm.deleteResource(testres.info.package, 
                                   testres.info.resourcetype, 
                                   testres.info.id)
        self.assertRaises(GetResourceError, self.xmldbm.getResource, 
                          testres.info.package, 
                          testres.info.resourcetype, 
                          testres.info.id)
        
        result = self.xmldbm.getResource(testres2.info.package, 
                                         testres2.info.resourcetype, 
                                         testres2.info.id)
        self.assertEquals(result.data, self.test_data)
        self.assertEquals(result.info.package.package_id, 
                          otherpackage.package_id)
        self.assertEquals(result.info.resourcetype.resourcetype_id, 
                          othertype.resourcetype_id)
        self.assertEquals(result.info.version_control, False)
        self.xmldbm.deleteResource(testres2.info.package, 
                                   testres2.info.resourcetype, 
                                   testres2.info.id)
        
        # cleanup
        self.env.registry.db_deleteResourceType(otherpackage.package_id,
                                                othertype.resourcetype_id)
        self.env.registry.db_deletePackage(otherpackage.package_id)
        
    def testVersionControlledResource(self):
        testres = XmlResource(self.test_package, self.test_resourcetype, 
                              data = self.test_data, version_control = True)
        self.xmldbm.addResource(testres)
        result = self.xmldbm.getResource(testres.info.package, 
                                         testres.info.resourcetype, 
                                         testres.info.id)
        self.assertEquals(result.data, self.test_data)
        self.assertEquals(result.info.package.package_id, 
                          self.test_package.package_id)
        self.assertEquals(result.info.resourcetype.resourcetype_id, 
                          self.test_resourcetype.resourcetype_id)
        self.assertEquals(result.info.version_control, True)
        self.assertEquals(result.info.revision, 1)
        # add a new resource with same id
        testres_v2 = XmlResource(self.test_package, self.test_resourcetype, 
                                 data = self.test_data, id = result.info.id, 
                                 version_control = True)
        self.xmldbm.addResource(testres_v2)
        # try to add a resource with same id, inactive version control        
        testres_v0 = XmlResource(self.test_package, self.test_resourcetype, 
                                 data = self.test_data, id = result.info.id, 
                                 version_control = False)
        self.assertRaises(AddResourceError, self.xmldbm.addResource, 
                          testres_v0)
        # get latest revision
        result = self.xmldbm.getResource(testres.info.package, 
                                         testres.info.resourcetype, 
                                         testres.info.id)
        self.assertEquals(result.info.revision, 2)
        self.assertEquals(result.resource_id, testres_v2.resource_id)
        # get previous revision
        result = self.xmldbm.getResource(testres.info.package, 
                                         testres.info.resourcetype, 
                                         testres.info.id,
                                         revision = 1)
        self.assertEquals(result.info.revision, 1)
        self.assertEquals(result.resource_id, testres.resource_id)
        # delete resource
        self.xmldbm.deleteResource(testres.info.package, 
                                   testres.info.resourcetype, 
                                   testres.info.id)
        # try to get latest revision (deleted)
        self.assertRaises(ResourceDeletedError, self.xmldbm.getResource,
                          testres.info.package, 
                          testres.info.resourcetype, 
                          testres.info.id)
        # get previous revision
        result = self.xmldbm.getResource(testres.info.package, 
                                         testres.info.resourcetype, 
                                         testres.info.id,
                                         revision = 2)
        self.assertEquals(result.info.revision, 2)
        self.assertEquals(result.resource_id, testres_v2.resource_id)
                
        # XXX: remove made db entries / BuG: revision counter is not reset on new resources

#    def testGetResourceList(self):
#        # add some test resources first:
#        testres1 = XmlResource(self.test_package, self.test_resourcetype, 
#                               data = self.test_data)
#        testres2 = XmlResource(self.test_package, self.test_resourcetype,
#                               data = self.test_data)
#        self.xmldbm.addResource(testres1)
#        self.xmldbm.addResource(testres2)
#        
#        l = self.xmldbm.getResourceList(self.test_package)
#        for res in l:
#            self.assertEqual(res.package_id, self.test_package)
#            self.assertEqual(res.resourcetype_id, self.test_resourcetype)
#        # delete test resource:
#        self.xmldbm.deleteResource(testres1.info.package_id, 
#                                   testres1.info.resourcetype_id, 
#                                   testres1.info.id)
#        self.xmldbm.deleteResource(testres2.info.package_id, 
#                                   testres2.info.resourcetype_id, 
#                                   testres2.info.id)
       
#    def testResourceExists(self):
#        testres1 = XmlResource(self.test_package, self.test_resourcetype,
#                               data=self.test_data)
#        self.xmldbm.addResource(testres1)
#        self.assertEquals(self.xmldbm.resourceExists(self.test_package, self.test_resourcetype,
#                                                     testres1.info.id), True)
#        self.assertEquals(self.xmldbm.resourceExists('not', 'there',
#                                                     testres1.info.id), False)
#        self.xmldbm.deleteResource(testres1.info.package_id, 
#                                   testres1.info.resourcetype_id, 
#                                   testres1.info.id)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(XmlResourceTest, 'test'))
    suite.addTest(unittest.makeSuite(XmlDbManagerTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')