# -*- coding: utf-8 -*-

import unittest

from seishub.exceptions import InvalidParameterError, DuplicateObjectError
from seishub.exceptions import NotFoundError, DeletedObjectError
from seishub.exceptions import InvalidObjectError
from seishub.util.text import hash
from seishub.test import SeisHubEnvironmentTestCase
from seishub.db.util import DbAttributeProxy
from seishub.xmldb.xmldbms import XmlDbManager
from seishub.xmldb.resource import XmlDocument, Resource, newXMLDocument 
from seishub.xmldb.resource import XML_DECLARATION_LENGTH


TEST_XML="""<testml>
<blah1 id="3"><blahblah1>blahblahblah</blahblah1></blah1>
</testml>"""

TEST_XML_MOD="""<testml>
<blah1 id="3"><blahblah1>blahblahblah</blahblah1></blah1>
<newblah>newblah</newblah>
</testml>"""

TEST_BAD_XML = u"""<testml>
<blah1 id="3"></blah1><blahblah1>blahblahblah<foo></blahblah1></foo></blah1>
</testml>"""

class XmlDocumentTest(SeisHubEnvironmentTestCase):
    def testXml_data(self):
        test_res = newXMLDocument(TEST_XML)
        xml_data = test_res.getData()
        self.assertEquals(xml_data, TEST_XML)
        test_res.data = TEST_BAD_XML
        self.assertRaises(InvalidObjectError, test_res.getXml_doc)


class XmlDbManagerTest(SeisHubEnvironmentTestCase):
    def __init__(self, *args, **kwargs):
        super(XmlDbManagerTest,self).__init__(*args, **kwargs)
        # set up test env:
        self.xmldbm = XmlDbManager(self.db)
        self.test_data = TEST_XML
        self.test_data_mod = TEST_XML_MOD
        
#    def _config(self):
#        self.config.set('db', 'verbose', True)
        
    def setUp(self):
        self.test_package = self.env.registry.db_getPackage('test')
        if not self.test_package:
            self.test_package = self.env.registry.db_registerPackage('test')
        self.test_resourcetype = self.env.registry.db_getResourceType('test', 
                                                                      'testml')
        if not self.test_resourcetype:
            self.test_resourcetype = self.env.registry.\
                                     db_registerResourceType('test', 'testml')
        self.vc_resourcetype = self.env.registry.\
                               db_getResourceType('test', 'vcresource')
        if not self.vc_resourcetype:
            self.vc_resourcetype = self.env.registry.\
                                db_registerResourceType('test', 'vcresource', 
                                                        version_control = True)

    def tearDown(self):
        try:
            self.env.registry.\
                db_deleteResourceType(self.test_package.package_id,
                                      self.test_resourcetype.resourcetype_id)
        except:
            print "Warning: Resourcetype %s could not be deleted during tear" \
                  " down." % (self.test_resourcetype.resourcetype_id)
        try:
            self.env.registry.\
                db_deleteResourceType(self.test_package.package_id,
                                      self.vc_resourcetype.resourcetype_id)
        except:
            print "Warning: Resourcetype %s could not be deleted during tear" \
                  " down." % (self.vc_resourcetype.resourcetype_id)
        try:
            self.env.registry.db_deletePackage(self.test_package.package_id)
        except:
            print "Warning: Package %s could not be deleted during tear" \
                  " down." % (self.test_package.package_id)
