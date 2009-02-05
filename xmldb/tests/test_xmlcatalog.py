# -*- coding: utf-8 -*-
"""
This test suite consists of various tests related to the catalog interface.
"""

from seishub.exceptions import SeisHubError
from seishub.test import SeisHubEnvironmentTestCase
from twisted.web import http
import unittest


RAW_XML = """<station rel_uri="bern">
    <station_code>BERN</station_code>
    <chan_code>1</chan_code>
    <stat_type>0</stat_type>
    <lon>12.51200</lon>
    <lat>50.23200</lat>
    <stat_elav>0.63500</stat_elav>
    <XY>
        <paramXY>20.5</paramXY>
        <paramXY>11.5</paramXY>
        <paramXY>blah</paramXY>
    </XY>
    
</station>"""

RAW_XML1 = """<station rel_uri="bern">
    <station_code>BERN</station_code>
    <chan_code>1</chan_code>
    <stat_type>0</stat_type>
    <lon>12.51200</lon>
    <lat>50.23200</lat>
    <stat_elav>0.63500</stat_elav>
    <XY>
        <paramXY>20.5</paramXY>
        <paramXY>11.5</paramXY>
        <paramXY>blah</paramXY>
    </XY>
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
    <XY>
        <paramXY>2110.5</paramXY>
        <paramXY>111.5</paramXY>
        <paramXY>cblah</paramXY>
    </XY>
</station>"""

RAW_XML3 = """<?xml version="1.0"?>
<testml>
<blah1 id="3"><blahblah1>blahblahblah</blahblah1></blah1>
</testml>
"""

RAW_XML4 = """<?xml version="1.0"?>
<testml>
<blah1 id="4"><blahblah1>moep</blahblah1></blah1>
</testml>
"""

PID1 = "testpackage"
RID1 = "station"
RID2 = "testml"
PID2 = "degenesis"
RID3 = "weapon"
IDX1 = "/station/XY/paramXY"
IDX2 = "/testml/blah1/@id"
IDX3 = "/weapon/damage"
IDX4 = "/station"
IDX5 = "/testml"


