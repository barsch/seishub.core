# -*- coding: utf-8 -*-

import unittest
import os
import inspect

from sqlalchemy.sql import and_ #@UnresolvedImport

from seishub.test import SeisHubEnvironmentTestCase
from seishub.exceptions import NotFoundError, DuplicateObjectError
from seishub.xmldb.xmlindexcatalog import XmlIndexCatalog
from seishub.xmldb.xmldbms import XmlDbManager
from seishub.xmldb.index import XmlIndex, DATETIME_INDEX
from seishub.xmldb.resource import Resource, newXMLDocument
from seishub.xmldb.defaults import index_def_tab, DEFAULT_PREFIX, \
                                   INDEX_DEF_TABLE
from seishub.xmldb.xpath import XPathQuery


RAW_XML1="""<station rel_uri="bern">
    <station_code>BERN</station_code>
    <chan_code>1</chan_code>
    <stat_type>0</stat_type>
    <lon>12.51200</lon>
    <lat>50.23200</lat>
    <stat_elav>0.63500</stat_elav>
</station>"""

RAW_XML2 = """<station rel_uri="genf">
    <station_code>GENF</station_code>
    <chan_code>1</chan_code>
    <stat_type>0</stat_type>
    <lon>22.51200</lon>
    <lat>55.23200</lat>
    <stat_elav>0.73500</stat_elav>
    <XY>
        <paramXY>2.5</paramXY>
        <paramXY>0</paramXY>
        <paramXY>99</paramXY>
    </XY>
</station>"""

RAW_XML3 = """<?xml version="1.0"?>
<testml>
<blah1 id="3"><blahblah1>blahblahblah</blahblah1></blah1>
</testml>
"""

URI1 = "/real/bern"
URI2 = "/fake/genf"
URI3 = "/testml/res1"

IDX1 = "/testpackage/station/station/lon"
IDX2 = "/testpackage/station/station/lat"
IDX3 = "/testpackage/testml/testml/blah1/@id"
IDX4 = "/testpackage/station/station/XY/paramXY"

so_tests = ['so1.xml','so2.xml','so3.xml','so4.xml','so5.xml']
so_indexes = ['/sortordertests/sotest/sortorder/int1', 
              '/sortordertests/sotest/sortorder/int2', 
              '/sortordertests/sotest/sortorder/str1', 
              '/sortordertests/sotest/sortorder/str2']

