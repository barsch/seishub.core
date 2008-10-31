# -*- coding: utf-8 -*-
import unittest
from StringIO import StringIO

from twisted.web import http

from seishub.test import SeisHubEnvironmentTestCase
from seishub.packages.processor import Processor
from seishub.exceptions import SeisHubError
from seishub.packages.processor import PUT, GET
from seishub.core import Component, implements
from seishub.packages.builtins import IResourceType, IPackage


XML_DOC = """<?xml version="1.0" encoding="utf-8"?>

<testml>
  <blah1 id="3">
    <blahblah1>üöäß</blahblah1>
  </blah1>
</testml>"""


class AResourceType(Component):
    """A test package and resource type."""
    implements(IResourceType, IPackage)
    
    package_id = 'test'
    resourcetype_id = 'rt'
    version_control = False


class AResourceType2(Component):
    """Another test package and resource type."""
    implements(IResourceType, IPackage)
    
    package_id = 'test2'
    resourcetype_id = 'rt'
    version_control = False


class PackageRegistryTestSuite(SeisHubEnvironmentTestCase):
    """A test suite for the package registry."""
    
    def test_shouldNotFail(self):
        """XXX: BUG - see ticket #65 - This test should not fail!"""
        # install resource 1
        self.env.enableComponent(AResourceType)
        proc = Processor(self.env)
        proc.run(PUT, '/test/xml/rt/1', StringIO(XML_DOC))
        # disable resource type 2
        self.env.disableComponent(AResourceType)
        # install resource 2
        self.env.enableComponent(AResourceType2)
        # try to fetch existing resource from disabled resource type 1
        try:
            proc.run(GET, '/test1/xml/rt/1')
            self.fail("Expected ProcessorError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # try to fetch non existing resource from enabled resource type 2
        try:
            proc.run(GET, '/test2/xml/rt/muh')
            self.fail("Expected ProcessorError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # try to fetch non existing resource from enabled resource type 2
        # XXX: BUG - see ticket #65
        # there was no resource added to /test2/rt yet!
        try:
            proc.run(GET, '/test2/xml/rt/1')
            self.fail("Expected ProcessorError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PackageRegistryTestSuite, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')