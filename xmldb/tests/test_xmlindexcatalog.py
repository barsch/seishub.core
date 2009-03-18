# -*- coding: utf-8 -*-

from seishub.exceptions import DuplicateObjectError, NotFoundError
from seishub.test import SeisHubEnvironmentTestCase
from seishub.xmldb.index import XmlIndex, DATETIME_INDEX
from seishub.xmldb.resource import Resource, newXMLDocument
from seishub.xmldb.xpath import XPathQuery
import inspect
import os
import unittest


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
    <test_date>20081212010102.123456789</test_date>
    <test_date2>20081212010102.050300000</test_date2>
</station>"""

RAW_XML3 = """<?xml version="1.0"?>
<testml>
<res_link>BERN</res_link>
<blah1 id="3"><blahblah1>blahblahblah</blahblah1></blah1>
</testml>
"""

RAW_XML4 = u"""
<station rel_uri="bern">
    <station_code>BERN</station_code>
    <chan_code>1</chan_code>
    <stat_type>0</stat_type>
    <lon>12.51200</lon>
    <lat>50.23200</lat>
    <stat_elav>0.63500</stat_elav>
    <XY>
        <X>1</X>
        <Y id = "1">2</Y>
        <Z>
            <value>3</value>
        </Z>
    </XY>
    <XY>
        <X>4</X>
        <Y id = "2">5</Y>
        <Z>
            <value>6</value>
        </Z>
    </XY>
    <creation_date>%s</creation_date>
    <bool>%s</bool>
