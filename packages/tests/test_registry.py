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
        self.assertEqual(schema[0].package_id, 'degenesis')
        self.assertEqual(schema[0].resourcetype_id, 'weapon')
        self.assertEqual(schema[0].type, 'xsd')
        # get schema resource
        res = schema[0].resource
        self.assertEqual(res.data, TEST_SCHEMA)
        # add a second schema without resourcetype
        self.env.registry.schemas.register('degenesis', None, 'xsd', 
                                           TEST_SCHEMA)
        # get schemas for package 'degenesis'        
        schemas = self.env.registry.schemas.get(package_id = 'degenesis')
        self.assertEqual(len(schemas),2)
        # delete first added schema
        self.env.registry.schemas.delete(schema[0].uid)
        schema = self.env.registry.schemas.get(package_id = 'degenesis')
        self.assertEqual(schema[0].package_id, 'degenesis')
        self.assertEqual(schema[0].type, 'xsd')
        self.env.registry.schemas.delete(schema[0].uid)

    def test_StylesheetRegistry(self):
        self.env.registry.stylesheets.register('degenesis', 'weapon', 'xhtml', 
                                               TEST_SCHEMA)
        stylesheet = self.env.registry.stylesheets.get(package_id='degenesis')
        self.assertEqual(stylesheet[0].package_id, 'degenesis')
        self.assertEqual(stylesheet[0].resourcetype_id, 'weapon')
        self.assertEqual(stylesheet[0].type, 'xhtml')
        self.env.registry.stylesheets.delete(stylesheet[0].uid)
        
    def test_AliasRegistry(self):
        self.env.registry.aliases.register('degenesis', 'weapon', 
                                           'arch1', 
                                           '/degenesis/weapon[./name = Bogen]')
        alias = self.env.registry.aliases.get(package_id = 'degenesis',
                                              resourcetype_id = 'weapon',
                                              name = 'arch1')
        self.assertEqual(alias[0].package_id, 'degenesis')
        self.assertEqual(alias[0].resourcetype_id, 'weapon')
        self.assertEqual(alias[0].expr, '/degenesis/weapon[./name = Bogen]')
        
        self.env.registry.aliases.register('degenesis', None, 
                                           'arch2', 
                                           '/degenesis/*/*[./name = Bogen]')
        alias = self.env.registry.aliases.get(package_id = 'degenesis')
        self.assertEqual(len(alias),1)
        self.assertEqual(alias[0].package_id, 'degenesis')
        self.assertEqual(alias[0].resourcetype_id, None)
        self.assertEqual(alias[0].expr, '/degenesis/*/*[./name = Bogen]')
        
        self.env.registry.aliases.delete('degenesis', 'weapon', 'arch1')
        alias = self.env.registry.aliases.get(package_id = 'degenesis',
                                              resourcetype_id = 'weapon',
                                              name = 'arch1')
        self.assertEquals(len(alias),0)
        self.env.registry.aliases.delete('degenesis', '', 'arch2')
        alias = self.env.registry.aliases.get(package_id = 'degenesis')
        self.assertEquals(len(alias),0)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PackageRegistryTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')