class XmlCatalogTest(SeisHubEnvironmentTestCase):
    def setUp(self):
        # register packages
        self.env.registry.db_registerPackage(PID1)
        self.env.registry.db_registerPackage(PID2)
        # register resourcetypes
        self.env.registry.db_registerResourceType(PID1, RID1)
        self.env.registry.db_registerResourceType(PID1, RID2)
        self.env.registry.db_registerResourceType(PID2, RID3)
        # register indexes
        self.idx1 = self.env.catalog.registerIndex(PID1, RID1, IDX1)
        self.idx2 = self.env.catalog.registerIndex(PID1, RID2, IDX2)
        self.idx3 = self.env.catalog.registerIndex(PID2, RID3, IDX3)
        # create a small test catalog
        self.res1 = self.env.catalog.addResource(PID1, RID1, RAW_XML1)
        self.res2 = self.env.catalog.addResource(PID1, RID1, RAW_XML2)
        self.res3 = self.env.catalog.addResource(PID1, RID2, RAW_XML3)
    
    def tearDown(self):
        # remove resources
        try:
            self.env.catalog.deleteResource(PID1, RID1, self.res1.id)
        except:
            pass
        try:
            self.env.catalog.deleteResource(PID1, RID1, self.res2.id)
        except:
            pass
        try:
            self.env.catalog.deleteResource(PID1, RID2, self.res3.id)
        except:
            pass
        # remove indexes
        self.env.catalog.deleteIndex(self.idx1)
        self.env.catalog.deleteIndex(self.idx2)
        self.env.catalog.deleteIndex(self.idx3)
        # remove resourcetypes
        self.env.registry.db_deleteResourceType(PID1, RID1)
        self.env.registry.db_deleteResourceType(PID1, RID2)
        self.env.registry.db_deleteResourceType(PID2, RID3)
        # remove packages
        self.env.registry.db_deletePackage(PID1)
        self.env.registry.db_deletePackage(PID2)
        
    def testIResourceManager(self):
        # add / get / delete a resource
        catalog = self.env.catalog
        res = catalog.addResource(PID1, RID1, RAW_XML, uid = 1000, 
                                  name = 'testfilename.xml')
        r = catalog.getResource(PID1, RID1, res.name)
        self.assertEquals(RAW_XML, r.document.data)
        self.assertEquals(1000, r.document.meta.uid)
        self.assertEquals('testfilename.xml', r.name)
        # rename
        catalog.moveResource(PID1, RID1, 'testfilename.xml', 'changed.xml')
        r = catalog.getResource(PID1, RID1, 'changed.xml')
        self.assertEquals('changed.xml', r.name)
        catalog.deleteResource(PID1, RID1, 'changed.xml')
        # list resources
        r = catalog.getResourceList(PID1, RID1)
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0].package.package_id, PID1)
        self.assertEqual(r[0].resourcetype.resourcetype_id, RID1)
        self.assertEqual(r[0].document.data, self.res1.document.data)
        self.assertEqual(r[1].package.package_id, PID1)
        self.assertEqual(r[1].resourcetype.resourcetype_id, RID1)
        self.assertEqual(r[1].document.data, self.res2.document.data)
        r = catalog.getResourceList(PID1)
        self.assertEqual(len(r), 3)
        self.assertEqual(r[0].package.package_id, PID1)
        self.assertEqual(r[0].resourcetype.resourcetype_id, RID1)
        self.assertEqual(r[0].document.data, self.res1.document.data)
        self.assertEqual(r[1].package.package_id, PID1)
        self.assertEqual(r[1].resourcetype.resourcetype_id, RID1)
        self.assertEqual(r[1].document.data, self.res2.document.data)
        self.assertEqual(r[2].package.package_id, PID1)
        self.assertEqual(r[2].resourcetype.resourcetype_id, RID2)
        self.assertEqual(r[2].document.data, self.res3.document.data)
        r = catalog.getResourceList()
        assert len(r) >= 3
        # unexisting package
        r = catalog.getResourceList('unexisting package')
        self.assertEquals(len(r), 0)
        # empty package
        r = catalog.getResourceList(PID2)
        self.assertEqual(len(r), 0)
        # delete all resources of type 'station'
        r = catalog.getResourceList("testpackage", "station")
        assert len(r) == 2
        catalog.deleteAllResources("testpackage", "station")
        r = catalog.getResourceList("testpackage", "station")
        assert len(r) == 0
    
    def test_reindex(self):
        # TODO: testReindex
        self.env.catalog.reindex(self.idx1)
        self.env.catalog.reindex(self.idx2)
        self.env.catalog.reindex(self.idx3)
    
    def test_getIndexes(self):
        # get all indexes
        l = self.env.catalog.getIndexes('testpackage')
        self.assertEqual(len(l), 2)
        self.assertEqual(str(l[0]), "/testpackage/station" + IDX1)
        self.assertEqual(str(l[1]), "/testpackage/testml" + IDX2)
        l = self.env.catalog.getIndexes('degenesis')
        self.assertEqual(len(l), 1)
        self.assertEqual(str(l[0]), "/degenesis/weapon" + IDX3)
        # by package
        l = self.env.catalog.getIndexes(package_id = 'testpackage')
        self.assertEqual(len(l), 2)
        self.assertEqual(str(l[0]), "/testpackage/station" + IDX1)
        self.assertEqual(str(l[1]), "/testpackage/testml" + IDX2)
        l = self.env.catalog.getIndexes(package_id = 'degenesis')
        self.assertEqual(len(l), 1)
        self.assertEqual(str(l[0]), "/degenesis/weapon" + IDX3)
        # by resource type
        l = self.env.catalog.getIndexes(resourcetype_id = 'station')
        self.assertEqual(len(l), 1)
        self.assertEqual(str(l[0]), "/testpackage/station" + IDX1)
        l = self.env.catalog.getIndexes(resourcetype_id = 'testml')
        self.assertEqual(len(l), 1)
        self.assertEqual(str(l[0]), "/testpackage/testml" + IDX2)
        #by package and resourcetype
        l = self.env.catalog.getIndexes(package_id = 'testpackage',
                                         resourcetype_id = 'station')
        self.assertEqual(len(l), 1)
        self.assertEqual(str(l[0]), "/testpackage/station" + IDX1)
        l = self.env.catalog.getIndexes(package_id = 'testpackage',
                                         resourcetype_id = 'weapon')
        self.assertEqual(len(l), 0)
    
    def test_query(self):
        """XXX: problem with limit clauses on resultsets containing indexes with multiple values per document.
        """
        # set up
        self.env.catalog.reindex(self.idx1)
        idx4 = self.env.catalog.registerIndex(PID1, RID1, IDX4, "boolean")
        self.env.catalog.reindex(idx4)
        idx5 = self.env.catalog.registerIndex(PID1, RID2, IDX5, "boolean")
        self.env.catalog.reindex(idx5)
        
        res1 = self.env.catalog.query('/testpackage/station/station ' +\
                                      'order by XY/paramXY asc limit 2', 
                                      full = True)
        self.assertEqual(len(res1), 2)
        self.assertEqual(res1[0]._id, self.res2._id)
        self.assertEqual(res1[0].document._id, self.res2.document._id)
        self.assertEqual(res1[1]._id, self.res1._id)
        self.assertEqual(res1[1].document._id, self.res1.document._id)
        
        # XXX: using limit here may lead to confusing results!!!
        res1 = self.env.catalog.query('/testpackage/station/station ' +\
                                      'order by XY/paramXY asc')
        self.assertEqual(len(res1['ordered']), 2)
        self.assertEqual(res1['ordered'][0], self.res2.document._id)
        self.assertEqual(res1['ordered'][1], self.res1.document._id)
        idx_data = res1[self.res2.document._id]['/testpackage/station' + IDX1]
        idx_data.sort()
        self.assertEqual(idx_data, [u'0', u'111.5', u'2.5', 
                                    u'2110.5', u'99', u'cblah'])
        idx_data = res1[self.res1.document._id]['/testpackage/station' + IDX1]
        idx_data.sort()
        self.assertEqual(idx_data, ['11.5', '20.5', 'blah'])
        
        res1 = self.env.catalog.query('/testpackage/station/station ' +\
                                      'order by XY/paramXY asc limit 2')
        self.assertEqual(len(res1['ordered']), 2)
        self.assertEqual(res1['ordered'][0], self.res2.document._id)
        self.assertEqual(res1['ordered'][1], self.res1.document._id)
        idx_data = res1[self.res2.document._id]['/testpackage/station' + IDX1]
        idx_data.sort()
        self.assertEqual(idx_data, ['0', '2.5', '99'])
        idx_data = res1[self.res1.document._id]['/testpackage/station' + IDX1]
        idx_data.sort()
        self.assertEqual(idx_data, ['11.5', '20.5', 'blah'])

        res3 = self.env.catalog.query('/testpackage/*/*', full = True)
        self.assertEqual(len(res3), 3)
        self.assertEqual(res3[0]._id, self.res1._id)
        self.assertEqual(res3[0].document._id, self.res1.document._id)
        self.assertEqual(res3[1]._id, self.res2._id)
        self.assertEqual(res3[1].document._id, self.res2.document._id)
        self.assertEqual(res3[2]._id, self.res3._id)
        self.assertEqual(res3[2].document._id, self.res3.document._id)
        
        # XXX: not supported yet ?
        res4 = self.env.catalog.query('/testpackage/*/station')
