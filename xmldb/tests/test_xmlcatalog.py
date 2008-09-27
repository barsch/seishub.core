# -*- coding: utf-8 -*-

import unittest

from seishub.test import SeisHubEnvironmentTestCase
from seishub.core import SeisHubError


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
</station>"""

RAW_XML3 = """<?xml version="1.0"?>
<testml>
<blah1 id="3"><blahblah1>blahblahblah</blahblah1></blah1>
</testml>
"""

URI = "/testpackage/station"
URI1 = "/real/bern"
URI2 = "/fake/genf"
URI3 = "/testml/res1"

pid1 = "testpackage"
rid1 = "station"
rid2 = "testml"
pid2 = "degenesis"
rid3 = "weapon"
IDX1 = "/station/XY/paramXY"
IDX2 = "/testml/blah1/@id"
IDX3 = "/weapon/damage"

class XmlCatalogTest(SeisHubEnvironmentTestCase):
    def setUp(self):
        # register packages
        self.pkg1 = self.env.registry.db_registerPackage(pid1)
        self.rt1 = self.env.registry.db_registerResourceType(pid1, rid1)
        self.rt2 = self.env.registry.db_registerResourceType(pid1, rid2)
        self.pkg2 = self.env.registry.db_registerPackage(pid2)
        self.rt3 = self.env.registry.db_registerResourceType(pid2, rid3)
        
        # create a small test catalog
        self.res1 = self.env.catalog.addResource(pid1, rid1, RAW_XML1)
        self.res2 = self.env.catalog.addResource(pid1, rid1, RAW_XML2)
        self.res3 = self.env.catalog.addResource(pid1, rid2, RAW_XML3)
        self.env.catalog.registerIndex(pid1, rid1, IDX1)
        self.env.catalog.registerIndex(pid1, rid2, IDX2)
        self.env.catalog.registerIndex(pid2, rid3, IDX3)
    
    def tearDown(self):
        # clean up test catalog
        self.env.catalog.removeIndex("testpackage", "station", IDX1)
        self.env.catalog.removeIndex("testpackage", "testml", IDX2)
        self.env.catalog.removeIndex("degenesis", "weapon", IDX3)
        try:
            self.env.catalog.deleteResource(self.res1.package.package_id,
                                            self.res1.resourcetype.resourcetype_id,
                                            self.res1.id)
        except:
            pass
        try:
            self.env.catalog.deleteResource(self.res2.package.package_id,
                                            self.res2.resourcetype.resourcetype_id,
                                            self.res2.id)
        except:
            pass
        try:
            self.env.catalog.deleteResource(self.res3.package.package_id,
                                            self.res3.resourcetype.resourcetype_id,
                                            self.res3.id)
        except:
            pass
        # remove packages
        self.env.registry.db_deleteResourceType(pid1, rid1)
        self.env.registry.db_deleteResourceType(pid1, rid2)
        self.env.registry.db_deletePackage(pid1)
        self.env.registry.db_deleteResourceType(pid2, rid3)
        self.env.registry.db_deletePackage(pid2)
        
    def testIResourceManager(self):
        # add / get / delete a resource
        catalog = self.env.catalog
        res = catalog.addResource(pid1, rid1, RAW_XML, uid = 1000)
        r = catalog.getResource(pid1, rid1, res.id)
        self.assertEquals(RAW_XML, r.document.data)
        self.assertEquals(1000, r.document.uid)
        catalog.deleteResource(pid1, rid1, res.id)
        # list resources
        r = catalog.getResourceList(pid1, rid1)
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0].package.package_id, pid1)
        self.assertEqual(r[0].resourcetype.resourcetype_id, rid1)
        self.assertEqual(r[0].document.data, self.res1.document.data)
        self.assertEqual(r[1].package.package_id, pid1)
        self.assertEqual(r[1].resourcetype.resourcetype_id, rid1)
        self.assertEqual(r[1].document.data, self.res2.document.data)
        r = catalog.getResourceList(pid1)
        self.assertEqual(len(r), 3)
        self.assertEqual(r[0].package.package_id, pid1)
        self.assertEqual(r[0].resourcetype.resourcetype_id, rid1)
        self.assertEqual(r[0].document.data, self.res1.document.data)
        self.assertEqual(r[1].package.package_id, pid1)
        self.assertEqual(r[1].resourcetype.resourcetype_id, rid1)
        self.assertEqual(r[1].document.data, self.res2.document.data)
        self.assertEqual(r[2].package.package_id, pid1)
        self.assertEqual(r[2].resourcetype.resourcetype_id, rid2)
        self.assertEqual(r[2].document.data, self.res3.document.data)
        r = catalog.getResourceList()
        assert len(r) >= 3
        # unexisting package
        self.assertRaises(SeisHubError, 
                          catalog.getResourceList, 'unexisting package')
        r = catalog.getResourceList(pid2)
        self.assertEqual(r, list())
        # delete all resources of type 'station'
        r = catalog.getResourceList("testpackage", "station")
        assert len(r) == 2
        catalog.deleteAllResources("testpackage", "station")
        r = catalog.getResourceList("testpackage", "station")
        assert len(r) == 0

    
    def testReindex(self):
        # TODO: testReindex
        self.env.catalog.reindex("testpackage", "station", IDX1)

    def testListIndexes(self):
        # get all indexes
        l = self.env.catalog.listIndexes()
        self.assertEqual(len(l), 3)
        self.assertEqual(str(l[0]), "/testpackage/station" + IDX1)
        self.assertEqual(str(l[1]), "/testpackage/testml" + IDX2)
        self.assertEqual(str(l[2]), "/degenesis/weapon" + IDX3)
        # by package
        l = self.env.catalog.listIndexes(package_id = 'testpackage')
        self.assertEqual(len(l), 2)
        self.assertEqual(str(l[0]), "/testpackage/station" + IDX1)
        self.assertEqual(str(l[1]), "/testpackage/testml" + IDX2)
        l = self.env.catalog.listIndexes(package_id = 'degenesis')
        self.assertEqual(len(l), 1)
        self.assertEqual(str(l[0]), "/degenesis/weapon" + IDX3)
        # by resource type
        l = self.env.catalog.listIndexes(resourcetype_id = 'station')
        self.assertEqual(len(l), 1)
        self.assertEqual(str(l[0]), "/testpackage/station" + IDX1)
        l = self.env.catalog.listIndexes(resourcetype_id = 'testml')
        self.assertEqual(len(l), 1)
        self.assertEqual(str(l[0]), "/testpackage/testml" + IDX2)
        #by package and resourcetype
        l = self.env.catalog.listIndexes(package_id = 'testpackage',
                                         resourcetype_id = 'station')
        self.assertEqual(len(l), 1)
        self.assertEqual(str(l[0]), "/testpackage/station" + IDX1)
        l = self.env.catalog.listIndexes(package_id = 'testpackage',
                                         resourcetype_id = 'weapon')
        self.assertEqual(len(l), 0)
        
    def testQuery(self):
        self.env.catalog.reindex("testpackage", "station", IDX1)
        res1 = self.env.catalog.query('/testpackage/station/station',
                                      [['/testpackage/station/station/XY/paramXY','asc']],
                                      limit = 2)
        res2 = self.env.catalog.query({'query':'/testpackage/station/station',
                                       'order_by':[['/testpackage/station/station/XY/paramXY','asc']],
                                       'limit':2})
        self.assertEqual(res1, [self.res2.document._id, 
                                self.res1.document._id])
        self.assertEqual(res2, [self.res2.document._id, 
                                self.res1.document._id])
        res3 = self.env.catalog.query('/testpackage/*/*')
        self.assertEqual(res3, [self.res1.document._id,
                         self.res2.document._id,
                         self.res3.document._id])
        res4 = self.env.catalog.query('/testpackage/*/station')
        # XXX: rootnode still ignored here!!!
#        self.assertEqual(res4, [self.res1.document._id,
#                                self.res2.document._id])
        res5 = self.env.catalog.query('/testpackage/testml/testml')
        self.assertEqual(res5, [self.res3.document._id])
        


def suite():
    return unittest.makeSuite(XmlCatalogTest, 'test')

if __name__ == '__main__':
    unittest.main(defaultTest='suite')