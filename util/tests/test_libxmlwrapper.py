# -*- coding: utf-8 -*-

from twisted.trial.unittest import TestCase

from seishub.util.libxmlwrapper import XmlSchema, XmlTreeDoc, InvalidXPathExpression

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

class XmlSchemaTest(TestCase):
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
        
class XmlTreeTest(TestCase):
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
                          "A string\nAnother string\n")
        