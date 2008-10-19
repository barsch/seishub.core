# -*- coding: utf-8 -*-
import unittest
import os

from seishub.core import SeisHubError
from seishub.test import SeisHubEnvironmentTestCase
from seishub.core import Component, implements
from seishub.packages.builtins import IResourceType, IPackage
from seishub.packages.installer import registerStylesheet, registerAlias 
from seishub.packages.installer import registerSchema
from seishub.packages.interfaces import IGETMapper, IPUTMapper
from seishub.xmldb.resource import Resource, newXMLDocument


TEST_SCHEMA="""<xs:schema elementFormDefault="qualified"
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

</xs:schema>"""

TEST_STYLESHEET = """<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
    xmlns:xlink="http://www.w3.org/1999/xlink" exclude-result-prefixes="xlink"
    version="1.0">
    
    <xsl:output method="text" encoding="utf-8"
        media-type="application/json" />
    
    <xsl:template match="/seishub">
        <xsl:text>{</xsl:text>

            <xsl:if test="//package">
                <xsl:text>"package":[</xsl:text>
                <xsl:for-each select="//package">

                    <xsl:text>"</xsl:text>
                    <xsl:value-of select="@xlink:href" />
                    <xsl:text>"</xsl:text>
                    <xsl:if test="not (position()=last())">
                        <xsl:text>,</xsl:text>
                    </xsl:if>
                </xsl:for-each>

                <xsl:text>],</xsl:text>
            </xsl:if>

            <xsl:if test="//resourcetype">
                <xsl:text>"resourcetype":[</xsl:text>
                <xsl:for-each select="//resourcetype">
                    <xsl:text>"</xsl:text>
                    <xsl:value-of select="@xlink:href" />

                    <xsl:text>"</xsl:text>
                    <xsl:if test="not (position()=last())">
                        <xsl:text>,</xsl:text>
                    </xsl:if>
                </xsl:for-each>
                <xsl:text>],</xsl:text>
            </xsl:if>

            <xsl:if test="//mapping">
                <xsl:text>"mapping":[</xsl:text>
                <xsl:for-each select="//mapping">
                    <xsl:text>"</xsl:text>
                    <xsl:value-of select="@xlink:href" />
                    <xsl:text>"</xsl:text>
                    <xsl:if test="not (position()=last())">

                        <xsl:text>,</xsl:text>
                    </xsl:if>
                </xsl:for-each>
                <xsl:text>],</xsl:text>
            </xsl:if>

            <xsl:if test="//alias">
                <xsl:text>"alias":[</xsl:text>

                <xsl:for-each select="//alias">
                    <xsl:text>"</xsl:text>
                    <xsl:value-of select="@xlink:href" />
                    <xsl:text>"</xsl:text>
                    <xsl:if test="not (position()=last())">
                        <xsl:text>,</xsl:text>
                    </xsl:if>

                </xsl:for-each>
                <xsl:text>],</xsl:text>
            </xsl:if>

            <xsl:if test="//index">
                <xsl:text>"index":[</xsl:text>
                <xsl:for-each select="//index">
                    <xsl:text>"</xsl:text>

                    <xsl:value-of select="@xlink:href" />
                    <xsl:text>"</xsl:text>
                    <xsl:if test="not (position()=last())">
                        <xsl:text>,</xsl:text>
                    </xsl:if>
                </xsl:for-each>
                <xsl:text>],</xsl:text>

            </xsl:if>

            <xsl:if test="//resource">
                <xsl:text>"resource":[</xsl:text>
                <xsl:for-each select="//resource">
                    <xsl:text>"</xsl:text>
                    <xsl:value-of select="@xlink:href" />
                    <xsl:text>"</xsl:text>

                    <xsl:if test="not (position()=last())">
                        <xsl:text>,</xsl:text>
                    </xsl:if>
                </xsl:for-each>
                <xsl:text>],</xsl:text>
            </xsl:if>

        <xsl:text>}</xsl:text>

    </xsl:template>

</xsl:stylesheet>"""

TEST_RESLIST = """<seishub xml:base="http://localhost:8080" xmlns:xlink="http://www.w3.org/1999/xlink">
    <mapping xlink:type="simple" xlink:href="/seishub/schema/browser">browser</mapping>
    <resource xlink:type="simple" xlink:href="/seishub/schema/3">/seishub/schema/3</resource>
    <resource xlink:type="simple" xlink:href="/seishub/schema/4">/seishub/schema/4</resource>
</seishub>"""

