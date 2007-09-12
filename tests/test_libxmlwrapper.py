from twisted.trial.unittest import TestCase

from seishub.libxmlwrapper import XmlSchema, XmlTreeDoc

class XmlSchemaTest(TestCase):
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
    
    def testValidate(self):
        validDoc=XmlTreeDoc(self.good_xml)
        invalidDoc=XmlTreeDoc(self.bad_xml)
        schema=XmlSchema(self.test_schema)
        self.assertEquals(schema.validate(validDoc),True)
        self.assertEquals(schema.validate(invalidDoc),False)
        print invalidDoc.getErrors()
        
        