</station>
"""

URI1 = "/real/bern"
URI2 = "/fake/genf"
URI3 = "/testml/res1"

IDX1 = "/station/lon"
IDX2 = "/station/lat"
IDX3 = "/testml/blah1/@id"
IDX4 = "/station/XY/paramXY"

so_tests = ['so1.xml', 'so2.xml', 'so3.xml', 'so4.xml', 'so5.xml']
so_indexes = [
    '/sortorder/int1', 
    '/sortorder/int2', 
    '/sortorder/str1', 
    '/sortorder/str2',
]

class XmlIndexCatalogTest(SeisHubEnvironmentTestCase):
    """
    """
    def setUp(self):
        self.catalog = self.env.catalog.index_catalog
        self.xmldb = self.env.catalog.xmldb
        self.so_res = list()
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
                                                 RAW_XML1, name = 'RAW_XML1')
        self.res2 = self.env.catalog.addResource(self.pkg1.package_id, 
                                                 self.rt1.resourcetype_id, 
                                                 RAW_XML2, name = 'RAW_XML2')
        self.res3 = self.env.catalog.addResource(self.pkg1.package_id, 
                                                 self.rt2.resourcetype_id, 
                                                 RAW_XML3, name = 'RAW_XML3')
        self.idx1 = self.env.catalog.registerIndex("testpackage", "station", 
                                                   "longitude", IDX1)
        self.idx2 = self.env.catalog.registerIndex("testpackage", "station", 
                                                   "latitude", IDX2)
        self.idx3 = self.env.catalog.registerIndex("testpackage", "testml", 
                                                   "blah_id", IDX3)
        self.idx4 = self.env.catalog.registerIndex("testpackage", "station", 
                                                   "paramXY", IDX4)
        # index rootnode, too
        self.idx5 = self.env.catalog.registerIndex("testpackage", "station", 
                                                   "5", "/station", 
                                                   type="boolean")
        self.env.catalog.reindexIndex(self.idx1)
        self.env.catalog.reindexIndex(self.idx2)
        self.env.catalog.reindexIndex(self.idx3)
        self.env.catalog.reindexIndex(self.idx4)
        self.env.catalog.reindexIndex(self.idx5)
        # add sort order test resources
        path = os.path.dirname(inspect.getsourcefile(self.__class__))
        test_path = os.path.join(path,'data')
        for f in so_tests:
            fh = open(test_path+os.sep+f, 'r')
            data = fh.read()
            fh.close()
            res = self.env.catalog.addResource('sortordertests', 'sotest', 
                                               data)
            self.so_res.append(res)
        self.idx_so = []
        for i in so_indexes:
            idx = self.env.catalog.registerIndex('sortordertests', 'sotest', 
                                                 i[-4:], i)
            self.idx_so.append(idx)
            self.env.catalog.reindexIndex(idx)
        
    def _cleanup_testdata(self):
        """
        """
        self.env.catalog.deleteIndex(self.idx1)
        self.env.catalog.deleteIndex(self.idx2)
        self.env.catalog.deleteIndex(self.idx3)
        self.env.catalog.deleteIndex(self.idx4)
        self.env.catalog.deleteIndex(self.idx5)
        self.env.catalog.deleteResource(self.res1)
        self.env.catalog.deleteResource(self.res2)
        self.env.catalog.deleteResource(self.res3)
        for idx in self.idx_so:
            self.env.catalog.deleteIndex(idx)
        for res in self.so_res:
            self.env.catalog.deleteResource(res)
    
    def test_registerIndex(self):
        """
        """
        index = XmlIndex(self.rt1, "/station/XY/paramXY", DATETIME_INDEX, 
                         "%Y/%m", label='test')
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
        self.catalog.deleteIndex(index)
    
    def test_deleteIndex(self):
        """
        """
        index = XmlIndex(self.rt1, "/station/XY/paramXY", label='test')
        self.catalog.registerIndex(index)
        res = self.catalog.getIndexes(self.rt1.package.package_id, 
                                      self.rt1.resourcetype_id,
                                      "/station/XY/paramXY")
        self.assertEquals(len(res), 1)
        self.catalog.deleteIndex(index)
        res = self.catalog.getIndexes(self.rt1.package.package_id, 
                                      self.rt1.resourcetype_id,
                                      "/station/XY/paramXY")
        self.assertEquals(len(res), 0)
    
    def test_getIndexes(self):
        """
        """
        index_rt1 = XmlIndex(self.rt1, "/station/XY/paramXY", label='id1')
        index2_rt1 = XmlIndex(self.rt1, "/station/station_code", label='id2')
        index_rt2 = XmlIndex(self.rt2, "/station/XY/paramXY", label='id3')
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
        self.catalog.deleteIndex(index_rt1)
        self.catalog.deleteIndex(index2_rt1)
        self.catalog.deleteIndex(index_rt2)
    
    def test_indexResource(self):
        # set up
        res = Resource(self.rt1, document = newXMLDocument(RAW_XML2))
        self.xmldb.addResource(res)
        index1 = XmlIndex(self.rt1, "/station/station_code", label='idx1')
        index2 = XmlIndex(self.rt1, "/station/XY/paramXY", label='idx2')
        self.catalog.registerIndex(index1)
        self.catalog.registerIndex(index2)
        
        #index3 = XmlIndex(self.rt1, "/station/test_date", FLOAT_INDEX)
        #self.catalog.registerIndex(index3)
        
        # index resource
        r = self.catalog.indexResource(res)
        #el = self.catalog.dumpIndex(index1)
        self.assertEquals(len(r), 4)
        el = self.catalog.dumpIndex(index1)
        self.assertEquals(len(el), 1)
        self.assertEquals(el[0].key, "GENF")
        self.assertEquals(el[0].document.data, res.document.data)
        el = self.catalog.dumpIndex(index2)
        self.assertEqual(len(el), 3)
        keys = ["0", "2.5", "99"]
        for e in el:
            assert e.key in keys
            keys.remove(e.key)
            self.assertEquals(e.document.data, res.document.data)
        
        # dumpIndexByDocument
        el = self.catalog.dumpIndexByDocument(res.document._id)
        self.assertEqual(len(el), 4)
        self.assertEquals(el[0].key, "GENF")
        self.assertEquals(el[0].document.data, res.document.data)
        self.assertEquals(el[0].index.xpath, "/station/station_code")
        self.assertEquals(el[1].key, "2.5")
        self.assertEquals(el[1].document.data, res.document.data)
        self.assertEquals(el[1].index.xpath, "/station/XY/paramXY")
        self.assertEquals(el[2].key, "0")
        self.assertEquals(el[2].document.data, res.document.data)
        self.assertEquals(el[2].index.xpath, "/station/XY/paramXY")
        self.assertEquals(el[3].key, "99")
        self.assertEquals(el[3].document.data, res.document.data)
        self.assertEquals(el[3].index.xpath, "/station/XY/paramXY")
        # clean up
        self.catalog.deleteIndex(index1)
        self.catalog.deleteIndex(index2)
        self.xmldb.deleteResource(res)
    
    def test_indexResourceWithGrouping(self):
        # set up
        res = Resource(self.rt1, document = newXMLDocument(RAW_XML4))
        self.xmldb.addResource(res)
        index = XmlIndex(self.rt1, "/station/XY/Z/value",
                         group_path = "/station/XY")
        self.catalog.registerIndex(index)
        r = self.catalog.indexResource(res)
        self.assertEquals(len(r), 2)
        el = self.catalog.dumpIndex(index)
        self.assertEquals(len(el), 2)
        self.assertEquals(el[0].key, "3")
        self.assertEquals(el[0].group_pos, 0)
        self.assertEquals(el[0].document.data, res.document.data)
        self.assertEquals(el[1].key, "6")
        self.assertEquals(el[1].group_pos, 1)
        self.assertEquals(el[1].document.data, res.document.data)
        # clean up
        self.catalog.deleteIndex(index)
        self.xmldb.deleteResource(res)
    
    def test_flushIndex(self):
        # set up
        index1 = XmlIndex(self.rt1, "/station/station_code", label = "code")
        index2 = XmlIndex(self.rt1, "/station/XY/paramXY", label = "paramXY")
        self.catalog.registerIndex(index1)
        self.catalog.registerIndex(index2)
        res = Resource(self.rt1, document = newXMLDocument(RAW_XML2))
        self.xmldb.addResource(res)
        self.catalog.indexResource(res)
        
        # index1 and index2 contain data
        el = self.catalog.dumpIndex(index1)
        self.assertEquals(len(el), 1)
        el = self.catalog.dumpIndex(index2)
        self.assertEquals(len(el), 3)
        # flush index1
        self.catalog.flushIndex(index1)
        # index1 data has gone
        el = self.catalog.dumpIndex(index1)
        self.assertEquals(len(el), 0)
        # index2 data still there
        el = self.catalog.dumpIndex(index2)
        self.assertEquals(len(el), 3)
        # flush index2
        self.catalog.flushIndex(index2)
        el = self.catalog.dumpIndex(index2)
        self.assertEquals(len(el), 0)
        # clean up:
        self.catalog.deleteIndex(index1)
        self.catalog.deleteIndex(index2)
        self.xmldb.deleteResource(res)
    
    def test_runXPathQuery(self):
        # create test catalog
        self._setup_testdata()
        #======================================================================
        # location path queries
        #======================================================================
        # all resources of package testpackage, resourcetype 'station' with 
        # rootnode 'station'
        q = "/testpackage/station/station"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(len(res['ordered']), 2)
        self.assertTrue(self.res1.document._id in res)
        self.assertTrue(self.res2.document._id in res)
        # all resources of package testpackage, resourcetype 'station'
        q = "/testpackage/station/*"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(len(res['ordered']), 2)
        self.assertTrue(self.res1.document._id in res)
        self.assertTrue(self.res2.document._id in res)
        # all resources of package testpackage
        q = "/testpackage/*/*"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(len(res['ordered']), 3)
        self.assertTrue(self.res1.document._id in res)
        self.assertTrue(self.res2.document._id in res)
        self.assertTrue(self.res3.document._id in res)
        # all resources
        q = "/*/*/*"
        res = self.catalog.query(XPathQuery(q))
        assert len(res['ordered']) >= 3
        self.assertTrue(self.res1.document._id in res)
        self.assertTrue(self.res2.document._id in res)
        self.assertTrue(self.res3.document._id in res)
        
        #======================================================================
        # node existence queries
        #====================================================================== 
        q = "/testpackage/station[station/lat]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(len(res['ordered']), 2)
        self.assertTrue(self.res1.document._id in res)
        self.assertTrue(self.res2.document._id in res)
        
        q = "/testpackage/station[station/XY/paramXY]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(len(res['ordered']), 1)
        self.assertEqual(res['ordered'], [self.res2.document._id])
        
        #======================================================================
        # key queries
        #======================================================================
        # single key query
        q = "/testpackage/station[station/lon = 12.51200]"
        xpq = XPathQuery(q)
        res = self.catalog.query(xpq)
        self.assertEqual(res['ordered'], [self.res1.document._id])
        
        # multiple key queries
        q = "/testpackage/station[station/lon != 12.51200 and station/lat = 55.23200]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(res['ordered'], [self.res2.document._id])
        q = "/testpackage/station[station/lat = 55.23200 and station/lon != 12.51200]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(res['ordered'], [self.res2.document._id])
        q = "/testpackage/station[station/lon = 12.51200 or station/lon = 22.51200]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(len(res['ordered']), 2)
        self.assertTrue(self.res1.document._id in res)
        self.assertTrue(self.res2.document._id in res)
        q = "/testpackage/station[station/lon = 12.51200 or station/lon = 0.51200]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(res['ordered'], [self.res1.document._id])
        q = "/testpackage/station[station/lon = 12.51200 or station/XY/paramXY = 2.5]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(len(res['ordered']), 2)
        self.assertTrue(self.res1.document._id in res)
        self.assertTrue(self.res2.document._id in res)
        q = "/testpackage/station[station/lon = 12.51200 or station/XY/paramXY = -100]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(res['ordered'], [self.res1.document._id])
        
        #======================================================================
        # combined queries
        #======================================================================
        # node existance AND key query
        q = "/testpackage/station[station/XY/paramXY and station/lon = 12.51200]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(len(res['ordered']), 0)
        q = "/testpackage/station[station/XY/paramXY and station/lon = 22.51200]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(res['ordered'], [self.res2.document._id])
        q = "/testpackage/station[station/lon = 12.51200 and station/XY/paramXY]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(len(res['ordered']), 0)
        q = "/testpackage/station[station/lon = 22.51200 and station/XY/paramXY]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(res['ordered'], [self.res2.document._id])
        
        # node existance OR key query
        q = "/testpackage/station[station/XY/paramXY or station/lon = 12.51200]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(len(res['ordered']), 2)
        self.assertTrue(self.res1.document._id in res)
        self.assertTrue(self.res2.document._id in res)

        #======================================================================
        # queries w/ order_by and limit clause
        #======================================================================
        # predicate query w/ order_by
        q = "/sortordertests/sotest[sortorder/int1] order by sortorder/int1 desc"
        res = self.catalog.query(XPathQuery(q))
        res_ids = [r.document._id for r in self.so_res]
        res_ids.reverse()
        self.assertEqual(res['ordered'], res_ids)
        
        so1 = "/sortordertests/sotest[sortorder/int1] order by sortorder/int1 desc " +\
              "limit 3"
        so2 = "/sortordertests/sotest[sortorder/int1] order by sortorder/int2 asc, "+\
              "sortorder/str2 desc limit 5"
        so3 = "/sortordertests/sotest order by sortorder/int2 desc, " +\
              "sortorder/str2 desc limit 3"
        res2 = self.catalog.query(XPathQuery(so1))
        res3 = self.catalog.query(XPathQuery(so2))
        res4 = self.catalog.query(XPathQuery(so3))
        
        self.assertEqual(res2['ordered'], res_ids[:3])
        res_ids.reverse()
        self.assertEqual(res3['ordered'],[res_ids[0],res_ids[3],res_ids[4],
                               res_ids[1],res_ids[2]])
        self.assertEqual(res4['ordered'],[res_ids[1],res_ids[2],res_ids[0]])
        
        #======================================================================
        # node level queries
        #======================================================================
        # all indexed data for the given xpath, note: also documents NOT having
        # the requested node are returned!
        q = "/testpackage/station/station/XY/paramXY"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(len(res['ordered']), 2)
        self.assertTrue(self.res1.document._id in res)
        self.assertTrue(self.res2.document._id in res)
        self.assertEqual(res[self.res1.document._id]["paramXY"], None)
        self.assertEqual(res[self.res2.document._id]["paramXY"], ['0', '2.5', '99'])
        # XXX: more testing!
        
        #======================================================================
        # queries w/ not(...)
        #======================================================================
        q = "/testpackage/station[not(station/XY/paramXY)]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(len(res['ordered']), 1)
        self.assertEqual(res['ordered'], [self.res1.document._id])
        q = "/testpackage/station[station/XY/paramXY != '2.5']"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(res['ordered'], [self.res2.document._id])
        q = "/testpackage/station[not(station/XY/paramXY = '2.5')]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(res['ordered'], [self.res1.document._id])
        q = "/testpackage/station[not(station/XY/paramXY = '2.5' " +\
            "and station/XY/paramXY = '0' and station/XY/paramXY = '99')]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(res['ordered'], [self.res1.document._id])
        q = "/testpackage/station[not(station/XY/paramXY = '2.5')]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(res['ordered'], [self.res1.document._id])
        
        
        #======================================================================
        # queries w/ labels
        #======================================================================
        q = "/testpackage/station[longitude]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(len(res['ordered']), 2)
        q = "/testpackage/station[longitude = 22.51200 and station/XY/paramXY]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(res['ordered'], [self.res2.document._id])
        q = "/testpackage/station[longitude=22.51200 and paramXY=5]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(res['ordered'], [])
        q = "/testpackage/station[longitude=22.51200 and paramXY=2.5]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(res['ordered'], [self.res2.document._id])
        
        #======================================================================
        # invalid queries
        #======================================================================
        # unknown index
        q = "/testpackage/station[station/XY]"
        self.assertRaises(NotFoundError, self.catalog.query, XPathQuery(q))
        # remove test catalog
        self._cleanup_testdata()
    
    def test_indexTypes(self):
        text_idx = self.env.catalog.registerIndex("testpackage", "station", 
                                                  "idx1", 
                                                  "/station/station_code", 
                                                  "text")
        float_idx = self.env.catalog.registerIndex("testpackage", "station", 
                                                   "idx2", "/station/lon", 
                                                   "float")
        self.env.catalog.reindexIndex(text_idx)
        self.env.catalog.reindexIndex(float_idx)
        
        # print self.catalog.dumpIndex("testpackage", "station", "/station/station_code")
        # clean up
        self.env.catalog.deleteAllIndexes("testpackage")
    
#    def testIndexCache(self):
#        before = list(self.catalog._cache['package_id'].values()[0])
#        self._setup_testdata()
#        between = list(self.catalog._cache['package_id'].values()[0])
#        self._cleanup_testdata()
#        after = list(self.catalog._cache['package_id'].values()[0])
    
    def test_updateIndexView(self):
        """
        Tests creation of an index view.
        """
        # create test catalog
        self._setup_testdata()
        
        self.catalog.updateIndexView(self.idx1)
        sql = 'SELECT * FROM "/testpackage/station"'
        res = self.env.db.engine.execute(sql).fetchall()
        self.assertEquals(res, [(6, u'testpackage', u'station', u'RAW_XML1', 
                                 u'12.51200', u'50.23200', None, 1), 
                                (7, u'testpackage', u'station', u'RAW_XML2', 
                                 u'22.51200', u'55.23200', u'0', 1), 
                                (7, u'testpackage', u'station', u'RAW_XML2', 
                                 u'22.51200', u'55.23200', u'2.5', 1), 
                                (7, u'testpackage', u'station', u'RAW_XML2', 
                                 u'22.51200', u'55.23200', u'99', 1)])
        self.catalog.dropIndexView(self.idx1)
        sql = 'SELECT * FROM "/testpackage/station"'
        self.assertRaises(Exception, self.env.db.engine.execute, sql)
        # remove test catalog
        self._cleanup_testdata()


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(XmlIndexCatalogTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')