class XmlIndexCatalogTest(SeisHubEnvironmentTestCase):
    #TODO: testGetIndexes
    # last_id = 0
    # test_xpath = "/station/XY/paramXY"
    # test_uri="/stations/bern"

    def __init__(self, *args, **kwargs):
        SeisHubEnvironmentTestCase.__init__(self, *args,**kwargs)
        self.catalog = self.env.catalog.index_catalog
        self.so_ids = list()

    def setUp(self):
        self.pkg1 = self.env.registry.db_registerPackage("testpackage")
        self.rt1 = self.env.registry.db_registerResourceType("testpackage",
                                                             "station")
        self.rt2 = self.env.registry.db_registerResourceType('testpackage',
                                                             'testml')
        self.rt3 = self.env.registry.db_registerResourceType('testpackage',
                                                             'testtype')
        self.pkg2 = self.env.registry.db_registerPackage("sortordertests")
        self.rt4 = self.env.registry.db_registerResourceType("sortordertests",
                                                             'sotest')

    def tearDown(self):
        self.env.registry.db_deleteResourceType("testpackage", "station")
        self.env.registry.db_deleteResourceType("testpackage", 'testml')
        self.env.registry.db_deleteResourceType("testpackage", 'testtype')
        self.env.registry.db_deletePackage("testpackage")
        self.env.registry.db_deleteResourceType("sortordertests", 'sotest')
        self.env.registry.db_deletePackage("sortordertests")

    def _setup_testdata(self):
        # create us a small test catalog
        self.res1 = self.env.catalog.addResource(self.pkg1.package_id, 
                                                 self.rt1.resourcetype_id, 
                                                 RAW_XML1)
        self.res2 = self.env.catalog.addResource(self.pkg1.package_id, 
                                                 self.rt1.resourcetype_id, 
                                                 RAW_XML2)
        self.res3 = self.env.catalog.addResource(self.pkg1.package_id, 
                                                 self.rt2.resourcetype_id, 
                                                 RAW_XML3)
        self.env.catalog.registerIndex(xpath = IDX1)
        self.env.catalog.registerIndex(xpath = IDX2)
        self.env.catalog.registerIndex(xpath = IDX3)
        self.env.catalog.registerIndex(xpath = IDX4)
        self.env.catalog.reindex(xpath = IDX1)
        self.env.catalog.reindex(xpath = IDX2)
        self.env.catalog.reindex(xpath = IDX3)
        self.env.catalog.reindex(xpath = IDX4)
        # add sort order test resources
        path = os.path.dirname(inspect.getsourcefile(self.__class__))
        test_path = os.path.join(path,'data')
        for f in so_tests:
            fh = open(test_path+os.sep+f, 'r')
            data = fh.read()
            fh.close()
            res = self.env.catalog.addResource('sortordertests', 'sotest', 
                                               data)
            self.so_ids.append([res.package.package_id, 
                                res.resourcetype.resourcetype_id, 
                                res.id, res.document._id])
        for i in so_indexes:
            self.env.catalog.registerIndex(xpath = i)
            self.env.catalog.reindex(xpath = i)
        
    def _cleanup_testdata(self):
        self.env.catalog.removeIndex(xpath = IDX1)
        self.env.catalog.removeIndex(xpath = IDX2)
        self.env.catalog.removeIndex(xpath = IDX3)
        self.env.catalog.removeIndex(xpath = IDX4)
        self.env.catalog.deleteResource(self.res1.package.package_id,
                                        self.res1.resourcetype.resourcetype_id,
                                        self.res1.id)
        self.env.catalog.deleteResource(self.res2.package.package_id,
                                        self.res2.resourcetype.resourcetype_id,
                                        self.res2.id)
        self.env.catalog.deleteResource(self.res3.package.package_id,
                                        self.res3.resourcetype.resourcetype_id,
                                        self.res3.id)
        for i in so_indexes:
            self.env.catalog.removeIndex(xpath = i)
        for res in self.so_ids:
            self.env.catalog.deleteResource(res[0],res[1],res[2])    
    
    def _assertClassAttributesEqual(self,first,second):
        return self.assertEquals(first.__dict__,second.__dict__)
    
    def _assertClassCommonAttributesEqual(self,first,second):
        # compare two classes' common attributes
        f = dict(first.__dict__)
        s = dict(second.__dict__)
        for k in s:
            if k not in f:
                f[k]=s[k]
        for k in f:
            if k not in s:
                s[k]=f[k]
        return self.assertEquals(f,s)
    
    def _assertClassAttributeListEqual(self,first,second,attribute_list):
        for attr in attribute_list:
            self.assertEqual(first.__getattribute__(attr),
                             second.__getattribute__(attr))
    
    def testRegisterIndex(self):
        index = XmlIndex(self.rt1, "/station/XY/paramXY", DATETIME_INDEX, 
                         "%Y/%m")
        self.catalog.registerIndex(index)
        
        res = self.catalog.getIndexes(self.rt1.package.package_id, 
                                      self.rt1.resourcetype_id,
                                      "/station/XY/paramXY")[0]
        self.assertEquals(res.resourcetype.resourcetype_id,
                          self.rt1.resourcetype_id)
        self.assertEquals(res.xpath, "/station/XY/paramXY")
        self.assertEquals(res.type, DATETIME_INDEX)
        self.assertEquals(res.options, "%Y/%m")
        
        
        # try to add a duplicate:
        self.assertRaises(DuplicateObjectError, 
                          self.catalog.registerIndex, index)
        
        # clean up:
        self.catalog.removeIndex(self.rt1.package.package_id,
                                 self.rt1.resourcetype_id,
                                 "/station/XY/paramXY")
    
    def testRemoveIndex(self):
        index = XmlIndex(self.rt1, "/station/XY/paramXY")
        self.catalog.registerIndex(index)
        res = self.catalog.getIndexes(self.rt1.package.package_id, 
                                      self.rt1.resourcetype_id,
                                      "/station/XY/paramXY")
        self.assertEquals(len(res), 1)
        self.catalog.removeIndex(self.rt1.package.package_id,
                                 self.rt1.resourcetype_id,
                                 "/station/XY/paramXY")
        res = self.catalog.getIndexes(self.rt1.package.package_id, 
                                      self.rt1.resourcetype_id,
                                      "/station/XY/paramXY")
        self.assertEquals(len(res), 0)
    
    def testGetIndexes(self):
        index_rt1 = XmlIndex(self.rt1, "/station/XY/paramXY")
        index2_rt1 = XmlIndex(self.rt1, "/station/station_code")
        index_rt2 = XmlIndex(self.rt2, "/station/XY/paramXY")
        self.catalog.registerIndex(index_rt1)
        self.catalog.registerIndex(index2_rt1)
        self.catalog.registerIndex(index_rt2)
        
        # get by resourcetype:
        res = self.catalog.getIndexes(package_id=self.rt1.package.package_id,
                                      resourcetype_id=self.rt1.resourcetype_id)
        self.assertEquals(len(res), 2)
        self.assertEquals(res[0].resourcetype.resourcetype_id, 
                          self.rt1.resourcetype_id)
        self.assertEquals(res[0].xpath, index_rt1.xpath)
        self.assertEquals(res[1].resourcetype.resourcetype_id, 
                          self.rt1.resourcetype_id)
        self.assertEquals(res[1].xpath, index2_rt1.xpath)
        res = self.catalog.getIndexes(package_id=self.rt2.package.package_id,
                                      resourcetype_id=self.rt2.resourcetype_id)
        self.assertEquals(len(res), 1)
        self.assertEquals(res[0].resourcetype.resourcetype_id, 
                          self.rt2.resourcetype_id)
        self.assertEquals(res[0].xpath, index_rt2.xpath)
        
        # get by xpath
        res = self.catalog.getIndexes(xpath = "/station/XY/paramXY")
        self.assertEquals(len(res), 2)
        self.assertEquals(res[0].resourcetype.resourcetype_id, 
                          self.rt1.resourcetype_id)
        self.assertEquals(res[0].xpath, index_rt1.xpath)
        self.assertEquals(res[1].resourcetype.resourcetype_id, 
                          self.rt2.resourcetype_id)
        self.assertEquals(res[1].xpath, index_rt2.xpath)
        res = self.catalog.getIndexes(xpath = "/station/station_code")
        self.assertEquals(len(res), 1)
        self.assertEquals(res[0].resourcetype.resourcetype_id, 
                          self.rt1.resourcetype_id)
        self.assertEquals(res[0].xpath, index2_rt1.xpath)
        
        # get by rt and xpath
        res = self.catalog.getIndexes(package_id=self.rt1.package.package_id,
                                      resourcetype_id=self.rt1.resourcetype_id,
                                      xpath = "/station/XY/paramXY")
        self.assertEquals(len(res), 1)
        self.assertEquals(res[0].resourcetype.resourcetype_id, 
                          self.rt1.resourcetype_id)
        self.assertEquals(res[0].xpath, "/station/XY/paramXY")
        
        # remove:
        self.catalog.removeIndex(self.rt1.package.package_id,
                                 self.rt1.resourcetype_id,
                                 "/station/XY/paramXY")
        self.catalog.removeIndex(self.rt1.package.package_id,
                                 self.rt1.resourcetype_id,
                                 "/station/station_code")
        self.catalog.removeIndex(self.rt2.package.package_id,
                                 self.rt2.resourcetype_id,
                                 "/station/XY/paramXY")
    
