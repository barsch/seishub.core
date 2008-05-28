# -*- coding: utf-8 -*-

import unittest

from seishub.test import SeisHubTestCase


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

IDX1 = "/station/XY/paramXY"
IDX2 = "/testml/blah1/@id"

class XmlCatalogTest(SeisHubTestCase):
    #TODO: a whole bunch of tests is still missing here
    def setUp(self):
        # create us a small test catalog
        self.res1=self.env.catalog.newXmlResource("testpackage","station",RAW_XML1)
        self.res2=self.env.catalog.newXmlResource("testpackage","station",RAW_XML2)
        self.res3=self.env.catalog.newXmlResource("testpackage","testml",RAW_XML3)
        idx1=self.env.catalog.newXmlIndex(IDX1)
        idx2=self.env.catalog.newXmlIndex(IDX2)
        self.env.catalog.addResource(self.res1)
        self.env.catalog.addResource(self.res2)
        self.env.catalog.addResource(self.res3)
        self.env.catalog.registerIndex(idx1)
        self.env.catalog.registerIndex(idx2)
    
    def tearDown(self):
        # clean up again
        self.env.catalog.removeIndex(IDX1)
        self.env.catalog.removeIndex(IDX2)
        self.env.catalog.deleteResource(self.res1._id)
        self.env.catalog.deleteResource(self.res2._id)
        self.env.catalog.deleteResource(self.res3._id)
        
    def testIResourceManager(self):
        catalog=self.env.catalog
        res = catalog.newXmlResource("testpackage","station",RAW_XML)
        catalog.addResource(res)
        r = catalog.getResource(res._id)
        self.assertEquals(RAW_XML,r.getData())
        catalog.deleteResource(res._id)
    
    def testReindex(self):
        self.env.catalog.reindex(IDX1)
    
    def testListIndexes(self):
        self.env.catalog.listIndexes()
        
    def testQuery(self):
        self.env.catalog.reindex(IDX1)
        res1 = self.env.catalog.query('/station',[['/station/XY/paramXY','asc']],limit = 2)
        res2 = self.env.catalog.query({'query':'/station',
                                       'order_by':[['/station/XY/paramXY','asc']],
                                       'limit':2})
        self.assertEqual(res1,res2)


def suite():
    return unittest.makeSuite(XmlCatalogTest, 'test')

if __name__ == '__main__':
    unittest.main(defaultTest='suite')