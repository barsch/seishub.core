# -*- coding: utf-8 -*-

from twisted.trial.unittest import TestCase

from seishub.validator import XmlSchemaValidator


class XmlValidatorTest(TestCase):
    
    def setUp(self):
        self.test_schema="""<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
<xsd:element name="a" type="AType"/>
<xsd:complexType name="AType">
    <xsd:sequence>
        <xsd:element name="b" maxOccurs="2" type="xsd:string" />
    </xsd:sequence>
</xsd:complexType>
</xsd:schema>"""
        self.good_xml="""<a><b>A string</b></a>"""
        self.bad_xml="""<a><b><an_element></an_element></b></a>"""
    
    def testValidateXml(self):
        valid=XmlSchemaValidator(self.test_schema,self.good_xml).validate()
        self.assertEquals(valid,1)
        invalid=XmlSchemaValidator(self.test_schema,self.bad_xml).validate()
        self.assertEquals(invalid,0)
        