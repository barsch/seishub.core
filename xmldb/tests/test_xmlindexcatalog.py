# -*- coding: utf-8 -*-

from seishub.exceptions import DuplicateObjectError, NotFoundError
from seishub.test import SeisHubEnvironmentTestCase
from seishub.xmldb.index import XmlIndex, DATETIME_INDEX
from seishub.xmldb.resource import Resource, newXMLDocument
from seishub.xmldb.xpath import XPathQuery
from sqlalchemy.exceptions import ProgrammingError
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

URI1 = "/real/bern"
URI2 = "/fake/genf"
URI3 = "/testml/res1"

IDX1 = "/station/lon"
IDX2 = "/station/lat"
IDX3 = "/testml/blah1/@id"
IDX4 = "/station/XY/paramXY"

so_tests = ['so1.xml','so2.xml','so3.xml','so4.xml','so5.xml']
so_indexes = ['/sortorder/int1', 
              '/sortorder/int2', 
              '/sortorder/str1', 
              '/sortorder/str2',
              #'/sortorder'
              ]

class XmlIndexCatalogTest(SeisHubEnvironmentTestCase):
    #TODO: testGetIndexes
    # last_id = 0
    # test_xpath = "/station/XY/paramXY"
    # test_uri="/stations/bern"
    
    def setUp(self):
        self.catalog = self.env.catalog.index_catalog
        self.xmldb = self.env.catalog.xmldb
        self.so_ids = list()
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
        self.env.catalog.registerIndex("testpackage", "station", IDX1)
        self.env.catalog.registerIndex("testpackage", "station", IDX2)
        self.env.catalog.registerIndex("testpackage", "testml", IDX3)
        self.env.catalog.registerIndex("testpackage", "station", IDX4)
        # index rootnode, too
        self.env.catalog.registerIndex("testpackage", "station", "/station",
                                       type = "boolean")
        
        self.env.catalog.reindex("testpackage", "station", IDX1)
        self.env.catalog.reindex("testpackage", "station", IDX2)
        self.env.catalog.reindex("testpackage", "testml", IDX3)
        self.env.catalog.reindex("testpackage", "station", IDX4)
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
            self.env.catalog.registerIndex('sortordertests', 'sotest', i)
            self.env.catalog.reindex('sortordertests', 'sotest', i)
        
    def _cleanup_testdata(self):
        self.env.catalog.removeIndex("testpackage", "station", IDX1)
        self.env.catalog.removeIndex("testpackage", "station", IDX2)
        self.env.catalog.removeIndex("testpackage", "testml", IDX3)
        self.env.catalog.removeIndex("testpackage", "station", IDX4)
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
            self.env.catalog.removeIndex('sortordertests', 'sotest', i)
        for res in self.so_ids:
            self.env.catalog.deleteResource(res[0],res[1],res[2])
    
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
    
    def testIndexResource(self):
        # set up
        res = Resource(self.rt1, document = newXMLDocument(RAW_XML2))
        self.xmldb.addResource(res)
        index1 = XmlIndex(self.rt1, "/station/station_code")
        index2 = XmlIndex(self.rt1, "/station/XY/paramXY")
        self.catalog.registerIndex(index1)
        self.catalog.registerIndex(index2)
        
        #index3 = XmlIndex(self.rt1, "/station/test_date", FLOAT_INDEX)
        #self.catalog.registerIndex(index3)
        
        # index resource
        
        r = self.catalog.indexResource(res)
