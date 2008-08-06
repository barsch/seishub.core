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
    def setUp(self):
        self.env.registry.db_registerPackage('testpackage0', '1.0')
        self.env.registry.db_registerResourceType('weapon', 'testpackage0',  
                                                  '1.0')
    def tearDown(self):
        self.env.registry.db_deleteResourceType('testpackage0', 'weapon')
        self.env.registry.db_deletePackage('testpackage0')
        
    def test_split_uri(self):
        reg = self.env.registry.schemas
        self.assertEqual(reg._split_uri('/package/resourcetype/type'), 
                         ('package', 'resourcetype', 'type'))
        self.assertEqual(reg._split_uri('/package/type'), 
                         ('package', None, 'type'))
    
    def test_InMemoryRegistry(self):
        packages = self.env.registry.packages
        for p in packages:
            assert self.env.registry.packages.get(p).package_id == p
        resourcetypes = self.env.registry.resourcetypes
        rt_ids = resourcetypes.get('seishub')
        for id in rt_ids:
            rt_object = resourcetypes.get('seishub', id)
            assert rt_object.resourcetype_id == id
            
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
        self.assertEqual(schema[0].package.package_id, 'testpackage0')
        self.assertEqual(schema[0].resourcetype.resourcetype_id, 'weapon')
        self.assertEqual(schema[0].type, 'xsd')
        # get schema resource
        res = schema[0].resource
        self.assertEqual(res.document.data, TEST_SCHEMA)
        self.assertEqual(res.package.package_id, 'seishub')
        self.assertEqual(res.resourcetype.resourcetype_id, 'schema')
        # by uri
        schema = self.env.registry.schemas.get(uri='/testpackage0/weapon/xsd')
        self.assertEqual(schema[0].package.package_id, 'testpackage0')
        self.assertEqual(schema[0].resourcetype.resourcetype_id, 'weapon')
        self.assertEqual(schema[0].type, 'xsd')
        res = schema[0].resource
        self.assertEqual(res.document.data, TEST_SCHEMA)
        self.assertEqual(res.package.package_id, 'seishub')
        self.assertEqual(res.resourcetype.resourcetype_id, 'schema')
        
        # add a second schema without resourcetype
        self.env.registry.schemas.register('testpackage0', None, 'xsd', 
                                           TEST_SCHEMA)
        # get schemas for package 'testpackage0'        
        schemas = self.env.registry.schemas.get(package_id = 'testpackage0')
        self.assertEqual(len(schemas),1)
        self.assertEqual(schemas[0].package.package_id, 'testpackage0')
        self.assertEqual(schemas[0].resourcetype.resourcetype_id, None)
        self.assertEqual(schemas[0].type, 'xsd')
        #by uri
        schemas = self.env.registry.schemas.get(uri = '/testpackage0/xsd')
        self.assertEqual(len(schemas),1)
        self.assertEqual(schemas[0].package.package_id, 'testpackage0')
        self.assertEqual(schemas[0].resourcetype.resourcetype_id, None)
        self.assertEqual(schemas[0].type, 'xsd')
#        # try to delete multiple schemas
#        self.assertRaises(SeisHubError, self.env.registry.schemas.delete, 
#                          uri = '/testpackage0')
        # get all
        schemas = self.env.registry.schemas
        self.assertEqual(len(schemas), 2)
        
        # delete first added schema
        self.env.registry.schemas.delete(schema[0].package.package_id,
                                         schema[0].resourcetype.resourcetype_id,
                                         schema[0].type)
        schema = self.env.registry.schemas.get(package_id = 'testpackage0')
        self.assertEqual(schema[0].package.package_id, 'testpackage0')
        self.assertEqual(schema[0].resourcetype.resourcetype_id, None)
        self.assertEqual(schema[0].type, 'xsd')
        # delete by uri
        self.env.registry.schemas.delete(uri = '/testpackage0/xsd')

    def test_StylesheetRegistry(self):
        self.env.registry.stylesheets.register('testpackage0', 'weapon', 'xhtml', 
                                               TEST_SCHEMA)
        stylesheet = self.env.registry.stylesheets.get\
                                                    (package_id='testpackage0',
                                                    resourcetype_id = 'weapon')
        self.assertEqual(stylesheet[0].package.package_id, 'testpackage0')
        self.assertEqual(stylesheet[0].resourcetype.resourcetype_id, 'weapon')
        self.assertEqual(stylesheet[0].type, 'xhtml')
        # get stylesheet resource
        res = stylesheet[0].resource
        self.assertEqual(res.document.data, TEST_SCHEMA)
        self.assertEqual(res.package.package_id, 'seishub')
        self.assertEqual(res.resourcetype.resourcetype_id, 'stylesheet')
        self.env.registry.stylesheets.delete(
                                    stylesheet[0].package.package_id,
                                    stylesheet[0].resourcetype.resourcetype_id,
                                    stylesheet[0].type
                                    )
        
    def test_AliasRegistry(self):
        self.env.registry.aliases.register('testpackage0', 'weapon', 
                                           'arch1', 
                                           '/weapon[./name = Bogen]')
        alias = self.env.registry.aliases.get(package_id = 'testpackage0',
                                              resourcetype_id = 'weapon',
                                              name = 'arch1')
        self.assertEqual(len(alias), 1)
        self.assertEqual(alias[0].package.package_id, 'testpackage0')
        self.assertEqual(alias[0].resourcetype.resourcetype_id, 'weapon')
        self.assertEqual(alias[0].expr, '/weapon[./name = Bogen]')
        self.assertEqual(alias[0].getQuery(), 
                         '/testpackage0/weapon/weapon[./name = Bogen]')
        #get by uri:
        alias = self.env.registry.aliases.get(uri='/testpackage0/weapon/arch1')
        self.assertEqual(len(alias), 1)
        self.assertEqual(alias[0].package.package_id, 'testpackage0')
        self.assertEqual(alias[0].resourcetype.resourcetype_id, 'weapon')
        self.assertEqual(alias[0].expr, '/weapon[./name = Bogen]')
        self.assertEqual(alias[0].getQuery(), 
                         '/testpackage0/weapon/weapon[./name = Bogen]')
        
        self.env.registry.aliases.register('testpackage0', None, 
                                           'arch2', 
                                           '/*[./name = Bogen]')
        alias = self.env.registry.aliases.get(package_id = 'testpackage0')
        self.assertEqual(len(alias),1)
        self.assertEqual(alias[0].package.package_id, 'testpackage0')
        self.assertEqual(alias[0].resourcetype.resourcetype_id, None)
        self.assertEqual(alias[0].expr, '/*[./name = Bogen]')
        self.assertEqual(alias[0].getQuery(), 
                         '/testpackage0/*/*[./name = Bogen]')
        
        # get all
        all = self.env.registry.aliases
        assert len(all) >= 2
        
        # delete
        self.env.registry.aliases.delete('testpackage0', 'weapon', 'arch1')
        alias = self.env.registry.aliases.get(package_id = 'testpackage0',
                                              resourcetype_id = 'weapon',
                                              name = 'arch1')
        self.assertEquals(alias, list())
        self.env.registry.aliases.delete('testpackage0', '', 'arch2')
        alias = self.env.registry.aliases.get(package_id = 'testpackage0')
        self.assertEquals(alias, list())

