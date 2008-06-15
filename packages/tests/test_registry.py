import unittest
import os

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
        self.env.registry.schemas.register('testpackage0', 'weapon', 'xsd', 
                                           TEST_SCHEMA)
        schema = self.env.registry.schemas.get(package_id = 'testpackage0',
                                               resourcetype_id = 'weapon')
        self.assertEqual(schema[0].package_id, 'testpackage0')
        self.assertEqual(schema[0].resourcetype_id, 'weapon')
        self.assertEqual(schema[0].type, 'xsd')
        # get schema resource
        res = schema[0].resource
        self.assertEqual(res.data, TEST_SCHEMA)
        self.assertEqual(res.info.package_id, 'seishub')
        self.assertEqual(res.info.resourcetype_id, 'schema')
        # add a second schema without resourcetype
        self.env.registry.schemas.register('testpackage0', None, 'xsd', 
                                           TEST_SCHEMA)
        # get schemas for package 'testpackage0'        
        schemas = self.env.registry.schemas.get(package_id = 'testpackage0')
        self.assertEqual(len(schemas),2)
        # delete first added schema
        self.env.registry.schemas.delete(schema[0].uid)
        schema = self.env.registry.schemas.get(package_id = 'testpackage0')
        self.assertEqual(schema[0].package_id, 'testpackage0')
        self.assertEqual(schema[0].type, 'xsd')
        self.env.registry.schemas.delete(schema[0].uid)

    def test_StylesheetRegistry(self):
        self.env.registry.stylesheets.register('testpackage0', 'weapon', 'xhtml', 
                                               TEST_SCHEMA)
        stylesheet = self.env.registry.stylesheets.get(package_id='testpackage0')
        self.assertEqual(stylesheet[0].package_id, 'testpackage0')
        self.assertEqual(stylesheet[0].resourcetype_id, 'weapon')
        self.assertEqual(stylesheet[0].type, 'xhtml')
        # get stylesheet resource
        res = stylesheet[0].resource
        self.assertEqual(res.data, TEST_SCHEMA)
        self.assertEqual(res.info.package_id, 'seishub')
        self.assertEqual(res.info.resourcetype_id, 'stylesheet')
        self.env.registry.stylesheets.delete(stylesheet[0].uid)
        
    def test_AliasRegistry(self):
        self.env.registry.aliases.register('testpackage0', 'weapon', 
                                           'arch1', 
                                           '/testpackage0/weapon[./name = Bogen]')
        alias = self.env.registry.aliases.get(package_id = 'testpackage0',
                                              resourcetype_id = 'weapon',
                                              name = 'arch1')
        self.assertEqual(alias[0].package_id, 'testpackage0')
        self.assertEqual(alias[0].resourcetype_id, 'weapon')
        self.assertEqual(alias[0].expr, '/testpackage0/weapon[./name = Bogen]')
        
        self.env.registry.aliases.register('testpackage0', None, 
                                           'arch2', 
                                           '/testpackage0/*/*[./name = Bogen]')
        alias = self.env.registry.aliases.get(package_id = 'testpackage0')
        self.assertEqual(len(alias),1)
        self.assertEqual(alias[0].package_id, 'testpackage0')
        self.assertEqual(alias[0].resourcetype_id, None)
        self.assertEqual(alias[0].expr, '/testpackage0/*/*[./name = Bogen]')
        
        # get all
        all = self.env.registry.aliases.get()
        assert len(all) >= 2
        
        # delete
        self.env.registry.aliases.delete('testpackage0', 'weapon', 'arch1')
        alias = self.env.registry.aliases.get(package_id = 'testpackage0',
                                              resourcetype_id = 'weapon',
                                              name = 'arch1')
        self.assertEquals(len(alias), 0)
        self.env.registry.aliases.delete('testpackage0', '', 'arch2')
        alias = self.env.registry.aliases.get(package_id = 'testpackage0')
        self.assertEquals(len(alias), 0)

from seishub.packages.registry import registerStylesheet
from seishub.packages.registry import registerAlias

class AResourceType():
    package_id = 'testpackage'
    resourcetype_id = 'aresourcetype'
    registerStylesheet('aformat','data/weapon.xsd')
    registerAlias('analias','/resourceroot[./a/predicate/expression]',
                  limit = 10, order_by = {'/path/to/element':'ASC'})

class FromFilesystemTest(SeisHubTestCase):
    def testRegisterStylesheet(self):
        # note: schema registry uses the same functionality and is therefore
        # not tested seperately
        from seishub.packages.registry import StylesheetRegistry
        
        # invalid class (no package id/resourcetype id)
        try:
            class Foo():
                registerStylesheet('blah','blah')
        except Exception, e:
            assert isinstance(e, AssertionError)
        
        class Bar():
            package_id = 'testpackage'
            resourcetype_id = 'aresourcetype'
            registerStylesheet('xhtml','path/to/file')
        p = os.path.join(self.env.config.path,'seishub','packages','tests',
                         'path/to/file')
        assert ['testpackage', 'aresourcetype', p, 'xhtml']\
               in StylesheetRegistry._registry
        
        res = self.registry.stylesheets.get('testpackage', 'aresourcetype',
                                            'aformat')
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].resource.data, file('data/weapon.xsd').read())
        
        # clean up
        self.registry.stylesheets.delete(res[0].uid)
        
        
    def testRegisterAlias(self):
        from seishub.packages.registry import AliasRegistry        
        # no package id/resourcetype id
        try:
            class Foo():
                registerAlias('blah','blah')
        except Exception, e:
            assert isinstance(e, AssertionError)
        
        class Bar():
            package_id = 'testpackage'
            resourcetype_id = 'aresourcetype'
            registerAlias('analias','/resourceroot[./a/predicate/expression]',
                          limit = 10, order_by = {'/path/to/element':'ASC'})

        assert ['testpackage', 'aresourcetype', 'analias', 
                '/resourceroot[./a/predicate/expression]', 
                10, {'/path/to/element': 'ASC'}] in AliasRegistry._registry
        
        res = self.registry.aliases.get('testpackage', 'aresourcetype', 
                                        'analias')
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].expr,'/resourceroot[./a/predicate/expression]')
        
        # clean up
        self.registry.aliases.delete(res[0].package_id,
                                     res[0].resourcetype_id,
                                     res[0].name)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PackageRegistryTest, 'test'))
    suite.addTest(unittest.makeSuite(FromFilesystemTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')