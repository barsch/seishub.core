import unittest

from seishub.test import SeisHubTestCase

TEST_SCHEMA="""<?xml version="1.0"?>
<xs:schema elementFormDefault="qualified"
    xmlns:xs="http://www.w3.org/2001/XMLSchema">

    <xs:element name="armor">
        <xs:complexType>
            <xs:attribute name="lang" type="xs:string"/>
            <xs:sequence>
                <xs:element name="name" type="xs:string" use="required" />
                <xs:element name="properties" type="xs:string" />
                <xs:element name="headAC" type="xs:string" />
                <xs:element name="torsoAC" type="xs:string" />
                <xs:element name="legsAC" type="xs:string" />
                <xs:element name="load" type="xs:string" />
            </xs:sequence>
        </xs:complexType>
    </xs:element>

</xs:schema>
"""

class PackageRegistryTest(SeisHubTestCase):
    def test_SchemaRegistry(self):
        self.env.registry.schemas.register('degenesis', 'weapon', 'xsd', 
                                           TEST_SCHEMA)
        schema = self.env.registry.schemas.get(package_id = 'degenesis',
                                               resourcetype_id = 'weapon')
        self.assertEqual(schema.package_id, 'degenesis')
        self.assertEqual(schema.resourcetype_id, 'weapon')
        self.assertEqual(schema.type, 'xsd')
        # get schema resource
        res = schema.resource
        self.assertEqual(res.data, TEST_SCHEMA)
        # add a second schema without resourcetype
        self.env.registry.schemas.register('degenesis', None, 'xsd', 
                                           TEST_SCHEMA)
        # get schemas for package 'degenesis'        
        schemas = self.env.registry.schemas.get(package_id = 'degenesis')
        self.assertEqual(len(schemas),2)
        # delete first added schema
        self.env.registry.schemas.delete(schema.uid)
        schema = self.env.registry.schemas.get(package_id = 'degenesis')
        self.assertEqual(schema.package_id, 'degenesis')
        self.assertEqual(schema.type, 'xsd')
        self.env.registry.schemas.delete(schema.uid)

    def test_StylesheetRegistry(self):
        self.env.registry.stylesheets.register('degenesis', 'weapon', 'xhtml', 
                                               TEST_SCHEMA)
        stylesheet = self.env.registry.stylesheets.get(package_id='degenesis')
        self.assertEqual(stylesheet.package_id, 'degenesis')
        self.assertEqual(stylesheet.resourcetype_id, 'weapon')
        self.assertEqual(stylesheet.type, 'xhtml')
        self.env.registry.stylesheets.delete(stylesheet.uid)
        
    def test_AliasRegistry(self):
        self.env.registry.aliases.register('degenesis', 'weapon', 
                                           'arch', 
                                           '/degenesis/weapon[./name = Bogen]')
        alias = self.env.registry.aliases.get(name = 'arch')
        self.assertEqual(alias.package_id, 'degenesis')
        self.assertEqual(alias.resourcetype_id, 'weapon')
        self.assertEqual(alias.expr, '/degenesis/weapon[./name = Bogen]')
        self.env.registry.aliases.delete('degenesis', 'weapon', 'arch')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PackageRegistryTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')