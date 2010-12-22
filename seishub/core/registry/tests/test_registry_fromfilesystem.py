# -*- coding: utf-8 -*-

from seishub.core.core import Component, implements
from seishub.core.packages.installer import registerSchema, registerStylesheet
from seishub.core.packages.interfaces import IResourceType, IPackage
from seishub.core.test import SeisHubEnvironmentTestCase
import os
import unittest


class APackage(Component):
    implements(IPackage)

    package_id = 'atestpackage'
    registerStylesheet('data' + os.sep + 'resourcelist_json.xslt',
                       'resourcelist')

class AResourceType(Component):
    implements(IResourceType)

    package_id = 'atestpackage'
    resourcetype_id = 'aresourcetype'
    registerStylesheet('data' + os.sep + 'resourcelist_json.xslt', 'aformat')


class PackageRegistryFilesystemTest(SeisHubEnvironmentTestCase):
    def __init__(self, *args, **kwargs):
        SeisHubEnvironmentTestCase.__init__(self, *args, **kwargs)

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_registerSchema(self):
        try:
            class Foo():
                """invalid no package"""
                registerSchema('blah', 'blah')
        except Exception, e:
            assert isinstance(e, AssertionError)

        try:
            class Bar():
                """invalid, no resourcetype"""
                package_id = 'atestpackage'
                registerSchema('path/to/file1', 'xhtml')
        except Exception, e:
            assert isinstance(e, AssertionError)

        class FooBar():
            """valid, package and resourcetype specific"""
            package_id = 'atestpackage'
            resourcetype_id = 'aresourcetype'
            registerSchema('path/to/file2', 'xhtml')

        p2 = os.path.join(self.env.getPackagePath(), 'seishub', 'core',
                          'registry', 'tests', 'path/to/file2')
        assert {'filename': p2, 'type': 'xhtml'} in\
                FooBar._registry_schemas

    def test_registerStylesheet(self):
        # invalid class (no package id)
        try:
            class Foo():
                """invalid no package"""
                registerStylesheet('blah', 'blah')
        except Exception, e:
            assert isinstance(e, AssertionError)

        class Bar():
            """valid, package specific"""
            package_id = 'atestpackage'
            registerStylesheet('path/to/file1', 'xhtml')

        class FooBar():
            """valid, package and resourcetype specific"""
            package_id = 'atestpackage'
            resourcetype_id = 'aresourcetype'
            registerStylesheet('path/to/file2', 'xhtml')

        p1 = os.path.join(self.env.getPackagePath(), 'seishub', 'core',
                          'registry', 'tests', 'path/to/file1')
        p2 = os.path.join(self.env.getPackagePath(), 'seishub', 'core',
                          'registry', 'tests', 'path/to/file2')
        assert {'filename': p1, 'type': 'xhtml'} in Bar._registry_stylesheets
        assert {'filename': p2, 'type': 'xhtml'} in\
                FooBar._registry_stylesheets

    def test_autoInstaller(self):
        from seishub.core.packages.installer import PackageInstaller
        self.env.enableComponent(APackage)
        self.env.enableComponent(AResourceType)
        # stylesheets
        stylesheet = self.registry.stylesheets.get('atestpackage',
                                                   'aresourcetype', 'aformat')
        self.assertEqual(len(stylesheet), 1)
        p = os.path.join(self.env.getPackagePath(), 'seishub', 'core',
                         'registry', 'tests', 'data', 'resourcelist_json.xslt')
        self.assertEqual(stylesheet[0].resource.document.data, file(p).read())
        stylesheet = self.registry.stylesheets.get('atestpackage', None,
                                                   'resourcelist')
        self.assertEqual(len(stylesheet), 1)
        p = os.path.join(self.env.getPackagePath(), 'seishub', 'core',
                         'registry', 'tests', 'data', 'resourcelist_json.xslt')
        self.assertEqual(stylesheet[0].resource.document.data, file(p).read())
        self.registry.stylesheets.delete(stylesheet[0].package.package_id,
                                         stylesheet[0].resourcetype.\
                                            resourcetype_id,
                                         stylesheet[0].type)
        self.env.disableComponent(AResourceType)
        PackageInstaller.cleanup(self.env)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PackageRegistryFilesystemTest, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