#    def testIndexResource(self):
#        dbmgr = XmlDbManager(self.db)
#        catalog = XmlIndexCatalog(db = self.db,
#                                  resource_storage = dbmgr)
#        bad_catalog = XmlIndexCatalog(db = self.db)
#        
#        # register a test resource:
#        test_res = Resource(self.rt3, document = newXMLDocument(RAW_XML1))
#        dbmgr.addResource(test_res)
#
#        # register a test index:
#        test_index=XmlIndex(key_path = self._test_kp,
#                            value_path = self._test_vp)
#        catalog.registerIndex(test_index)
#        
#        # index test resource:
#        catalog.indexResource(test_res.document._id, 
#                              test_index.getValue_path(), 
#                              test_index.getKey_path())
#        
#        #TODO: check db entries made
#                
#        # pass unknown index:
#        self.assertRaises(NotFoundError, catalog.indexResource,
#                          test_res.document._id, value_path="blub", 
#                          key_path="blah")
#        
#        # clean up:
#        catalog.removeIndex(key_path=self._test_kp, value_path=self._test_vp)
#        dbmgr.deleteResource(id = test_res.id)
    
#    def testFlushIndex(self):
#        dbmgr=XmlDbManager(self.db)
#        catalog=XmlIndexCatalog(self.db,dbmgr)
#        #first register an index and add some data:
#        test_index=XmlIndex(key_path = self._test_kp,
#                            value_path = self._test_vp)
#        try:
#            catalog.registerIndex(test_index)
#        except:
#            print "Error registering index."
#        
#        test_res = Resource(self.rt3, document = newXMLDocument(RAW_XML1))
#        try:
#            dbmgr.addResource(test_res)
#        except:
#            raise
#            print "Error adding resource."
#
#        catalog.indexResource(test_res.document._id, 
#                              test_index.getValue_path(),
#                              test_index.getKey_path())
#        #flush index:
#        catalog.flushIndex(value_path=self._test_vp, 
#                           key_path=self._test_kp)
#        
#        #TODO: check if index is properly flushed
#        
#        # clean up:
#        catalog.removeIndex(test_index.getValue_path(), test_index.getKey_path())
#        dbmgr.deleteResource(id = test_res.id)
#        
#    def testQuery(self):
#        """XXX: these tests fail, will be fixed with #75"""
#        # create test catalog
#        self._setup_testdata()
#        
#        q0 = "/testpackage/station/station[lon != 12.51200 and lat = 55.23200]"
#        q1 = "/testpackage/station/station[lat]"
#        q2 = "/testpackage/station/station[XY/paramXY or lon = 12.51200]"
#        q3 = "/".join(['',str(self.pkg1._id), str(self.rt2._id), 'testml'])
#
#        res0 = self.catalog.query(XPathQuery(q0))
#        res1 = self.catalog.query(XPathQuery(q1))
#        res2 = self.catalog.query(XPathQuery(q2))
#        res3 = self.catalog.query(XPathQuery(q3))
#        res0.sort(); res1.sort(); res2.sort(); res3.sort()
#        self.assertEqual(res0, [self.res2.document._id])
#        self.assertEqual(res1, [self.res1.document._id, 
#                                self.res2.document._id])
#        self.assertEqual(res2, [self.res1.document._id, 
#                                self.res2.document._id])
#        self.assertEqual(res3, [self.res3.document._id])
#
#        # sort order tests
#        so1 = "/sortordertests/sotest/sortorder[int1]"
#        so2 = "/".join(['',str(self.pkg2._id), str(self.rt4._id), 'sortorder'])
#        res1 = self.catalog.query(
#            XPathQuery(so1, [["/sortordertests/sotest/sortorder/int1","asc"]])
#            )
#        res2 = self.catalog.query(XPathQuery(so1, [["/sortordertests/sotest/sortorder/int1","desc"]], 
#                                             limit = 3))
#        res3 = self.catalog.query(XPathQuery(so1, [["/sortordertests/sotest/sortorder/int2","asc"],
#                                                   ["/sortordertests/sotest/sortorder/str2","desc"]], 
#                                             limit = 5))
#        res4 = self.catalog.query(XPathQuery(so2,[["/sortordertests/sotest/sortorder/int2","desc"]],
#                                             limit = 3))
#        
#        sot_res = [res[3] for res in self.so_ids]
#        self.assertEqual(res1,sot_res)
#        sot_res.reverse()
#        self.assertEqual(res2,sot_res[:3])
#        sot_res.reverse()
#        self.assertEqual(res3,[sot_res[0],sot_res[3],sot_res[4],
#                               sot_res[1],sot_res[2]])
#        self.assertEqual(res4,[sot_res[1],sot_res[2],sot_res[0]])
#        
#        # remove test catalog
#        self._cleanup_testdata()


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(XmlIndexCatalogTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')