#            
    def testUnversionedResource(self):
        # add empty resource
        empty = Resource(document = XmlDocument())
        self.assertRaises(InvalidParameterError, self.xmldbm.addResource, empty)
        testres = Resource(self.test_package, self.test_resourcetype, 
                           document = newXMLDocument(self.test_data, 
                                                     uid = 1000))
        otherpackage = self.env.registry.db_registerPackage("otherpackage")
        othertype = self.env.registry.db_registerResourceType("otherpackage", 
                                                              "testml")
        testres2 = Resource(otherpackage, othertype,
                            document = newXMLDocument(self.test_data))
        self.xmldbm.addResource(testres)
        self.xmldbm.addResource(testres2)
        result = self.xmldbm.getResource(testres.package, 
                                         testres.resourcetype, 
                                         testres.id)
        # check lazyness of Resource.data:
        assert isinstance(result.document._data, DbAttributeProxy)
        self.assertEquals(result.name, str(testres.id))
        self.assertEquals(result.document.data, self.test_data)
        self.assertTrue(result.document.meta.datetime)
        self.assertEquals(result.document.meta.size, 
                          len(self.test_data) + XML_DECLARATION_LENGTH)
        self.assertEquals(result.document.meta.hash, 
                          hash(self.test_data))
        self.assertEquals(result.document.meta.uid, 1000)
        self.assertEquals(result.package.package_id, 
                          self.test_package.package_id)
        self.assertEquals(result.resourcetype.resourcetype_id, 
                          self.test_resourcetype.resourcetype_id)
        self.assertEquals(result.resourcetype.version_control, False)
        # modify resource
        modres = Resource(result.package, result.resourcetype, result.id,
                          document = newXMLDocument(self.test_data_mod))
        self.xmldbm.modifyResource(modres)
        result = self.xmldbm.getResource(testres.package, 
                                         testres.resourcetype, 
                                         id = testres.id)
        self.assertEquals(result.document.data, self.test_data_mod)
        # user id is still the same
        self.assertEquals(result.document.meta.uid, 1000)
        self.assertEquals(result.package.package_id, 
                          self.test_package.package_id)
        self.assertEquals(result.resourcetype.resourcetype_id, 
                          self.test_resourcetype.resourcetype_id)
        self.assertEquals(result.resourcetype.version_control, False)
        # delete resource
        self.xmldbm.deleteResource(testres.package, 
                                   testres.resourcetype, 
                                   id = testres.id)
        self.assertRaises(NotFoundError, self.xmldbm.getResource, 
                          testres.package, 
                          testres.resourcetype, 
                          testres.id)
        
        result = self.xmldbm.getResource(testres2.package, 
                                         testres2.resourcetype, 
                                         testres2.id)
        self.assertEquals(result.document.data, self.test_data)
        self.assertEquals(result.document.meta.uid, None)
        self.assertEquals(result.package.package_id, 
                          otherpackage.package_id)
        self.assertEquals(result.resourcetype.resourcetype_id, 
                          othertype.resourcetype_id)
        self.assertEquals(result.resourcetype.version_control, False)
        # try to add a resource with same id
        testres_v = Resource(self.test_package, self.test_resourcetype, 
                                 document = newXMLDocument(self.test_data),
                                 id = result.id)
        self.assertRaises(DuplicateObjectError, self.xmldbm.addResource, 
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
                           document = newXMLDocument(self.test_data))
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
        # modify resource /  a new resource with same id
        testres_v2 = Resource(self.test_package, self.vc_resourcetype, 
                              document = newXMLDocument(self.test_data), 
                              id = result.id)
        self.xmldbm.modifyResource(testres_v2)
        # get latest revision
        result = self.xmldbm.getResource(testres.package, 
                                         testres.resourcetype, 
                                         id = testres.id)
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
                                   id = testres.id)
        # try to get latest revision (deleted)
        self.assertRaises(DeletedObjectError, self.xmldbm.getResource,
                          testres.package, 
                          testres.resourcetype, 
                          id = testres.id)
        # get previous revision
        result = self.xmldbm.getResource(testres.package, 
                                         testres.resourcetype, 
                                         id = testres.id,
                                         revision = 2)
        self.assertEquals(result.revision, 2)
        self.assertEquals(result.document._id, testres_v2.document._id)
        
        # get version history
        revisions = self.xmldbm.getResourceList(self.test_package, 
                                                self.vc_resourcetype,
                                                id = testres.id)
        self.assertEqual(len(revisions), 3)
        self.assertEqual(revisions[0].revision, 1)
        self.assertEqual(revisions[1].revision, 2)
        self.assertEqual(revisions[2].revision, 3)
        
        # delete revision 2
        self.xmldbm.deleteResource(self.test_package, self.vc_resourcetype,
                                   id = testres.id, revision = 2)
        revisions = self.xmldbm.getResourceList(self.test_package, 
                                              self.vc_resourcetype,
                                              id = testres.id)
        self.assertEqual(len(revisions), 2)
        self.assertEqual(revisions[0].revision, 1)
        self.assertEqual(revisions[1].revision, 3)
        
        # revert revision 1
        self.xmldbm.revertResource(self.test_package, self.vc_resourcetype,
                                   revision = 1, id = testres.id, name = None)
        newest = self.xmldbm.getResource(self.test_package, 
                                         self.vc_resourcetype,
                                         id = testres.id)
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
        self.assertRaises(NotFoundError, self.xmldbm.getResource,
                          self.test_package, self.vc_resourcetype, testres.id)
                
        # XXX: BuG: revision counter is not reset on new resources

    def testGetResourceList(self):
        # add some test resources first:
        testres1 = Resource(self.test_package, self.test_resourcetype, 
                            document = newXMLDocument(self.test_data))
        testres2 = Resource(self.test_package, self.test_resourcetype,
                            document = newXMLDocument(self.test_data))
        self.xmldbm.addResource(testres1)
        self.xmldbm.addResource(testres2)
        l = self.xmldbm.getResourceList(self.test_package)
        assert len(l) == 2
        for res in l:
            self.assertEqual(res.package.package_id, 
                             self.test_package.package_id)
            self.assertEqual(res.resourcetype.resourcetype_id, 
                             self.test_resourcetype.resourcetype_id)
        # delete test resource:
        self.xmldbm.deleteResource(testres1.package, 
                                   testres1.resourcetype, 
                                   testres1.id)
        self.xmldbm.deleteResource(testres2.package, 
                                   testres2.resourcetype, 
                                   testres2.id)
       
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