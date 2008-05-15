import unittest

from seishub.test import SeisHubTestCase

class PackageRegistryTest(SeisHubTestCase):
    def test_SchemaRegistry(self):
        self.env.registry.schemas.register('degenesis', 'weapon', 'xsd', 
                                                 '/seishub/xsd/blah')
        schema = self.env.registry.schemas.get(uri = '/seishub/xsd/blah')
        self.assertEqual(schema.package_id, 'degenesis')
        self.assertEqual(schema.resourcetype_id, 'weapon')
        self.assertEqual(schema.type, 'xsd')
        self.env.registry.schemas.delete(uri = '/seishub/xsd/blah')
        
        self.env.registry.schemas.register('degenesis', None, 'xsd', 
                                           '/seishub/xsd/degenesis')
        schema = self.env.registry.schemas.get(uri = '/seishub/xsd/degenesis')
        self.assertEqual(schema.package_id, 'degenesis')
        self.assertEqual(schema.type, 'xsd')
        self.env.registry.schemas.delete(uri = '/seishub/xsd/degenesis')

    def test_StylesheetRegistry(self):
        self.env.registry.stylesheets.register('degenesis', 'weapon', 'xhtml', 
                                               '/seishub/xslt/degenesis/weapon')
        stylesheet = self.env.registry.stylesheets.get(uri = '/seishub/xslt/degenesis/weapon')
        self.assertEqual(stylesheet.package_id, 'degenesis')
        self.assertEqual(stylesheet.resourcetype_id, 'weapon')
        self.assertEqual(stylesheet.type, 'xhtml')
        self.env.registry.stylesheets.delete(uri = '/seishub/xslt/degenesis/weapon')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PackageRegistryTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')