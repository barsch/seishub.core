# -*- coding: utf-8 -*-

import unittest

from seishub.test import SeisHubTestCase
from seishub.xmldb.validator import XmlSchemaValidator


class XmlValidatorTest(SeisHubTestCase):
    
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


def suite():
    return unittest.makeSuite(XmlValidatorTest, 'test')

if __name__ == '__main__':
    unittest.main(defaultTest='suite')