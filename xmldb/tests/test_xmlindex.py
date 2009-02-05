# -*- coding: utf-8 -*-

from datetime import datetime
from seishub.core import Component, implements
from seishub.exceptions import SeisHubError
from seishub.packages.interfaces import IProcessorIndex, IPackage, \
    IResourceType
from seishub.test import SeisHubEnvironmentTestCase
from seishub.xmldb import index
from seishub.xmldb.index import NumericIndexElement, XmlIndex
from seishub.xmldb.resource import XmlDocument, newXMLDocument
import time
import unittest


RAW_XML1 = u"""
<station rel_uri="bern">
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
    <creation_date>%s</creation_date>
    <bool>%s</bool>
</station>
"""

RAW_XML2 = u"""
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
    
    def testIndexCommon(self):
        # index with single node key result:
        si = XmlIndex(self.rt1, xpath = "/station/station_code")
        # index with multiple nodes key result:
        mi = XmlIndex(self.rt1, xpath = "/station/XY/paramXY")
        # index which does not fit on test resource
        ni = XmlIndex(self.rt1, xpath = "/station/network")
        
        test_doc = newXMLDocument(RAW_XML1)
        
        class Foo(object):
            pass
        
        # pass a Foo: (which does not implement IXmlDoc)
        self.assertRaises(TypeError, si.eval, Foo())
        # pass an empty XmlDoc:
        self.assertRaises(SeisHubError, si.eval, XmlDocument())
        
        res = si.eval(test_doc, self.env)
        self.assertEquals(len(res), 1)
        self.assertEquals(res[0].index, si)
        self.assertEquals(res[0].document, test_doc)
        self.assertEquals(res[0].key, 'BERN')
        
        res = mi.eval(test_doc, self.env)
        self.assertEquals(len(res), 3)
        self.assertEquals(res[0].index, mi)
        self.assertEquals(res[0].document, test_doc)
        self.assertEquals(res[0].key, '20.5')
        self.assertEquals(res[1].index, mi)
        self.assertEquals(res[1].document, test_doc)
        self.assertEquals(res[1].key, '11.5')
        self.assertEquals(res[2].index, mi)
        self.assertEquals(res[2].document, test_doc)
        self.assertEquals(res[2].key, 'blah')
        
        res = ni.eval(test_doc, self.env)
        self.assertEquals(res, [])
    
    def testTextIndex(self):
        test_doc = newXMLDocument(RAW_XML1)
        idx = XmlIndex(self.rt1, "/station/lon", index.TEXT_INDEX)
        res = idx.eval(test_doc, self.env)[0]
        self.assertEquals(type(res), index.TextIndexElement)
        self.assertEquals(type(res.key), unicode)
        self.assertEquals(res.key, '12.51200')
    
    def testNumericIndex(self):
        test_doc = newXMLDocument(RAW_XML1)
        idx = XmlIndex(self.rt1, "/station/lon", index.NUMERIC_INDEX)
        res = idx.eval(test_doc, self.env)[0]
        self.assertEquals(type(res), NumericIndexElement)
        # self.assertEquals(type(res.key), float)
        self.assertEquals(res.key, '12.51200')
        # elements with wrong data type are ignored
        idx = XmlIndex(self.rt1, "/station/XY/paramXY", index.NUMERIC_INDEX)
        res = idx.eval(test_doc, self.env)
        self.assertEquals(len(res), 2)
    
    def testDateTimeIndex(self):
        dt = datetime(2008, 10, 10, 11, 53, 0, 54000)
        #timestamp = float(str(time.mktime(res.timetuple())) + ".054")
        # ISO 8601
        idx = XmlIndex(self.rt1, "/station/creation_date", 
                       index.DATETIME_INDEX)
        timestr = dt.strftime("%Y%m%dT%H:%M:%S") + ".0" + str(dt.microsecond)
        doc = newXMLDocument(RAW_XML1 % (timestr, ""))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, dt)
        
        # with timestamp
        idx = XmlIndex(self.rt1, "/station/creation_date", 
                       index.DATETIME_INDEX)
        timestr = "%10.3f" % (time.mktime(dt.timetuple()) + dt.microsecond/1e6)
        doc = newXMLDocument(RAW_XML1 % (timestr, ""))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, dt)
        # with custom format
        # microseconds are ignored since not supported by strftime()
        idx = XmlIndex(self.rt1, "/station/creation_date", 
                       index.DATETIME_INDEX, "%H:%M:%S - %Y%m%d")
        timestr = dt.strftime("%H:%M:%S - %Y%m%d")
        doc = newXMLDocument(RAW_XML1 % (timestr, ""))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, dt.replace(microsecond = 0))
    
    def test_DateIndex(self):
        dt = datetime(2008, 10, 10, 11, 53, 0, 54000)
        # ISO 8601
        idx = XmlIndex(self.rt1, "/station/creation_date", 
                       index.DATE_INDEX)
        timestr = dt.strftime("%Y%m%d")
        doc = newXMLDocument(RAW_XML1 % (timestr, ""))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, dt.date())
        # custom format
        idx = XmlIndex(self.rt1, "/station/creation_date", 
                       index.DATE_INDEX, "%d.%m.%Y")
        timestr = dt.strftime("%d.%m.%Y")
        doc = newXMLDocument(RAW_XML1 % (timestr, ""))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, dt.date())
    
    def testBooleanIndex(self):
        idx = XmlIndex(self.rt1, "/station/bool", index.BOOLEAN_INDEX)
        doc = newXMLDocument(RAW_XML1 % ("", "True"))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, True)
        
        doc = newXMLDocument(RAW_XML1 % ("", "False"))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, False)
        
        doc = newXMLDocument(RAW_XML1 % ("", "1"))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, True)
        
        doc = newXMLDocument(RAW_XML1 % ("", "0"))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, False)
        
        doc = newXMLDocument(RAW_XML1 % ("", "something"))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, True)
    
    def testIndexGrouping(self):
        doc = newXMLDocument(RAW_XML2)
        idx1 = XmlIndex(self.rt1, "/station/XY/X", index.NUMERIC_INDEX,
                        group_path = "/station/XY")
        res = idx1.eval(doc, self.env)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0].key, '1')
        self.assertEqual(res[0].group_pos, 0)
        self.assertEqual(res[1].key, '4')
        self.assertEqual(res[1].group_pos, 1)
        
        idx2 = XmlIndex(self.rt1, "/station/XY/Y", index.NUMERIC_INDEX,
                        group_path = "/station/XY")
        res = idx2.eval(doc, self.env)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0].key, '2')
        self.assertEqual(res[0].group_pos, 0)
        self.assertEqual(res[1].key, '5')
        self.assertEqual(res[1].group_pos, 1)
        
        idx3 = XmlIndex(self.rt1, "/station/XY/Y/@id", index.NUMERIC_INDEX,
                        group_path = "/station/XY")
        res = idx3.eval(doc, self.env)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0].key, '1')
        self.assertEqual(res[0].group_pos, 0)
        self.assertEqual(res[1].key, '2')
        self.assertEqual(res[1].group_pos, 1)
        
        idx4 = XmlIndex(self.rt1, "/station/XY/Z/value", index.NUMERIC_INDEX,
                        group_path = "/station/XY")
        res = idx4.eval(doc, self.env)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0].key, '3')
        self.assertEqual(res[0].group_pos, 0)
        self.assertEqual(res[1].key, '6')
        self.assertEqual(res[1].group_pos, 1)
    
#    def testNoneTypeIndex(self):
#        doc = newXMLDocument(RAW_XML1)
#        idx = XmlIndex(self.rt1, "/station/stat_type", index.NONETYPE_INDEX)
#        res = idx.eval(doc, self.env)
#        self.assertEquals(type(res[0]), index.NoneTypeIndexElement)
#        self.assertEquals(res[0].key, None)
#        
#        idx = XmlIndex(self.rt1, "/station/not_there", index.NONETYPE_INDEX)
#        res = idx.eval(doc, self.env)
#        self.assertEquals(len(res), 0)
#        
#        idx = XmlIndex(self.rt1, "/station/XY/paramXY[. = 20.5]", 
#                       index.NONETYPE_INDEX)
#        res = idx.eval(doc, self.env)
#        self.assertEquals(len(res), 1)
#        self.assertEquals(type(res[0]), index.NoneTypeIndexElement)
#        self.assertEquals(res[0].key, None)


class ProcessorIndexTestPackage(Component):
    implements(IPackage)
    package_id = 'processorindextest'


class ProcessorIndexTestResourcetype(Component):
    implements(IResourceType)
    package_id = 'processorindextest'
    resourcetype_id = 'testtype'


class TestIndex(Component):
    implements(IProcessorIndex)
    
    package_id = 'processorindextest'
    resourcetype_id = 'testtype'
    type = index.FLOAT_INDEX
    
    def eval(self, document):
        return [1,2,3]


class ProcessorIndexTest(SeisHubEnvironmentTestCase):
    def setUp(self):
        self.env.enableComponent(ProcessorIndexTestPackage)
        self.env.enableComponent(ProcessorIndexTestResourcetype)
    
    def tearDown(self):
        self.env.disableComponent(ProcessorIndexTestPackage)
        self.env.disableComponent(ProcessorIndexTestResourcetype)
    
    def testProcessorIndexRegistration(self):
        self.env.enableComponent(TestIndex)
        res = self.env.catalog.index_catalog.getIndexes('processorindextest', 
                                                        'testtype')
        self.assertEqual(len(res), 1)
        idx = res[0]
        self.assertEqual(idx.resourcetype.package.package_id, 
                         'processorindextest')
        self.assertEqual(idx.resourcetype.resourcetype_id, 'testtype')
        self.assertEqual(idx.type, index.PROCESSOR_INDEX)
        self.assertEqual(idx.options, TestIndex.__module__ + '.' +\
                         TestIndex.__name__)
        
        test_doc = newXMLDocument(RAW_XML1)
        res = idx.eval(test_doc, self.env)
        self.assertEqual(len(res), 3)
        self.assertEqual(type(res[0]), index.FloatIndexElement)
        self.assertEqual(type(res[1]), index.FloatIndexElement)
        self.assertEqual(type(res[2]), index.FloatIndexElement)
        self.assertEqual(res[0].key, 1)
        self.assertEqual(res[1].key, 2)
        self.assertEqual(res[2].key, 3)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(XmlIndexTest, 'test'))
    suite.addTest(unittest.makeSuite(ProcessorIndexTest, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')