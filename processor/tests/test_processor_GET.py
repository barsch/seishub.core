# -*- coding: utf-8 -*-

from StringIO import StringIO
from seishub.core import Component, implements
from seishub.exceptions import SeisHubError
from seishub.packages.builtins import IResourceType, IPackage
from seishub.packages.installer import PackageInstaller
from seishub.processor import PUT, DELETE, GET, Processor
from seishub.test import SeisHubEnvironmentTestCase
from twisted.web import http
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
    
    package_id = 'get-test'
    resourcetype_id = 'notvc'
    version_control = False


class AResourceType2(Component):
    """Another test package and resource type."""
    implements(IResourceType, IPackage)
    
    package_id = 'get-test2'
    resourcetype_id = 'notvc'
    version_control = False


class AVersionControlledResourceType(Component):
    """A version controlled test resource type."""
    implements(IResourceType, IPackage)
    
    package_id = 'get-test'
    resourcetype_id = 'vc'
    version_control = True


class ProcessorGETTest(SeisHubEnvironmentTestCase):
    """Test case for HTTP GET processing."""
    
    def setUp(self):
        self.env.enableComponent(AVersionControlledResourceType)
        self.env.enableComponent(AResourceType)
    
    def tearDown(self):
        self.env.disableComponent(AVersionControlledResourceType)
        self.env.disableComponent(AResourceType)
    
    def test_getRootWithSlash(self):
        proc = Processor(self.env)
        data = proc.run(GET, '/')
        # data must be a dict
        self.assertTrue(isinstance(data, dict))
        # should have at least 'xml' root
        self.assertTrue(data.has_key('xml'))
    
    def test_getPackage(self):
        proc = Processor(self.env)
        data = proc.run(GET, '/xml')
        # data must be a dict
        self.assertTrue(isinstance(data, dict))
        # check entries in package
        self.assertTrue(data.has_key('get-test'))
        self.assertTrue(data.has_key('seishub'))
    
    def test_getResourceTypes(self):
        proc = Processor(self.env)
        data = proc.run(GET, '/xml/get-test')
        # data must be a dict
        self.assertTrue(isinstance(data, dict))
        # check entries in package
        self.assertTrue(data.has_key('notvc'))
        self.assertTrue(data.has_key('vc'))
    
    def test_dontHijackResources(self):
        """Don't hijack resources from different packages - see #65."""
        # deinstall resource type 2 and install resource type 1
        self.env.disableComponent(AResourceType2)
        self.env.disableComponent(AVersionControlledResourceType)
        self.env.enableComponent(AResourceType)
        proc = Processor(self.env)
        proc.run(PUT, '/xml/get-test/notvc/1', StringIO(XML_DOC))
        # disable resource type 1
        self.env.disableComponent(AResourceType)
        # install resource type 2
        self.env.enableComponent(AResourceType2)
        PackageInstaller.install(self.env)
        # try to fetch existing resource from disabled resource type 1
        try:
            proc.run(GET, '/xml/get-test/notvc/1')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # try to fetch non existing resource from enabled resource type 2
        try:
            proc.run(GET, '/xml/get-test2/notvc/muh')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # try to fetch non existing resource from enabled resource type 2
        try:
            proc.run(GET, '/xml/get-test2/notvc/1')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        self.env.enableComponent(AResourceType)
        proc.run(DELETE, '/xml/get-test/notvc/1')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ProcessorGETTest, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')