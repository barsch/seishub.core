import unittest

from seishub.test import SeisHubTestCase

class PackageRegistryTest(SeisHubTestCase):
    def test_registerSchema(self):
        self.env.registry.schemas.registerSchema('degenesis', 'weapon', 'xsd', 
                                                 '/seishub/xsd/blah')

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PackageRegistryTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')