from seishub.core import Component, implements
from seishub.packages.builtin import IResourceType, IPackage
from seishub.packages.installer import registerStylesheet, registerAlias

class AResourceType(Component):
    implements(IResourceType, IPackage)
    package_id = 'atestpackage'
    resourcetype_id = 'aresourcetype'
    registerStylesheet('aformat','data/weapon.xsd')
    registerAlias('analias','/resourceroot[./a/predicate/expression]',
                  limit = 10, order_by = {'/path/to/element':'ASC'})

class FromFilesystemTest(SeisHubEnvironmentTestCase):
    def __init__(self, *args, **kwargs):
        SeisHubEnvironmentTestCase.__init__(self, *args, **kwargs)
        
    def testRegisterStylesheet(self):
        # note: schema registry uses the same functionality and is therefore
        # not tested seperately
        # invalid class (no package id/resourcetype id)
        try:
            class Foo():
                registerStylesheet('blah','blah')
        except Exception, e:
            assert isinstance(e, AssertionError)
        
        class Bar():
            package_id = 'atestpackage'
            resourcetype_id = 'aresourcetype'
            registerStylesheet('xhtml','path/to/file')
        p = os.path.join(self.env.config.path,'seishub','packages','tests',
                         'path/to/file')
        assert {'filename': p, 'type': 'xhtml'} in Bar._registry_stylesheets
        
    def testRegisterAlias(self):       
        # no package id/resourcetype id
        try:
            class Foo():
                registerAlias('blah','blah')
        except Exception, e:
            assert isinstance(e, AssertionError)
        
        class Bar():
            package_id = 'testpackage'
            resourcetype_id = 'resourcetype'
            registerAlias('otheralias','/resourceroot[./other/predicate/expression]',
                          limit = 10, order_by = {'/path/to/other/element':'ASC'})

        assert {'name': 'otheralias', 
                'expr': '/resourceroot[./other/predicate/expression]', 
                'limit': 10, 
                'order_by': {'/path/to/other/element': 'ASC'}
                } in Bar._registry_aliases
    
    def testAutoInstaller(self):
        from seishub.packages.installer import PackageInstaller
        self.env.enableComponent(AResourceType)
        PackageInstaller.install(self.env)
        # stylesheet
        stylesheet = self.registry.stylesheets.get('atestpackage', 'aresourcetype',
                                            'aformat')
        self.assertEqual(len(stylesheet), 1)
        p = os.path.join(self.env.config.path,'seishub','packages','tests',
                         'data','weapon.xsd')
        self.assertEqual(stylesheet[0].resource.document.data, file(p).read())
        # alias
        alias = self.registry.aliases.get('atestpackage', 'aresourcetype', 
                                        'analias')
        self.assertEqual(len(alias), 1)
        self.assertEqual(alias[0].expr,'/resourceroot[./a/predicate/expression]')
        
        # clean up
        self.registry.aliases.delete(alias[0].package.package_id,
                                     alias[0].resourcetype.resourcetype_id,
                                     alias[0].name)
        self.registry.stylesheets.delete(stylesheet[0].package.package_id,
                                         stylesheet[0].resourcetype.resourcetype_id,
                                         stylesheet[0].type)
        self.env.disableComponent(AResourceType)
        PackageInstaller.cleanup(self.env)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PackageRegistryTest, 'test'))
    suite.addTest(unittest.makeSuite(FromFilesystemTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')