class PackageRegistryTest(SeisHubEnvironmentTestCase):
    def setUp(self):
        self.env.registry.db_registerPackage('testpackage0', '1.0')
        self.env.registry.db_registerResourceType('testpackage0', 'weapon',   
                                                  '1.0')
        self.env.registry.db_registerResourceType('testpackage0', 'armor',   
                                                  '1.0')
        
    def tearDown(self):
        self.env.registry.db_deleteResourceType('testpackage0', 'weapon')
        self.env.registry.db_deleteResourceType('testpackage0', 'armor')
        self.env.registry.db_deletePackage('testpackage0')
        
    def test_split_uri(self):
        reg = self.env.registry.stylesheets
        self.assertEqual(reg._split_uri('/package/resourcetype/type'), 
                         ('package', 'resourcetype', 'type'))
        self.assertEqual(reg._split_uri('/package/type'), 
                         ('package', None, 'type'))
        reg = self.env.registry.schemas
        self.assertEqual(reg._split_uri('/package/resourcetype/type'), 
                         ('package', 'resourcetype', 'type'))
        self.assertEqual(reg._split_uri('/package/resourcetype'), 
                         ('package', 'resourcetype', None))
        
    
    def test_InMemoryRegistry(self):
        packages = self.env.registry.getPackageIds()
        for p in packages:
            assert self.env.registry.getPackage(p).package_id == p
            resourcetypes = self.env.registry.getResourceTypeIds(p)
            for rt in resourcetypes:
                rt_object = self.env.registry.getResourceType(p ,rt)
                assert rt_object.resourcetype_id == rt
    
    def test_DatabaseRegistry(self):
        # regsiter a package
        self.env.registry.db_registerPackage('db_registered_package', '1.0')
        package = self.env.registry.db_getPackages('db_registered_package')[0]
        self.assertEqual(package.package_id, 'db_registered_package')
        self.assertEqual(package.version, '1.0')
        self.env.registry.db_deletePackage('db_registered_package')
        package = self.env.registry.db_getPackages('db_registered_package')
        assert package == list()
        
        # register a resourcetype
        self.env.registry.db_registerPackage('db_registered_package', '1.0')
        self.env.registry.db_registerResourceType('db_registered_package',
                                                  'db_regsitered_resourcetype',  
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
        self.env.registry.schemas.register('testpackage0', 'armor', 'xsd', 
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
        
        # schema without resourcetype is not allowed
        self.assertRaises(SeisHubError, self.env.registry.schemas.register, 
                          'testpackage0', None, 'xsd', TEST_SCHEMA)
        
        # get schemas for package 'testpackage0'        
        schemas = self.env.registry.schemas.get(package_id = 'testpackage0')
        self.assertEqual(len(schemas), 2)
        self.assertEqual(schemas[0].package.package_id, 'testpackage0')
        self.assertEqual(schemas[0].resourcetype.resourcetype_id, 'weapon')
        self.assertEqual(schemas[0].type, 'xsd')
        self.assertEqual(schemas[1].package.package_id, 'testpackage0')
        self.assertEqual(schemas[1].resourcetype.resourcetype_id, 'armor')
        self.assertEqual(schemas[1].type, 'xsd')
        
        # get by uri
        # no schemas with package testpackage0 and resourcetype xsd
        schemas = self.env.registry.schemas.get(uri = '/testpackage0/xsd')
        self.assertEqual(len(schemas), 0)
        # one schemas with package testpackage0 and resourcetype weapon
        schemas = self.env.registry.schemas.get(uri = '/testpackage0/weapon')
        self.assertEqual(len(schemas), 1)
        # one schemas with package testpackage0, resourcetype weapon and type xsd
        schemas = self.env.registry.schemas.get(uri =\
                                                '/testpackage0/weapon/xsd')
        self.assertEqual(len(schemas), 1)

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
        self.assertEqual(len(schema), 1)
        self.assertEqual(schema[0].resourcetype.resourcetype_id, 'armor')
        
        # delete by uri
        self.env.registry.schemas.delete(uri = '/testpackage0/armor')
        schema = self.env.registry.schemas.get(package_id = 'testpackage0')
        self.assertEqual(len(schema), 0)

    def test_StylesheetRegistry(self):
        # with resourcetype
        self.env.registry.stylesheets.register('testpackage0', 'weapon', 
                                               'xhtml', TEST_STYLESHEET)
        # without resourcetype
        self.env.registry.stylesheets.register('testpackage0', None, 
                                               'xhtml', TEST_STYLESHEET)
        
        stylesheet = self.env.registry.stylesheets.get\
                                                    (package_id='testpackage0',
                                                    resourcetype_id = 'weapon')
        self.assertEqual(len(stylesheet), 1)
        self.assertEqual(stylesheet[0].package.package_id, 'testpackage0')
        self.assertEqual(stylesheet[0].resourcetype.resourcetype_id, 'weapon')
        self.assertEqual(stylesheet[0].type, 'xhtml')
        self.assertEquals(stylesheet[0].content_type, 'application/json')
        
        stylesheet_nort = self.env.registry.stylesheets.get(package_id =\
                                                            'testpackage0')
        self.assertEqual(len(stylesheet_nort), 1)
        self.assertEqual(stylesheet_nort[0].package.package_id, 'testpackage0')
        self.assertEqual(stylesheet_nort[0].resourcetype.resourcetype_id, None)
        
        # transformations
        res_list = Resource(document = newXMLDocument(TEST_RESLIST))
        self.assertEquals(stylesheet[0].transform(res_list), 
                          '{"mapping":["/seishub/schema/browser"],"resource"'+\
                          ':["/seishub/schema/3","/seishub/schema/4"],}')
        self.assertEquals(stylesheet[0].transform(TEST_RESLIST),
                          '{"mapping":["/seishub/schema/browser"],"resource"'+\
                          ':["/seishub/schema/3","/seishub/schema/4"],}')
        
        # get stylesheet resource
        res = stylesheet[0].resource
        self.assertEqual(res.document.data, TEST_STYLESHEET)
        self.assertEqual(res.package.package_id, 'seishub')
        self.assertEqual(res.resourcetype.resourcetype_id, 'stylesheet')
        
        # remove
        self.env.registry.stylesheets.delete(
                                    stylesheet[0].package.package_id,
                                    stylesheet[0].resourcetype.resourcetype_id,
                                    stylesheet[0].type
                                    )
        stylesheet = self.env.registry.stylesheets.get\
                                                    (package_id='testpackage0',
                                                    resourcetype_id = 'weapon')
        self.assertEqual(len(stylesheet), 0)
        self.env.registry.stylesheets.delete('testpackage0', None, 'xhtml')
        stylesheet_nort = self.env.registry.stylesheets.get(package_id =\
                                                            'testpackage0')
        self.assertEqual(len(stylesheet_nort), 0)
        
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


class APackage(Component):
    implements(IPackage)
    
    package_id = 'atestpackage'
    registerStylesheet('resourcelist','data/resourcelist_json.xslt')

class AResourceType(Component):
    implements(IResourceType)
    
    package_id = 'atestpackage'
    resourcetype_id = 'aresourcetype'
    registerStylesheet('aformat','data/weapon.xsd')
    registerAlias('analias','/resourceroot[./a/predicate/expression]',
                  limit = 10, order_by = {'/path/to/element':'ASC'})
    

class TestMapper(Component):
    implements(IGETMapper, IPUTMapper)
    
    mapping_url = '/test/testmapping'
    
    def processGET(self, request):
        pass
    
    def processPUT(self, request):
        pass


class TestMapper2(Component):
    implements(IGETMapper)
    
    mapping_url = '/test/testmapping/two'
    
    def processGET(self, request):
        pass
    

class TestMapper3(Component):
    implements(IGETMapper)
    
    mapping_url = '/test/three/testmapping'
    
    def processGET(self, request):
        pass


class FromFilesystemTest(SeisHubEnvironmentTestCase):
    def __init__(self, *args, **kwargs):
        SeisHubEnvironmentTestCase.__init__(self, *args, **kwargs)
        
    def setUp(self):
        self.env.enableComponent(TestMapper)
        self.env.enableComponent(TestMapper2)
        self.env.enableComponent(TestMapper3)
        
    def tearDown(self):
        self.env.disableComponent(TestMapper)
        self.env.disableComponent(TestMapper2)
        self.env.disableComponent(TestMapper3)
        
    def testMapperRegistry(self):
        self.env.disableComponent(TestMapper)
        assert '/test/testmapping' not in self.env.registry.mappers.keys()
        self.env.enableComponent(TestMapper)
        # get with exact url
        m = self.env.registry.mappers.get('/test/testmapping', 'GET')
        self.assertEquals(type(m[0]), TestMapper)
        m = self.env.registry.mappers.get('/test/testmapping/two', 'GET')
        self.assertEquals(type(m[0]), TestMapper2)
        m = self.env.registry.mappers.get('/test/three/testmapping', 'GET')
        self.assertEquals(type(m[0]), TestMapper3)
        # url longer than mapper url
        m = self.env.registry.mappers.get('/test/testmapping/nottwo', 'GET')
        self.assertEquals(type(m[0]), TestMapper)
        m = self.env.registry.mappers.get('/test/testmapping/two/nottwo', 
                                           'GET')
        self.assertEquals(type(m[0]), TestMapper2)
        # no mapper
        m = self.env.registry.mappers.get('/test/three')
        self.assertEquals(len(m), 0)
        # without method
        m = self.env.registry.mappers.get('/test/testmapping/two')
        m = map(type, m)
        assert TestMapper2 in m
        assert TestMapper in m
        
        all = self.env.registry.mappers
        assert '/test/testmapping' in all
        self.assertEqual(all['/test/testmapping'], ['PUT', 'GET'])
        mapper = self.env.registry.mappers.get('/test/testmapping', 'GET')
        assert TestMapper(self.env) is mapper[0]
        methods = self.env.registry.mappers.getMethods('/test/testmapping')
        self.assertEqual(methods, ['PUT', 'GET'])
        # get mappers of a certain method
        a = self.env.registry.mappers.get(method='GET')
        b = self.env.registry.mappers.getMappings(method='GET')
        self.assertEquals(a, b)
    
    def testRegisterSchema(self):
        try:
            class Foo():
                """invalid no package"""
                registerSchema('blah','blah')
        except Exception, e:
            assert isinstance(e, AssertionError)
            
        try:
            class Bar():
                """invalid, no resourcetype"""
                package_id = 'atestpackage'
                registerSchema('xhtml','path/to/file1')
        except Exception, e:
            assert isinstance(e, AssertionError)
            
        class FooBar():
            """valid, package and resourcetype specific"""
            package_id = 'atestpackage'
            resourcetype_id = 'aresourcetype'
            registerSchema('xhtml','path/to/file2')
        
        p2 = os.path.join(self.env.config.path,'seishub','packages','tests',
                         'path/to/file2')
        assert {'filename': p2, 'type': 'xhtml'} in\
                FooBar._registry_schemas
                
    def testRegisterStylesheet(self):
        # invalid class (no package id)
        try:
            class Foo():
                """invalid no package"""
                registerStylesheet('blah','blah')
        except Exception, e:
            assert isinstance(e, AssertionError)
        
        class Bar():
            """valid, package specific"""
            package_id = 'atestpackage'
            registerStylesheet('xhtml','path/to/file1')
            
        class FooBar():
            """valid, package and resourcetype specific"""
            package_id = 'atestpackage'
            resourcetype_id = 'aresourcetype'
            registerStylesheet('xhtml','path/to/file2')
        
        p0 = os.path.join(self.env.config.path,'seishub','packages','tests',
                         'blah')
        p1 = os.path.join(self.env.config.path,'seishub','packages','tests',
                         'path/to/file1')
        p2 = os.path.join(self.env.config.path,'seishub','packages','tests',
                         'path/to/file2')
        assert {'filename': p1, 'type': 'xhtml'} in Bar._registry_stylesheets
        assert {'filename': p2, 'type': 'xhtml'} in\
                FooBar._registry_stylesheets
        
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
        self.env.enableComponent(APackage)
        self.env.enableComponent(AResourceType)
        PackageInstaller.install(self.env)
        
        # stylesheets
        stylesheet = self.registry.stylesheets.get('atestpackage', 
                                                   'aresourcetype', 'aformat')
        self.assertEqual(len(stylesheet), 1)
        p = os.path.join(self.env.config.path,'seishub','packages','tests',
                         'data','weapon.xsd')
        self.assertEqual(stylesheet[0].resource.document.data, file(p).read())
        
        stylesheet = self.registry.stylesheets.get('atestpackage', None, 
                                                   'resourcelist')
        self.assertEqual(len(stylesheet), 1)
        p = os.path.join(self.env.config.path,'seishub','packages','tests',
                         'data','resourcelist_json.xslt')
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
                                         stylesheet[0].resourcetype.\
                                            resourcetype_id,
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