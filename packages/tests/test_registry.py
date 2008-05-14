import unittest

from seishub.test import SeisHubTestCase

class PackageRegistryTest(SeisHubTestCase):
    def test_SchemaRegistry(self):
        self.env.registry.schemas.registerSchema('degenesis', 'weapon', 'xsd', 
                                                 '/seishub/xsd/blah')
        schema = self.env.registry.schemas.getSchema(uri = '/seishub/xsd/blah')
        self.assertEqual(schema.package_id, 'degenesis')
        self.assertEqual(schema.resourcetype_id, 'weapon')
        self.assertEqual(schema.type, 'xsd')
        self.env.registry.schemas.deleteSchema(uri = '/seishub/xsd/blah')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PackageRegistryTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')