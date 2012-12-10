# -*- coding: utf-8 -*-

from seishub.core.exceptions import InvalidObjectError
from seishub.core.util.xmlwrapper import XmlSchema, XmlTreeDoc, \
    InvalidXPathExpression, xpathNamespaceFix
import unittest


TEST_SCHEMA = """<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
<xsd:element name="a" type="AType"/>
<xsd:complexType name="AType">
    <xsd:sequence>
        <xsd:element name="b" maxOccurs="2" type="xsd:string" />
    </xsd:sequence>
</xsd:complexType>
</xsd:schema>"""

GOOD_XML = """<a><b>A string</b>
<b>Another string</b>
</a>"""
BAD_XML = """<a><b><an_element></an_element></b></a>"""

NAMESPACEFILE = """
<order xmlns="http://test.org/order" xmlns:special="http://test.org/spec">
    <billing_number>123456789</billing_number>
    <ordered_things>
      <hotel_room xmlns="http://test.org/room">
        <room_name xmlns="">Suite</room_name>
        <room_number>557</room_number>
        <special:size>50</special:size>
      </hotel_room>
    </ordered_things>
</order>
""".strip()


class XmlSchemaTest(unittest.TestCase):
    def setUp(self):
        self.test_schema = TEST_SCHEMA
        self.good_xml = GOOD_XML
        self.bad_xml = BAD_XML

    def testValidate(self):
        validDoc = XmlTreeDoc(self.good_xml)
        invalidDoc = XmlTreeDoc(self.bad_xml)
        schema = XmlSchema(self.test_schema)
        # if valid, no exception is raised
        schema.validate(validDoc)
        self.assertRaises(InvalidObjectError, schema.validate, invalidDoc)


class XmlTreeTest(unittest.TestCase):
    def testEvalXPath(self):
        tree_doc = XmlTreeDoc(xml_data=GOOD_XML)
        # an invalid expression:
        self.assertRaises(InvalidXPathExpression,
                          tree_doc.evalXPath,
                          '//')

        # a valid expression
        self.assertEquals(tree_doc.evalXPath('/a/b')[1].getStrContent(),
                          "Another string")

        # an expression, returning multiple xml elements;
        # getStrContent() concatenates all Element values:
        self.assertEquals(tree_doc.evalXPath('/a')[0].getStrContent(),
                          "<a><b>A string</b>\n<b>Another string</b>\n</a>")

        # expression containing namespaces
        ns_doc = XmlTreeDoc(xml_data=TEST_SCHEMA)
        self.assertEquals(ns_doc.evalXPath(
            '/xsd:schema/xsd:element/@name')[0].getStrContent(), "a")

    def testXPathNamespaceFix(self):
        """
        Tests the xpathNamespaceFix() function.
        """
        expr = "/{http://quakeml.org/xmlns/quakeml/1.2}quakeml"
        result = xpathNamespaceFix(expr)
        self.assertEqual(result,
            ('/ns0:quakeml', {'ns0': 'http://quakeml.org/xmlns/quakeml/1.2'}))

        expr = "/quakeml"
        result = xpathNamespaceFix(expr, 'http://quakeml.org/xmlns/bed/1.2')
        self.assertEqual(result,
            ('/default:quakeml', {'default':
                'http://quakeml.org/xmlns/bed/1.2'}))

        expr = "/{http://quakeml.org/xmlns/quakeml/1.2}quakeml/eventParameters"
        result = xpathNamespaceFix(expr, 'http://quakeml.org/xmlns/bed/1.2')
        self.assertEqual(result, ('/ns0:quakeml/default:eventParameters',
         {'default': 'http://quakeml.org/xmlns/bed/1.2',
          'ns0': 'http://quakeml.org/xmlns/quakeml/1.2'}))

    def testXPathWithNamespaces(self):
        """
        Tests the xpath evaluation function with namespaces.
        """
        doc = XmlTreeDoc(xml_data=NAMESPACEFILE)
        self.assertEqual("557", doc.evalXPath("/order/ordered_things/"
            "{http://test.org/room}hotel_room/"
            "{http://test.org/room}room_number")[0].getStrContent())
        self.assertEqual("50", doc.evalXPath("/order/ordered_things/"
            "{http://test.org/room}hotel_room/"
            "{http://test.org/spec}size")[0].getStrContent())


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(XmlSchemaTest, 'test'))
    suite.addTest(unittest.makeSuite(XmlTreeTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