#        self.assertEqual(res4, [self.res1.document._id,
#                                self.res2.document._id])
        res5 = self.env.catalog.query('/testpackage/testml/testml', 
                                      full = True)
        self.assertEqual(len(res5), 1)
        self.assertEqual(res5[0]._id, self.res3._id)
        self.assertEqual(res5[0].document._id, self.res3.document._id)
        # clean up
        self.env.catalog.removeIndex(idx4)
        self.env.catalog.removeIndex(idx5)
    
    def test_indexRevision(self):
        """
        Tests indexing of a version controlled resource.
        
        Indexing of revisions is only rudimentary supported. Right now only
        the latest revision is indexed - old revisions are not represented in
        the database.
        """
        # create revision controlled resourcetype
        self.env.registry.db_registerPackage("test-catalog")
        self.env.registry.db_registerResourceType("test-catalog", "index", 
                                                  version_control=True)
        # add an index
        index = self.env.catalog.registerIndex("test-catalog", "index", 
                                               "/station/lat")
        # add a resource + some revisions
        self.env.catalog.addResource("test-catalog", "index", RAW_XML, 
                                     name="muh.xml")
        self.env.catalog.modifyResource("test-catalog", "index", RAW_XML, 
                                        name="muh.xml")
        self.env.catalog.modifyResource("test-catalog", "index", RAW_XML, 
                                        name="muh.xml")
        # get index directly from catalog for latest revision
        res=self.env.catalog.getResource("test-catalog", "index", "muh.xml")
        index_dict=self.env.catalog.getIndexData(res)
        self.assertEqual(index_dict, {u'/station/lat': u'50.23200'})
        # get index directly from catalog for revision 3 (==latest)
        res=self.env.catalog.getResource("test-catalog", "index", "muh.xml", 3)
        index_dict=self.env.catalog.getIndexData(res)
        self.assertEqual(index_dict, {u'/station/lat': u'50.23200'})
        # get index directly from catalog for revision 2
        # XXX: older revison do not have any indexed values
        # this behaviour may change later
        res=self.env.catalog.getResource("test-catalog", "index", "muh.xml", 2)
        index_dict=self.env.catalog.getIndexData(res)
        self.assertEqual(index_dict, {})
        # remove everything
        self.env.catalog.deleteIndex(index)
        self.env.registry.db_deleteResourceType("test-catalog", "index")
        self.env.registry.db_deletePackage("test-catalog")
    
    def test_addInvalidIndex(self):
        """
        SeisHub should not allow adding of an index with no XPath expression.
        """
        # create a resourcetype
        self.env.registry.db_registerPackage("test-catalog")
        self.env.registry.db_registerResourceType("test-catalog", "index")
        # invalid package
        self.assertRaises(SeisHubError, self.env.catalog.registerIndex, 
                          "XXX", "index", "/station/lat")
        self.assertRaises(SeisHubError, self.env.catalog.registerIndex, 
                          package_id="XXX", resourcetype_id="index", 
                          xpath="/station/lat")
        # invalid resourcetype
        self.assertRaises(SeisHubError, self.env.catalog.registerIndex, 
                          "test-catalog", "XXX", "/station/lat")
        self.assertRaises(SeisHubError, self.env.catalog.registerIndex, 
                          package_id="test-catalog", resourcetype_id="XXX", 
                          xpath="/station/lat")
        # invalid index type
        self.assertRaises(SeisHubError, self.env.catalog.registerIndex, 
                          "test-catalog", "index", "/station/lat", "XXX")
        self.assertRaises(SeisHubError, self.env.catalog.registerIndex, 
                          package_id="test-catalog", resourcetype_id="index", 
                          xpath="/station/lat", type="XXX")
        # empty XPath expression
        self.assertRaises(SeisHubError, self.env.catalog.registerIndex, 
                          "test-catalog", "index", "")
        self.assertRaises(SeisHubError, self.env.catalog.registerIndex, 
                          package_id="test-catalog", resourcetype_id="index", 
                          xpath="")
        # remove everything
        self.env.registry.db_deleteResourceType("test-catalog", "index")
        self.env.registry.db_deletePackage("test-catalog")
    