#        el = self.catalog.dumpIndex(self.pkg1.package_id, 
#                                    self.rt1.resourcetype_id, 
#                                    "/station/test_date")
        self.assertEquals(len(r), 4)
        el = self.catalog.dumpIndex(self.pkg1.package_id, 
                                    self.rt1.resourcetype_id, 
                                    "/station/station_code")
        self.assertEquals(len(el), 1)
        self.assertEquals(el[0].key, "GENF")
        self.assertEquals(el[0].document.data, res.document.data)
        el = self.catalog.dumpIndex(self.pkg1.package_id, 
                                    self.rt1.resourcetype_id, 
                                    "/station/XY/paramXY")
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
        self.catalog.removeIndex(self.rt1.package.package_id,
                                 self.rt1.resourcetype_id,
                                 "/station/station_code")
        self.catalog.removeIndex(self.rt1.package.package_id,
                                 self.rt1.resourcetype_id,
                                 "/station/XY/paramXY")
        self.xmldb.deleteResource(id = res.id)
    
    def testFlushIndex(self):
        # set up
        index1 = XmlIndex(self.rt1, "/station/station_code")
        index2 = XmlIndex(self.rt1, "/station/XY/paramXY")
        self.catalog.registerIndex(index1)
        self.catalog.registerIndex(index2)
        res = Resource(self.rt1, document = newXMLDocument(RAW_XML2))
        self.xmldb.addResource(res)
        self.catalog.indexResource(res)
        
        # index1 and index2 contain data
        el = self.catalog.dumpIndex(self.pkg1.package_id, 
                                    self.rt1.resourcetype_id, 
                                    "/station/station_code")
        self.assertEquals(len(el), 1)
        el = self.catalog.dumpIndex(self.pkg1.package_id, 
                                    self.rt1.resourcetype_id, 
                                    "/station/XY/paramXY")
        self.assertEquals(len(el), 3)
        # flush index1
        self.catalog.flushIndex(self.rt1.package.package_id,
                                 self.rt1.resourcetype_id,
                                 "/station/station_code")
        # index1 data has gone
        el = self.catalog.dumpIndex(self.pkg1.package_id, 
                                    self.rt1.resourcetype_id, 
                                    "/station/station_code")
        self.assertEquals(len(el), 0)
        # index2 data still there
        el = self.catalog.dumpIndex(self.pkg1.package_id, 
                                    self.rt1.resourcetype_id, 
                                    "/station/XY/paramXY")
        self.assertEquals(len(el), 3)
        # flush index2
        self.catalog.flushIndex(self.rt1.package.package_id,
                                self.rt1.resourcetype_id,
                                "/station/XY/paramXY")
        el = self.catalog.dumpIndex(self.pkg1.package_id, 
                                    self.rt1.resourcetype_id, 
                                    "/station/XY/paramXY")
        self.assertEquals(len(el), 0)
        
        # clean up:
        self.catalog.removeIndex(self.rt1.package.package_id,
                                 self.rt1.resourcetype_id,
                                 "/station/station_code")
        self.catalog.removeIndex(self.rt1.package.package_id,
                                 self.rt1.resourcetype_id,
                                 "/station/XY/paramXY")
        self.xmldb.deleteResource(id = res.id)
        
    def testIndexQuery(self):
        pass
        
    def testXPathQuery(self):
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
        # node existance queries
        #====================================================================== 
        q = "/testpackage/station/station[lat]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(len(res['ordered']), 2)
        self.assertTrue(self.res1.document._id in res)
        self.assertTrue(self.res2.document._id in res)
        
        q = "/testpackage/station/station[XY/paramXY]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(len(res['ordered']), 1)
        self.assertEqual(res['ordered'], [self.res2.document._id])
        
        #======================================================================
        # key queries
        #======================================================================
        # single key query
        q = "/testpackage/station/station[lon = 12.51200]"
        xpq = XPathQuery(q)
        res = self.catalog.query(xpq)
        self.assertEqual(res['ordered'], [self.res1.document._id])
        
        # multiple key queries
        q = "/testpackage/station/station[lon != 12.51200 and lat = 55.23200]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(res['ordered'], [self.res2.document._id])
        q = "/testpackage/station/station[lat = 55.23200 and lon != 12.51200]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(res['ordered'], [self.res2.document._id])
        q = "/testpackage/station/station[lon = 12.51200 or lon = 22.51200]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(len(res['ordered']), 2)
        self.assertTrue(self.res1.document._id in res)
        self.assertTrue(self.res2.document._id in res)
        q = "/testpackage/station/station[lon = 12.51200 or lon = 0.51200]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(res['ordered'], [self.res1.document._id])
        q = "/testpackage/station/station[lon = 12.51200 or XY/paramXY = 2.5]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(len(res['ordered']), 2)
        self.assertTrue(self.res1.document._id in res)
        self.assertTrue(self.res2.document._id in res)
        q = "/testpackage/station/station[lon = 12.51200 or XY/paramXY = -100]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(res['ordered'], [self.res1.document._id])
        
        #======================================================================
        # combined queries
        #======================================================================
        # node existance AND key query
        q = "/testpackage/station/station[XY/paramXY and lon = 12.51200]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(len(res['ordered']), 0)
        q = "/testpackage/station/station[XY/paramXY and lon = 22.51200]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(res['ordered'], [self.res2.document._id])
        q = "/testpackage/station/station[lon = 12.51200 and XY/paramXY]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(len(res['ordered']), 0)
        q = "/testpackage/station/station[lon = 22.51200 and XY/paramXY]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(res['ordered'], [self.res2.document._id])
        
        # node existance OR key query
        q = "/testpackage/station/station[XY/paramXY or lon = 12.51200]"
        res = self.catalog.query(XPathQuery(q))
        self.assertEqual(len(res['ordered']), 2)
        self.assertTrue(self.res1.document._id in res)
        self.assertTrue(self.res2.document._id in res)

        #======================================================================
        # queries w/ order_by and limit clause
        #======================================================================
        # predicate query w/ order_by
        q = "/sortordertests/sotest/sortorder[int1] order by int1 desc"
        res = self.catalog.query(XPathQuery(q))
        res_ids = [id[3] for id in self.so_ids]
        res_ids.reverse()
        self.assertEqual(res['ordered'], res_ids)
        
        so1 = "/sortordertests/sotest/sortorder[int1] order by int1 desc " +\
              "limit 3"
        so2 = "/sortordertests/sotest/sortorder[int1] order by int2 asc, "+\
              "str2 desc limit 5"
        so3 = "/sortordertests/sotest/sortorder order by int2 desc, " +\
              "str2 desc limit 3"
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
        self.assertEqual(res[self.res1.document._id]
                         ["/testpackage/station/station/XY/paramXY"],
                         None)
        self.assertEqual(res[self.res2.document._id]
                         ["/testpackage/station/station/XY/paramXY"],
                         ['0', '2.5', '99'])
        # XXX: more testing!
        
        #======================================================================
        # invalid queries
        #======================================================================
        # unknown index
        q = "/testpackage/station/station[XY]"
        self.assertRaises(NotFoundError, self.catalog.query, XPathQuery(q))
        
        # remove test catalog
        self._cleanup_testdata()
        
    def testIndexTypes(self):
        text_idx = self.env.catalog.registerIndex("testpackage", "station", 
                                                  "/station/station_code", 
                                                  "text")
        float_idx = self.env.catalog.registerIndex("testpackage", "station", 
                                                   "/station/lon", "float")
        self.env.catalog.reindex("testpackage", "station", "/station/station_code")
        self.env.catalog.reindex("testpackage", "station", "/station/lon")
        
        # print self.catalog.dumpIndex("testpackage", "station", "/station/station_code")
        
    def testCreateView(self):
        """Fails with SQLite. (no support for views)
        """
        # create test catalog
        self._setup_testdata()
        
        self.catalog.createView("testpackage", "station")
        sql = 'SELECT * FROM "/testpackage/station"'
        res = self.env.db.engine.execute(sql).fetchall()
        self.assertEquals(res, 
                          [(6, '12.51200', '50.23200', None, True), 
                           (7, '22.51200', '55.23200', '0', True), 
                           (7, '22.51200', '55.23200', '2.5', True), 
                           (7, '22.51200', '55.23200', '99', True)])
        self.catalog.dropView("testpackage", "station")
        sql = 'SELECT * FROM "/testpackage/station"'
        self.assertRaises(ProgrammingError, self.env.db.engine.execute, sql)
        # remove test catalog
        self._cleanup_testdata()
        

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(XmlIndexCatalogTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')