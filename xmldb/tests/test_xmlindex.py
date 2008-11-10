# -*- coding: utf-8 -*-

import unittest

from seishub.test import SeisHubEnvironmentTestCase
from seishub.exceptions import SeisHubError
from seishub.xmldb.resource import XmlDocument, Resource, newXMLDocument
from seishub.xmldb.index import XmlIndex


RAW_XML1="""<station rel_uri="bern">
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

class XmlIndexTest(SeisHubEnvironmentTestCase):
    def setUp(self):
        # register packages
        self.pkg1 = self.env.registry.db_registerPackage("testpackage")
        self.rt1 = self.env.registry.db_registerResourceType("testpackage",
                                                             "station")
    
    def tearDown(self):
        # remove packages
        self.env.registry.db_deleteResourceType("testpackage", "station")
        self.env.registry.db_deletePackage("testpackage")
        
    def testEval(self):
        #index with single node key result:
        test_index=XmlIndex(key_path = "lon",
                            value_path = "/testpackage/station/station"
                            )
        #index with multiple nodes key result:
        xy_index=XmlIndex(key_path="XY/paramXY",
                          value_path = "/testpackage/station/station"
                          )
        
        empty_resource = Resource(document = XmlDocument())
        test_resource = Resource(self.rt1, document = newXMLDocument(RAW_XML1))
        
        class Foo(object):
            pass
        
        # pass a Foo: (which does not implement IXmlDoc)
        self.assertRaises(TypeError,
                          test_index.eval,
                          Foo())
        # pass an empty XmlDoc:
        self.assertRaises(SeisHubError,
                          test_index.eval,
                          empty_resource.document)
        
        self.assertEquals({'value': None, 
                           'key': '12.51200'},
                          test_index.eval(test_resource.document)[0])
        self.assertEquals([{'value': None, 
                            'key': '20.5'}, 
                           {'value': None, 
                            'key': '11.5'}, 
                           {'value': None, 
                            'key': 'blah'}],
                          xy_index.eval(test_resource.document)
                          )


def suite():
    return unittest.makeSuite(XmlIndexTest, 'test')

if __name__ == '__main__':
    unittest.main(defaultTest='suite')