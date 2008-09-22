# -*- coding: utf-8 -*-

import unittest

from seishub.util.xmlwrapper import XmlSchema, XmlTreeDoc, InvalidXPathExpression


TEST_SCHEMA="""<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
<xsd:element name="a" type="AType"/>
<xsd:complexType name="AType">
    <xsd:sequence>
        <xsd:element name="b" maxOccurs="2" type="xsd:string" />
    </xsd:sequence>
</xsd:complexType>
</xsd:schema>"""

GOOD_XML="""<a><b>A string</b>
<b>Another string</b>
</a>"""
BAD_XML="""<a><b><an_element></an_element></b></a>"""


class XmlSchemaTest(unittest.TestCase):
    def setUp(self):
        self.test_schema=TEST_SCHEMA
        self.good_xml=GOOD_XML
        self.bad_xml=BAD_XML
    
    def testValidate(self):
        validDoc=XmlTreeDoc(self.good_xml)
        invalidDoc=XmlTreeDoc(self.bad_xml)
        schema=XmlSchema(self.test_schema)
        self.assertEquals(schema.validate(validDoc),True)
        self.assertEquals(schema.validate(invalidDoc),False)
        #print invalidDoc.getErrors()


class XmlTreeTest(unittest.TestCase):
    def testEvalXPath(self):
        tree_doc=XmlTreeDoc(xml_data=GOOD_XML)
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


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(XmlSchemaTest, 'test'))
    suite.addTest(unittest.makeSuite(XmlTreeTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')