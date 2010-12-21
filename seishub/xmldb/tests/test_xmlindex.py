# -*- coding: utf-8 -*-

from datetime import datetime
from obspy.core import UTCDateTime
from seishub.exceptions import SeisHubError
from seishub.test import SeisHubEnvironmentTestCase
from seishub.xmldb import index
from seishub.xmldb.index import NumericIndexElement, XmlIndex
from seishub.xmldb.resource import XmlDocument, newXMLDocument
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
        si = XmlIndex(self.rt1, xpath="/station/station_code")
        # index with multiple nodes key result:
        mi = XmlIndex(self.rt1, xpath="/station/XY/paramXY")
        # index which does not fit on test resource
        ni = XmlIndex(self.rt1, xpath="/station/network")

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
        self.assertEquals(res[0].index, ni)
        self.assertEquals(res[0].document, test_doc)
        self.assertFalse(res[0].key, None)

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

    def test_DateTimeIndex(self):
        """
        Tests indexing of datetimes.
        """
        # setup 
        dt = datetime(2008, 10, 23, 11, 53, 12, 54000)
        dt2 = datetime(2008, 10, 23, 11, 53, 12)
        dt3 = datetime(2008, 10, 23)
        dt4 = datetime(2008, 10, 23, 11)
        dt5 = datetime(2008, 10, 23, 11 , 53)
        # ISO 8601
        idx = XmlIndex(self.rt1, "/station/creation_date",
                       index.DATETIME_INDEX)
        timestr = dt.strftime("%Y%m%dT%H:%M:%S") + ".054000"
        doc = newXMLDocument(RAW_XML1 % (timestr, ""))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, dt)
        # ISO 8601 w/ minus
        idx = XmlIndex(self.rt1, "/station/creation_date",
                       index.DATETIME_INDEX)
        timestr = dt.strftime("%Y-%m-%dT%H:%M:%S") + ".054000"
        doc = newXMLDocument(RAW_XML1 % (timestr, ""))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, dt)
        # ISO 8601 w/ time zone
        idx = XmlIndex(self.rt1, "/station/creation_date",
                       index.DATETIME_INDEX)
        timestr = dt.strftime("%Y%m%dT%H:%M:%S") + ".054000Z"
        doc = newXMLDocument(RAW_XML1 % (timestr, ""))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, dt)
        # ISO 8601 w/o T
        idx = XmlIndex(self.rt1, "/station/creation_date",
                       index.DATETIME_INDEX)
        timestr = dt.strftime("%Y%m%d %H:%M:%S") + ".054000"
        doc = newXMLDocument(RAW_XML1 % (timestr, ""))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, dt)
        # ISO 8601 w/o milliseconds 
        idx = XmlIndex(self.rt1, "/station/creation_date",
                       index.DATETIME_INDEX)
        timestr = dt2.strftime("%Y%m%dT%H:%M:%S")
        doc = newXMLDocument(RAW_XML1 % (timestr, ""))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, dt2)
        # ISO 8601 w/o time - defaults to 00:00:00
        idx = XmlIndex(self.rt1, "/station/creation_date",
                       index.DATETIME_INDEX)
        timestr = dt3.strftime("%Y-%m-%d")
        doc = newXMLDocument(RAW_XML1 % (timestr, ""))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, dt3)
        # ISO 8601 w/o minutes - defaults to :00:00
        idx = XmlIndex(self.rt1, "/station/creation_date",
                       index.DATETIME_INDEX)
        timestr = dt4.strftime("%Y-%m-%dT%H")
        doc = newXMLDocument(RAW_XML1 % (timestr, ""))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, dt4)
        # ISO 8601 w/o seconds - defaults to :00
        idx = XmlIndex(self.rt1, "/station/creation_date",
                       index.DATETIME_INDEX)
        timestr = dt5.strftime("%Y-%m-%dT%H:%M")
        doc = newXMLDocument(RAW_XML1 % (timestr, ""))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, dt5)
        # with custom format
        # microseconds are ignored since not supported by strftime()
        idx = XmlIndex(self.rt1, "/station/creation_date",
                       index.DATETIME_INDEX, "%H:%M:%S - %Y%m%d")
        timestr = dt.strftime("%H:%M:%S - %Y%m%d")
        doc = newXMLDocument(RAW_XML1 % (timestr, ""))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, dt.replace(microsecond=0))

    def test_TimestampIndex(self):
        """
        Tests indexing of timestamps.
        """
        # w/ microseconds
        dt = UTCDateTime(2008, 10, 23, 11, 53, 12, 54000)
        idx = XmlIndex(self.rt1, "/station/creation_date",
                       index.TIMESTAMP_INDEX)
        timestr = "%f" % dt.timestamp
        doc = newXMLDocument(RAW_XML1 % (timestr, ""))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, dt)
        # w/o microseconds
        dt = UTCDateTime(2008, 10, 23, 11, 53, 12)
        idx = XmlIndex(self.rt1, "/station/creation_date",
                       index.TIMESTAMP_INDEX)
        timestr = "%f" % dt.timestamp
        doc = newXMLDocument(RAW_XML1 % (timestr, ""))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, dt)
        # negative timestamp works too
        dt = UTCDateTime(1969, 12, 31, 23, 36, 39, 500000)
        idx = XmlIndex(self.rt1, "/station/creation_date",
                       index.TIMESTAMP_INDEX)
        timestr = "%f" % dt.timestamp
        doc = newXMLDocument(RAW_XML1 % (timestr, ""))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, dt)

    def test_DateIndex(self):
        """
        Tests indexing of dates.
        """
        dt = datetime(2008, 10, 10, 11, 53, 0, 54000)
        # ISO 8601 w/o minus
        idx = XmlIndex(self.rt1, "/station/creation_date", index.DATE_INDEX)
        timestr = dt.strftime("%Y%m%d")
        doc = newXMLDocument(RAW_XML1 % (timestr, ""))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, dt.date())
        # ISO 8601 w/ minus
        idx = XmlIndex(self.rt1, "/station/creation_date", index.DATE_INDEX)
        timestr = dt.strftime("%Y-%m-%d")
        doc = newXMLDocument(RAW_XML1 % (timestr, ""))
        res = idx.eval(doc, self.env)[0]
        self.assertEqual(res.key, dt.date())
        # custom format
        idx = XmlIndex(self.rt1, "/station/creation_date", index.DATE_INDEX,
                       options="%d.%m.%Y")
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
                        group_path="/station/XY")
        res = idx1.eval(doc, self.env)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0].key, '1')
        self.assertEqual(res[0].group_pos, 0)
        self.assertEqual(res[1].key, '4')
        self.assertEqual(res[1].group_pos, 1)

        idx2 = XmlIndex(self.rt1, "/station/XY/Y", index.NUMERIC_INDEX,
                        group_path="/station/XY")
        res = idx2.eval(doc, self.env)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0].key, '2')
        self.assertEqual(res[0].group_pos, 0)
        self.assertEqual(res[1].key, '5')
        self.assertEqual(res[1].group_pos, 1)

        idx3 = XmlIndex(self.rt1, "/station/XY/Y/@id", index.NUMERIC_INDEX,
                        group_path="/station/XY")
        res = idx3.eval(doc, self.env)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0].key, '1')
        self.assertEqual(res[0].group_pos, 0)
        self.assertEqual(res[1].key, '2')
        self.assertEqual(res[1].group_pos, 1)

        idx4 = XmlIndex(self.rt1, "/station/XY/Z/value", index.NUMERIC_INDEX,
                        group_path="/station/XY")
        res = idx4.eval(doc, self.env)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0].key, '3')
        self.assertEqual(res[0].group_pos, 0)
        self.assertEqual(res[1].key, '6')
        self.assertEqual(res[1].group_pos, 1)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(XmlIndexTest, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
