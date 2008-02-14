# -*- coding: utf-8 -*-

from seishub.test import SeisHubTestCase
from seishub.xmldb.xmldbms import XmlDbManager
from seishub.xmldb.xmlresource import XmlResource, XmlResourceError
from seishub.xmldb.defaults import DEFAULT_PREFIX,RESOURCE_TABLE,URI_TABLE

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
TEST_URI='localhost/testml/blah3'


class XmlResourceTest(SeisHubTestCase):
    def testXml_data(self):
        test_res=XmlResource()
        test_res.setData(TEST_XML)
        xml_data=test_res.getData()
        self.assertEquals(xml_data,TEST_XML)
        self.assertEquals("testml",test_res.getResource_type())
        
        self.assertRaises(XmlResourceError,
                          test_res.setData,
                          TEST_BAD_XML)


class XmlDbManagerTest(SeisHubTestCase):
    def setUp(self):
        super(XmlDbManagerTest,self).setUp()
        # set up test env:
        

        self.xmldbm=XmlDbManager(self.db)
        self.test_data=TEST_XML
        self.test_uri=TEST_URI
    
    def testAddResource(self):
        testres=XmlResource(xml_data=self.test_data,uri=self.test_uri)
        self.xmldbm.addResource(testres)
        db_strings={'res_tab':DEFAULT_PREFIX+RESOURCE_TABLE,
                    'uri_tab':DEFAULT_PREFIX+URI_TABLE,
                    'uri':self.test_uri}
        query = """SELECT data FROM %(res_tab)s,%(uri_tab)s
                WHERE(%(res_tab)s.id=%(uri_tab)s.res_id
                AND %(uri_tab)s.uri='%(uri)s')""" % (db_strings)
        res = self.db.engine.execute(query).fetchall()
        self.assertEquals(res[0][0],self.test_data)
        self.xmldbm.deleteResource(self.test_uri)
        
    
    def testGetAndDeleteResource(self):
        testres=XmlResource(xml_data=self.test_data,uri=self.test_uri)
        self.xmldbm.addResource(testres)
        result = self.xmldbm.getResource(self.test_uri)
        self.assertEquals(result.getData(),self.test_data)
        self.assertEquals(result.getUri(),self.test_uri)
        res = self.xmldbm.deleteResource(self.test_uri)
        self.assertTrue(res)
    
    def testResolveUri(self):
        # add a test res first:
        testres=XmlResource(xml_data=self.test_data,uri=self.test_uri)
        self.xmldbm.addResource(testres)

        id = self.xmldbm._resolveUri(self.test_uri)
        self.assertTrue(id)
        
        # delete test resource:
        self.xmldbm.deleteResource(self.test_uri)
    
    def testGetUriList(self):
        # add some test resorces first:
        testres1=XmlResource(xml_data=self.test_data,uri=self.test_uri)
        testres2=XmlResource(xml_data=self.test_data,uri=self.test_uri+'/2')
        self.xmldbm.addResource(testres1)
        self.xmldbm.addResource(testres2)
        
        #print self.xmldbm.getUriList()
        #TODO: check results
        # delete test resource:
        self.xmldbm.deleteResource(self.test_uri)
        self.xmldbm.deleteResource(self.test_uri+'/2')
        