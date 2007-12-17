# -*- coding: utf-8 -*-

from twisted.trial.unittest import TestCase
from twisted.enterprise import adbapi

from seishub.util.libxmlwrapper import InvalidXmlDataError
from seishub.xmldb.xmldbms import XmlDbManager
from seishub.xmldb.xmlresource import XmlResource
from seishub.defaults import DB_DRIVER,DB_ARGS
from seishub.defaults import DEFAULT_PREFIX,RESOURCE_TABLE,URI_TABLE

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


class XmlResourceTest(TestCase):
    def testXml_data(self):
        test_res=XmlResource()
        test_res.setData(TEST_XML)
        xml_data=test_res.getData()
        self.assertEquals(xml_data,TEST_XML)
        
        self.assertRaises(InvalidXmlDataError,
                          test_res.setData,
                          TEST_BAD_XML)


class XmlDbManagerTest(TestCase):
    def setUp(self):
        self.dbConnection=adbapi.ConnectionPool(DB_DRIVER,**DB_ARGS)
        self.xmldbm=XmlDbManager(self.dbConnection)
        self.test_data=TEST_XML
        self.test_uri=TEST_URI
    
    def testAddResource(self):
        testres=XmlResource(xml_data=self.test_data,uri=self.test_uri)
        
        def _assertResults(result,assertEquals,test_data):
            assertEquals(result[0][0],test_data),test_data

        def _checkResults(self,dbConnection,test_uri,test_data,assertEquals):
            db_strings={'res_tab':DEFAULT_PREFIX+'_'+RESOURCE_TABLE,
                        'uri_tab':DEFAULT_PREFIX+'_'+URI_TABLE,
                        'uri':test_uri}
            query="""SELECT xml_data FROM %(res_tab)s,%(uri_tab)s
                WHERE(%(res_tab)s.id=%(uri_tab)s.res_id
                AND %(uri_tab)s.uri='%(uri)s')""" % (db_strings)
            d=dbConnection.runQuery(query) \
              .addCallback(_assertResults,assertEquals,test_data)
            return d
            
        d=self.xmldbm.addResource(testres)
        d.addCallback(_checkResults,
                      self.dbConnection,
                      self.test_uri, self.test_data,
                      self.assertEquals)
        
        return d
    
    def testGetAndDeleteResource(self):
        def _deleteResource(result,deleteResource,test_uri):
            d=deleteResource(test_uri)
            return d
        
        def _assertResults(result,assertEquals,test_uri,test_data):
            assertEquals(result.getData(),test_data)
            assertEquals(result.getUri(),test_uri)
        
        d=self.xmldbm.getResource(self.test_uri) \
            .addCallback(_assertResults,
                         self.assertEquals,self.test_uri,self.test_data) \
            .addCallback(_deleteResource,
                         self.xmldbm.deleteResource,self.test_uri)
        return d
    
    def testResolveUri(self):
        # add a test res first:
        testres=XmlResource(xml_data=self.test_data,uri=self.test_uri)
        d=self.xmldbm.addResource(testres)
        def Foo(res):
            print res
        d.addCallback(lambda foo: self.xmldbm._resolveUri(self.test_uri))
        d.addCallback(self.assertTrue)
        
        # delete test resource:
        d.addCallback(lambda foo: self.xmldbm.deleteResource(self.test_uri))
        
        return d
    

        