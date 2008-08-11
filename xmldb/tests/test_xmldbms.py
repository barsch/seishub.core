# -*- coding: utf-8 -*-

import unittest

from seishub.test import SeisHubEnvironmentTestCase
from seishub.xmldb.errors import AddResourceError, XmlResourceError,\
                                 GetResourceError, ResourceDeletedError
from seishub.xmldb.xmldbms import XmlDbManager
from seishub.xmldb.resource import XmlDocument, Resource


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

class XmlDocumentTest(SeisHubEnvironmentTestCase):
    def testXml_data(self):
        test_res = XmlDocument(TEST_XML)
        xml_data = test_res.getData()
        self.assertEquals(xml_data, TEST_XML)
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
        self.vc_resourcetype = self.env.registry.db_registerResourceType(
                                                        'vcresource', 'test',
                                                        version_control = True)

    def tearDown(self):
        self.env.registry.db_deleteResourceType(self.test_package.package_id,
                                       self.test_resourcetype.resourcetype_id)
        self.env.registry.db_deleteResourceType(self.test_package.package_id,
                                          self.vc_resourcetype.resourcetype_id)
        self.env.registry.db_deletePackage(self.test_package.package_id)
            
    def testUnversionedResource(self):
        # add empty resource
        empty = Resource(document = XmlDocument())
        self.assertRaises(AddResourceError, self.xmldbm.addResource, empty)
        testres = Resource(self.test_package, self.test_resourcetype, 
                           document = XmlDocument(self.test_data))
        otherpackage = self.env.registry.db_registerPackage("otherpackage")
        othertype = self.env.registry.db_registerResourceType("testml",
                                                              "otherpackage")
        testres2 = Resource(otherpackage, othertype,
                            document = XmlDocument(self.test_data))
        self.xmldbm.addResource(testres)
        self.xmldbm.addResource(testres2)
        result = self.xmldbm.getResource(testres.package, 
                                         testres.resourcetype, 
                                         testres.id)
        self.assertEquals(result.document.data, self.test_data)
        self.assertEquals(result.package.package_id, 
                          self.test_package.package_id)
        self.assertEquals(result.resourcetype.resourcetype_id, 
                          self.test_resourcetype.resourcetype_id)
        self.assertEquals(result.resourcetype.version_control, False)
        self.xmldbm.deleteResource(testres.package, 
                                   testres.resourcetype, 
                                   testres.id)
        self.assertRaises(GetResourceError, self.xmldbm.getResource, 
                          testres.package, 
                          testres.resourcetype, 
                          testres.id)
        
        result = self.xmldbm.getResource(testres2.package, 
                                         testres2.resourcetype, 
                                         testres2.id)
        self.assertEquals(result.document.data, self.test_data)
        self.assertEquals(result.package.package_id, 
                          otherpackage.package_id)
        self.assertEquals(result.resourcetype.resourcetype_id, 
                          othertype.resourcetype_id)
        self.assertEquals(result.resourcetype.version_control, False)
        # try to add a resource with same id
        testres_v = Resource(self.test_package, self.test_resourcetype, 
                                 document = XmlDocument(self.test_data),
                                 id = result.id)
        self.assertRaises(AddResourceError, self.xmldbm.addResource, 
                          testres_v)
        self.xmldbm.deleteResource(testres2.package, 
                                   testres2.resourcetype, 
                                   testres2.id)
        
        # cleanup
        self.env.registry.db_deleteResourceType(otherpackage.package_id,
                                                othertype.resourcetype_id)
        self.env.registry.db_deletePackage(otherpackage.package_id)
        
    def testVersionControlledResource(self):
        testres = Resource(self.test_package, self.vc_resourcetype, 
                           document = XmlDocument(self.test_data))
        self.xmldbm.addResource(testres)
        result = self.xmldbm.getResource(testres.package, 
                                         testres.resourcetype, 
                                         testres.id)
        self.assertEquals(result.document.data, self.test_data)
        self.assertEquals(result.package.package_id, 
                          self.test_package.package_id)
        self.assertEquals(result.resourcetype.resourcetype_id, 
                          self.vc_resourcetype.resourcetype_id)
        self.assertEquals(result.resourcetype.version_control, True)
        self.assertEquals(result.revision, 1)
        # add a new resource with same id
        testres_v2 = Resource(self.test_package, self.vc_resourcetype, 
                              document = XmlDocument(self.test_data), 
                              id = result.id)
        self.xmldbm.addResource(testres_v2)
        # get latest revision
        result = self.xmldbm.getResource(testres.package, 
                                         testres.resourcetype, 
                                         testres.id)
        self.assertEquals(result.revision, 2)
        self.assertEquals(result.document._id, 
                          testres_v2.document._id)
        # get previous revision
        result = self.xmldbm.getResource(testres.package, 
                                         testres.resourcetype, 
                                         testres.id,
                                         revision = 1)
        self.assertEquals(result.revision, 1)
        self.assertEquals(result.document._id, testres.document._id)
            
        # delete resource
        self.xmldbm.deleteResource(testres.package, 
                                   testres.resourcetype, 
                                   testres.id)
        # try to get latest revision (deleted)
        self.assertRaises(ResourceDeletedError, self.xmldbm.getResource,
                          testres.package, 
                          testres.resourcetype, 
                          testres.id)
        # get previous revision
        result = self.xmldbm.getResource(testres.package, 
                                         testres.resourcetype, 
                                         testres.id,
                                         revision = 2)
        self.assertEquals(result.revision, 2)
        self.assertEquals(result.document._id, testres_v2.document._id)
        
        # get version history
        revisions = self.xmldbm.getResourceList(self.test_package, 
                                              self.vc_resourcetype,
                                              testres.id)
        self.assertEqual(len(revisions), 3)
        self.assertEqual(revisions[0].revision, 1)
        self.assertEqual(revisions[1].revision, 2)
        self.assertEqual(revisions[2].revision, 3)
        
        # delete revision 2
        self.xmldbm.deleteResource(self.test_package, self.vc_resourcetype,
                                   testres.id, 2)
        revisions = self.xmldbm.getResourceList(self.test_package, 
                                              self.vc_resourcetype,
                                              testres.id)
        self.assertEqual(len(revisions), 2)
        self.assertEqual(revisions[0].revision, 1)
        self.assertEqual(revisions[1].revision, 3)
        
        # revert revision 1
        self.xmldbm.revertResource(self.test_package, self.vc_resourcetype,
                                   testres.id, 1)
        newest = self.xmldbm.getResource(self.test_package, 
                                         self.vc_resourcetype,
                                         testres.id)
        self.assertEqual(newest.revision, 4)
        self.assertEqual(newest.document._id, testres.document._id)
        
        # delete revision 3 (resource deleted marker)
        self.xmldbm.deleteResource(self.test_package, self.vc_resourcetype,
                                   testres.id, 3)
        revisions = self.xmldbm.getResourceList(self.test_package, 
                                                self.vc_resourcetype,
                                                testres.id)
        self.assertEqual(len(revisions), 2)
        self.assertEqual(revisions[0].revision, 1)
        self.assertEqual(revisions[1].revision, 4)
        
        # delete version history
        self.xmldbm.deleteResources(self.test_package, 
                                    self.vc_resourcetype,
                                    testres.id)
        self.assertRaises(GetResourceError, self.xmldbm.getResource,
                          self.test_package, self.vc_resourcetype, testres.id)
                
        # XXX: BuG: revision counter is not reset on new resources

