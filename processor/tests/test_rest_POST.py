# -*- coding: utf-8 -*-

"""A test suite for POST request on REST resources."""

from seishub.core import Component, implements
from seishub.packages.builtins import IResourceType, IPackage
from seishub.processor.resources import RESTFolder
from seishub.test import SeisHubEnvironmentTestCase
import unittest


XML_DOC = """<?xml version="1.0" encoding="UTF-8"?>

<testml>
  <blah1 id="3">
    <blahblah1>üöäß</blahblah1>
  </blah1>
</testml>"""


class AResourceType(Component):
    """A non versioned test resource type."""
    implements(IResourceType, IPackage)
    
    package_id = 'post-test'
    resourcetype_id = 'notvc'
    version_control = False


class AVersionControlledResourceType(Component):
    """A version controlled test resource type."""
    implements(IResourceType, IPackage)
    
    package_id = 'post-test'
    resourcetype_id = 'vc'
    version_control = True


class RestPOSTTests(SeisHubEnvironmentTestCase):
    """A test suite for POST request on REST resources."""
    
    def setUp(self):
        self.env.enableComponent(AVersionControlledResourceType)
        self.env.enableComponent(AResourceType)
        self.env.tree = RESTFolder()
    
    def tearDown(self):
        self.env.disableComponent(AVersionControlledResourceType)
        self.env.disableComponent(AResourceType)
    
    def test_processRoot(self):
        pass


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(RestPOSTTests, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')