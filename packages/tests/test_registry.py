import unittest
import os

from seishub.core import SeisHubError
from seishub.test import SeisHubEnvironmentTestCase

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

class PackageRegistryTest(SeisHubEnvironmentTestCase):
    def test_InMemoryRegistry(self):
        packages = self.env.registry.packages
        for p in packages:
            assert self.env.registry.packages.get(p).package_id == p
            
    def test_DatabaseRegistry(self):
        # regsiter a package
        self.env.registry.db_registerPackage('db_registered_package', '1.0')
        package = self.env.registry.db_getPackages('db_registered_package')[0]
        self.assertEqual(package.package_id, 'db_registered_package')
        self.assertEqual(package.version, '1.0')
        self.env.registry.db_deletePackage('db_registered_package')
        package = self.env.registry.db_getPackages('db_registered_package')
        assert package == list()
        
        # regsiter a resourcetype
        self.env.registry.db_registerPackage('db_registered_package', '1.0')
        self.env.registry.db_registerResourceType('db_regsitered_resourcetype', 
                                               'db_registered_package', 
                                               '1.0', True)
        restype = self.env.registry.db_getResourceTypes('db_registered_package',
                                                    'db_regsitered_resourcetype')[0]
        self.assertEqual(restype.package.package_id, 'db_registered_package')
        self.assertEqual(restype.resourcetype_id, 'db_regsitered_resourcetype')
        self.assertEqual(restype.version, '1.0')
        self.assertEqual(restype.version_control, True)
        
        # try to delete package although resourcetype belonging to package is
        # still there
        # XXX: fails with sqlite
        self.assertRaises(SeisHubError, 
                          self.env.registry.db_deletePackage, 
                          'db_registered_package')
        
        self.env.registry.db_deleteResourceType('db_registered_package',
                                             'db_regsitered_resourcetype')
        restype = self.env.registry.db_getResourceTypes('db_registered_package',
                                                  'db_regsitered_resourcetype')
        assert restype == list()
        self.env.registry.db_deletePackage('db_registered_package')
        
        # XXX: check deletion constraint with schemas/aliases/stylesheets/catalog objects
        

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
        self.env.registry.schemas.delete(schema[0].package_id,
                                         schema[0].resourcetype_id,
                                         schema[0].type)
        schema = self.env.registry.schemas.get(package_id = 'testpackage0')
        self.assertEqual(schema[0].package_id, 'testpackage0')
        self.assertEqual(schema[0].type, 'xsd')
        self.env.registry.schemas.delete(schema[0].package_id,
                                         schema[0].resourcetype_id,
                                         schema[0].type)

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
        self.env.registry.stylesheets.delete(stylesheet[0].package_id,
                                             stylesheet[0].resourcetype_id,
                                             stylesheet[0].type)
        
    def test_AliasRegistry(self):
        self.env.registry.aliases.register('testpackage0', 'weapon', 
                                           'arch1', 
                                           '/weapon[./name = Bogen]')
        alias = self.env.registry.aliases.get(package_id = 'testpackage0',
                                              resourcetype_id = 'weapon',
                                              name = 'arch1')
        self.assertEqual(alias[0].package_id, 'testpackage0')
        self.assertEqual(alias[0].resourcetype_id, 'weapon')
        self.assertEqual(alias[0].expr, '/weapon[./name = Bogen]')
        self.assertEqual(alias[0].getQuery(), 
                         '/testpackage0/weapon/weapon[./name = Bogen]')
        
        self.env.registry.aliases.register('testpackage0', None, 
                                           'arch2', 
                                           '/*[./name = Bogen]')
        alias = self.env.registry.aliases.get(package_id = 'testpackage0')
        self.assertEqual(len(alias),1)
        self.assertEqual(alias[0].package_id, 'testpackage0')
        self.assertEqual(alias[0].resourcetype_id, None)
        self.assertEqual(alias[0].expr, '/*[./name = Bogen]')
        self.assertEqual(alias[0].getQuery(), 
                         '/testpackage0/*/*[./name = Bogen]')
        
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

from seishub.core import Component, implements
from seishub.packages.builtin import IResourceType, IPackage
from seishub.packages.installer import registerStylesheet, registerAlias

class AResourceType(Component):
    implements(IResourceType, IPackage)
    package_id = 'testpackage'
    resourcetype_id = 'aresourcetype'
    registerStylesheet('aformat','data/weapon.xsd')
    registerAlias('analias','/resourceroot[./a/predicate/expression]',
                  limit = 10, order_by = {'/path/to/element':'ASC'})

class FromFilesystemTest(SeisHubEnvironmentTestCase):
    def __init__(self, *args, **kwargs):
        SeisHubEnvironmentTestCase.__init__(self, *args, **kwargs)
        self.env.enableComponent(AResourceType)
        
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
        assert {'filename': p, 'type': 'xhtml'} in Bar._registry_stylesheets
        
        res = self.registry.stylesheets.get('testpackage', 'aresourcetype',
                                            'aformat')
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].resource.data, file('data/weapon.xsd').read())
        
        # clean up
        self.registry.stylesheets.delete(res[0].package_id,
                                         res[0].resourcetype_id,
                                         res[0].type)
        
        
    def testRegisterAlias(self):       
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

        assert {'name': 'analias', 
                'expr': '/resourceroot[./a/predicate/expression]', 
                'limit': 10, 
                'order_by': {'/path/to/element': 'ASC'}
                } in Bar._registry_aliases
        
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