#    def test_automaticViewCreation(self):
#        """
#        Tests automatic view generation.
#        """
#        # set up
#        self.env.catalog.reindex("testpackage", "station", IDX1)
#        self.env.catalog.registerIndex(PID1, RID1, IDX4, "boolean")
#        self.env.catalog.reindex(PID1, RID1, IDX4)
#        self.env.catalog.registerIndex(PID1, RID2, IDX5, "boolean")
#        self.env.catalog.reindex(PID1, RID2, IDX5)
#        # query
#        sql = 'SELECT * FROM "/testpackage/station"'
#        res = self.env.db.engine.execute(sql).fetchall()
#        self.assertTrue((6, '11.5', 1) in res) 
#        self.assertTrue((6, '20.5', 1) in res) 
#        self.assertTrue((6, 'blah', 1) in res) 
#        self.assertTrue((7, '0', 1) in res)  
#        self.assertTrue((7, '111.5', 1) in res)  
#        self.assertTrue((7, '2.5', 1) in res)  
#        self.assertTrue((7, '2110.5', 1) in res)  
#        self.assertTrue((7, '99', 1) in res)  
#        self.assertTrue((7, 'cblah', 1) in res)
#        sql = 'SELECT * FROM "/testpackage/testml"'
#        res = self.env.db.engine.execute(sql).fetchall()
#        self.assertEqual(res, [(8, u'3', 1)])
#        # add a second resource and a new index
#        self.env.catalog.addResource(PID1, RID2, RAW_XML4)
#        self.env.catalog.registerIndex(PID1, RID2, "/testml/blah1/blahblah1")
#        sql = 'SELECT * FROM "/testpackage/testml"'
#        res = self.env.db.engine.execute(sql).fetchall()
#        self.assertEqual(res, [(8, '3', 1, 'blahblahblah'), 
#                               (9, '4', 1, 'moep')])
#        # clean up
#        self.env.catalog.removeIndex(PID1, RID1, IDX4)
#        self.env.catalog.removeIndex(PID1, RID2, IDX5)
    
    def test_queryCatalogWithOperators(self):
        """
        Tests a lot of operators with catalog queries.
        """
        # create a resourcetype
        self.env.registry.db_registerPackage("package")
        self.env.registry.db_registerResourceType("package", "rt")
        # add indexes
        index1 = self.env.catalog.registerIndex("package", "rt", 
                                                "/station/lat")
        index2 = self.env.catalog.registerIndex("package", "rt", 
                                                "/station/lon")
        # add resources
        self.env.catalog.addResource("package", "rt", RAW_XML, name='1')
        self.env.catalog.addResource("package", "rt", RAW_XML1, name='2')
        self.env.catalog.addResource("package", "rt", RAW_XML2, name='3')
        # queries
        # all
        query = '/package/rt/*'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 3)
        # lat != 51
        query = '/package/rt/station[lat!=55.23200]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 2)
        # lat < 51
        query = '/package/rt/station[lat<51]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 2)
        query =  '/package/rt/*[lat<51]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 2)
        # lat > 51
        query = '/package/rt/station[lat>51]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 1)
        query = '/package/rt/*[lat>51]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 1)
        # lat = 50.232001
        query =  '/package/rt/station[lat=50.232001]'
        result = self.env.catalog.query(query, full=True)
        self.assertFalse(result)
        query = '/package/rt/station[lat==50.232001]'
        result = self.env.catalog.query(query, full=True)
        self.assertFalse(result)
        # lat = 50.23200
        query = '/package/rt/station[lat=50.23200]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 2)
        query = '/package/rt/station[lat==50.23200]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 2)
        # lat > 49 and lat < 51 
        query = '/package/rt/station[lat>49 and lat<51]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 2)
        query = '/package/rt/station[lat<51 and lat>49]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 2)
        query = '/package/rt/station[(lat<51 and lat>49)]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 2)
        query = '/package/rt/*[lat>49 and lat<51]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 2)
        query = '/package/rt/*[lat<51 and lat>49]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 2)
        query = '/package/rt/*[(lat<51 and lat>49)]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 2)
        # lat > 49 and lon == 22.51200
        query = '/package/rt/station[lat>49 and lon=22.51200]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 1)
        # (lat > 49 and lat < 56) and lon == 22.51200
        query = '/package/rt/station[(lat>49 and lat<56) and lon=22.51200]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 1)
        # lat > 49 and (lat < 56 and lon == 22.51200)
        query = '/package/rt/station[lat>49 and (lat<56 and lon=22.51200)]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 1)
        # lat > 49 and (lat < 56 and lon == 22.51200)
        query = '/package/rt/station[lat>49 and (lat<56 and lon=22.51200)]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 1)
        # lat > 49 and lat < 56 and lon == 22.51200
        query = '/package/rt/station[lat>49 and lat<56 and lon=22.51200]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 1)
        # lat > 49 and lat < 56 or lon == 22.51200
        query = '/package/rt/station[(lat>52 and lat<56) or lon=12.51200]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 3)
        # lat > 49 or lat < 56 or lon == 22.51200
        query = '/package/rt/station[lat>49 or lat<56 or lon=22.51200]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 3)
        # remove everything
        self.env.catalog.deleteResource("package", "rt", '1')
        self.env.catalog.deleteResource("package", "rt", '2')
        self.env.catalog.deleteResource("package", "rt", '3')
        self.env.catalog.deleteIndex(index1)
        self.env.catalog.deleteIndex(index2)
        self.env.registry.db_deleteResourceType("package", "rt")
        self.env.registry.db_deletePackage("package")
    
    def test_queryCatalogWithMacros(self):
        """
        Test macros usage with catalog queries.
        """
        # create a resourcetype
        self.env.registry.db_registerPackage("package")
        self.env.registry.db_registerResourceType("package", "rt")
        # add indexes
        index = self.env.catalog.registerIndex("package", "rt", 
                                               "/station/XY/paramXY")
        # add resources
        self.env.catalog.addResource("package", "rt", RAW_XML, name='1')
        self.env.catalog.addResource("package", "rt", RAW_XML1, name='2')
        self.env.catalog.addResource("package", "rt", RAW_XML2, name='3')
        # queries
        query = '{a=XY/paramXY}/package/rt/station[{a}>10 and {a}=20.5]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 2)
        # with space
        query = '{a=XY/paramXY} /package/rt/station[{a}>10 and {a}=20.5]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 2)
        # a lot more spaces
        query = ' { b = XY/paramXY } /package/rt/station[{b}>10 and {b}=20.5]'
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 2)
        # multiple parameter and line breaks
        query = """{a=XY/paramXY, b=XY/paramXY}
                   /package/rt/station[{a}>10 and {b}=20.5]"""
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 2)
        # unused parameters should be ignored
        query = """{a=XY/paramXY, b=XY/paramXY, c=XY/muh/kuh}
                   /package/rt/station[{a}>10 and {b}=20.5]"""
        result = self.env.catalog.query(query, full=True)
        self.assertEqual(len(result), 2)
        # undefined parameter should raise an error
        query = '{a=XY/paramXY}/package/rt/station[{b}>10 and {b}=20.5]'
        try:
            self.env.catalog.query(query, full=True)
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEquals(e.code, http.BAD_REQUEST)
        # remove everything
        self.env.catalog.deleteResource("package", "rt", '1')
        self.env.catalog.deleteResource("package", "rt", '2')
        self.env.catalog.deleteResource("package", "rt", '3')
        self.env.catalog.deleteIndex(index)
        self.env.registry.db_deleteResourceType("package", "rt")
        self.env.registry.db_deletePackage("package")
    
    def test_registeringIndexTwice(self):
        """
        Test for registering an index a second time.
        """
        # create a resourcetype
        self.env.registry.db_registerPackage("package")
        self.env.registry.db_registerResourceType("package", "rt")
        # add index
        index1 = self.env.catalog.registerIndex("package", "rt", "/station/XY")
        # add index again
        try:
            self.env.catalog.registerIndex("package", "rt", "/station/XY")
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEquals(e.code, http.CONFLICT)
        # add index
        index2 = self.env.catalog.registerIndex("package", "rt", 
                                                "/station#lon")
        # add index again
        try:
            self.env.catalog.registerIndex("package", "rt", "/station#lon")
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEquals(e.code, http.CONFLICT)
        # remove everything
        self.env.catalog.deleteIndex(index1)
        self.env.catalog.deleteIndex(index2)
        self.env.registry.db_deleteResourceType("package", "rt")
        self.env.registry.db_deletePackage("package")


def suite():
    return unittest.makeSuite(XmlCatalogTest, 'test')


if __name__ == '__main__':
    unittest.main(defaultTest='suite')