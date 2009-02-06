# -*- coding: utf-8 -*-

from seishub.db.orm import DbAttributeProxy
from seishub.exceptions import InvalidObjectError, InvalidParameterError, \
    DuplicateObjectError, NotFoundError
from seishub.test import SeisHubEnvironmentTestCase
from seishub.util.text import hash
from seishub.xmldb.resource import XML_DECLARATION_LENGTH, XmlDocument, \
    Resource, newXMLDocument
from seishub.xmldb.xmldbms import XmlDbManager
import unittest


TEST_XML="""<testml>
<blah1 id="3"><blahblah1>blahblahblah%s</blahblah1></blah1>
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
    
    def setUp(self):
        self.xmldbm = XmlDbManager(self.db)
        self.test_data = TEST_XML
        self.test_data_mod = TEST_XML_MOD
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
        #======================================================================
        # addResource()
        #======================================================================
        # add empty resource
        empty = Resource(document = XmlDocument())
        self.assertRaises(InvalidParameterError, self.xmldbm.addResource, empty)
        res1 = Resource(self.test_resourcetype, 
                        document = newXMLDocument(self.test_data, 
                                                  uid = 1000))
        otherpackage = self.env.registry.db_registerPackage("otherpackage")
        othertype = self.env.registry.db_registerResourceType("otherpackage", 
                                                              "testml")
        res2 = Resource(othertype, document = newXMLDocument(self.test_data))
        self.xmldbm.addResource(res1)
        self.xmldbm.addResource(res2)
        
        # try to add a resource with same id
        res3 = Resource(self.test_resourcetype, 
                        document = newXMLDocument(self.test_data),
                        id = res2.id)
        self.assertRaises(DuplicateObjectError, self.xmldbm.addResource, res3)
        
        #======================================================================
        # getResource()
        #======================================================================
        result = self.xmldbm.getResource(id = res1.id)
        # check lazyness of Resource.data:
        assert isinstance(result.document._data, DbAttributeProxy)
        self.assertEquals(result.name, str(res1.id))
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
        
        result = self.xmldbm.getResource(id = res2.id)
        self.assertEquals(result.document.data, self.test_data)
        self.assertEquals(result.document.meta.uid, None)
        self.assertEquals(result.package.package_id, 
                          otherpackage.package_id)
        self.assertEquals(result.resourcetype.resourcetype_id, 
                          othertype.resourcetype_id)
        self.assertEquals(result.resourcetype.version_control, False)

        #======================================================================
        # modifyResource()
        #======================================================================
        modres = Resource(res1.resourcetype, res1.id,
                          document = newXMLDocument(self.test_data_mod))
        self.xmldbm.modifyResource(res1, modres)
        result = self.xmldbm.getResource(res1.package.package_id,
                                         res1.resourcetype.resourcetype_id, 
                                         id = res1.id)
        self.assertEquals(result.document.data, self.test_data_mod)
        # user id is still the same
        self.assertEquals(result.document.meta.uid, 1000)
        self.assertEquals(result.package.package_id, 
                          self.test_package.package_id)
        self.assertEquals(result.resourcetype.resourcetype_id, 
                          self.test_resourcetype.resourcetype_id)
        self.assertEquals(result.resourcetype.version_control, False)
        
        #======================================================================
        # deleteResource()
        #======================================================================
        # by object
        self.xmldbm.deleteResource(res1)
        self.assertRaises(NotFoundError, self.xmldbm.getResource, id = res1.id)
        # add again
        self.xmldbm.addResource(res1)
        # there again?
        self.assertTrue(self.xmldbm.getResource(id = res1.id))
        # now by resource_id
        self.xmldbm.deleteResource(resource_id = res1._id)
        self.assertRaises(NotFoundError, self.xmldbm.getResource, id = res1.id)
        # now for res2
        self.xmldbm.deleteResource(res2)
        self.assertRaises(NotFoundError, self.xmldbm.getResource, id = res2.id)
        # cleanup
        self.env.registry.db_deleteResourceType(otherpackage.package_id,
                                                othertype.resourcetype_id)
        self.env.registry.db_deletePackage(otherpackage.package_id)
    
    def testVersionControlledResource(self):
        testres = Resource(self.vc_resourcetype, 
                           document = newXMLDocument(self.test_data))
        self.xmldbm.addResource(testres)
        result = self.xmldbm.getResource(id = testres.id)
        self.assertEquals(result.document.data, self.test_data)
        self.assertEquals(result.package.package_id, 
                          self.test_package.package_id)
        self.assertEquals(result.resourcetype.resourcetype_id, 
                          self.vc_resourcetype.resourcetype_id)
        self.assertEquals(result.resourcetype.version_control, True)
        self.assertEquals(result.document.revision, 1)
        # modify resource /  a new resource with same id
        testres_v2 = Resource(self.vc_resourcetype, 
                              document = newXMLDocument(self.test_data % 'r2'), 
                              id = result.id)
        self.xmldbm.modifyResource(testres, testres_v2)
        # get latest revision
        rev2 = self.xmldbm.getResource(testres.package.package_id,
                                       testres.resourcetype.resourcetype_id, 
                                       id = testres.id)
        self.assertEquals(rev2.document.revision, 2)
        self.assertEquals(rev2.document._id, 
                          testres_v2.document._id)
        self.assertEquals(rev2.document.data, self.test_data % 'r2')

        # get previous revision
        rev1 = self.xmldbm.getResource(testres.package.package_id,
                                       testres.resourcetype.resourcetype_id, 
                                       id = testres.id,
                                       revision = 1)
        self.assertEquals(rev1.document.revision, 1)
        self.assertEquals(rev1._id, rev2._id)
        self.assertEquals(rev1.document.data, self.test_data)
        
        # get version history
        res2 = self.xmldbm.getResourceHistory(id = testres.id)
        self.assertEqual(len(res2.document), 2)
        self.assertEqual(res2.document[0].revision, 1)
        self.assertEqual(res2.document[0].data, self.test_data)
        self.assertEqual(res2.document[1].revision, 2)
        self.assertEqual(res2.document[1].data, self.test_data % 'r2')
        
        # add a third revision
        testres_v3 = Resource(self.vc_resourcetype, 
                              document = newXMLDocument(self.test_data % 'r3'))
        self.xmldbm.modifyResource(testres, testres_v3)
        res = self.xmldbm.getResourceHistory(id = testres.id)
        self.assertEqual(len(res.document), 3)
        
        # delete revision 2
        self.xmldbm.deleteRevision(res2, 2)
        self.assertRaises(NotFoundError, self.xmldbm.getResource,
                          testres.package.package_id, 
                          testres.resourcetype.resourcetype_id, None, 2, None, 
                          testres.id)
        res = self.xmldbm.getResourceHistory(id = testres.id)
        self.assertEqual(len(res.document), 2)
        # revert revision 1
        self.xmldbm.revertResource(id = testres.id, revision = 1)
        res = self.xmldbm.getResource(id = testres.id)
        self.assertEquals(res.document.revision, 1)
        self.assertEquals(res.document.data, self.test_data)
        # only one revision is left => res.document is not a list
        res = self.xmldbm.getResourceHistory(id = testres.id)
        self.assertEqual(res.document.revision, 1)
        # delete resource
        self.xmldbm.deleteResource(testres)
        # try to get latest revision (deleted)
        self.assertRaises(NotFoundError, self.xmldbm.getResource, 
                          id = testres.id)
        # XXX: BuG: revision counter is not reset on new resources
    
    def testGetResourceList(self):
        # add some test resources first:
        res1 = Resource(self.test_resourcetype, 
                            document = newXMLDocument(self.test_data))
        res2 = Resource(self.test_resourcetype,
                            document = newXMLDocument(self.test_data))
        self.xmldbm.addResource(res1)
        self.xmldbm.addResource(res2)
        l = self.xmldbm.getAllResources(self.test_package.package_id)
        assert len(l) == 2
        for res in l:
            self.assertEqual(res.package.package_id, 
                             self.test_package.package_id)
            self.assertEqual(res.resourcetype.resourcetype_id, 
                             self.test_resourcetype.resourcetype_id)
        # delete test resource:
        self.xmldbm.deleteResource(res1)
        self.xmldbm.deleteResource(res2)
       
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