#    def testGetResourceList(self):
#        # add some test resources first:
#        testres1 = XmlDocument(self.test_package, self.test_resourcetype, 
#                               data = self.test_data)
#        testres2 = XmlDocument(self.test_package, self.test_resourcetype,
#                               data = self.test_data)
#        self.xmldbm.addResource(testres1)
#        self.xmldbm.addResource(testres2)
#        
#        l = self.xmldbm.getResourceList(self.test_package)
#        for res in l:
#            self.assertEqual(res.package_id, self.test_package)
#            self.assertEqual(res.resourcetype_id, self.test_resourcetype)
#        # delete test resource:
#        self.xmldbm.deleteResource(testres1.package_id, 
#                                   testres1.resourcetype_id, 
#                                   testres1.id)
#        self.xmldbm.deleteResource(testres2.package_id, 
#                                   testres2.resourcetype_id, 
#                                   testres2.id)
       
#    def testResourceExists(self):
#        testres1 = XmlDocument(self.test_package, self.test_resourcetype,
#                               data=self.test_data)
#        self.xmldbm.addResource(testres1)
#        self.assertEquals(self.xmldbm.resourceExists(self.test_package, self.test_resourcetype,
#                                                     testres1.id), True)
#        self.assertEquals(self.xmldbm.resourceExists('not', 'there',
#                                                     testres1.id), False)
#        self.xmldbm.deleteResource(testres1.package_id, 
#                                   testres1.resourcetype_id, 
#                                   testres1.id)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(XmlDocumentTest, 'test'))
    suite.addTest(unittest.makeSuite(XmlDbManagerTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')