# -*- coding: utf-8 -*-
import unittest
from StringIO import StringIO

from twisted.web import http

from seishub.test import SeisHubEnvironmentTestCase
from seishub.packages.processor import Processor
from seishub.exceptions import SeisHubError
from seishub.packages.processor import PUT, POST, DELETE, GET
from seishub.core import Component, implements
from seishub.packages.builtins import IResourceType, IPackage
from seishub.packages.installer import PackageInstaller


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
        # should have at least 'package', 'property' and 'mapping' as keys
        for field in ['package', 'property', 'mapping']:
            self.assertTrue(data.has_key(field))
            self.assertTrue(isinstance(data.get(field), list))
        self.assertEquals(len(data.keys()), 3)
        # check entries in packages
        self.assertTrue('/get-test' in data.get('package'))
        self.assertTrue('/seishub' in data.get('package'))
    
    def test_getPackage(self):
        proc = Processor(self.env)
        data = proc.run(GET, '/get-test')
        # data must be a dict
        self.assertTrue(isinstance(data, dict))
        # should have 'resourcetype', 'alias', 'property' and 'mapping'
        for field in ['resourcetype', 'alias', 'property', 'mapping']:
            self.assertTrue(data.has_key(field))
            self.assertTrue(isinstance(data.get(field), list))
        self.assertEquals(len(data.keys()), 4)
        # check entries in resourcetypes - should be only 1 entry with xml
        self.assertTrue('/get-test/xml' in data.get('resourcetype'))
        self.assertEquals(len(data.get('resourcetype')), 1)
    
    def test_getResourceTypes(self):
        proc = Processor(self.env)
        # test valid GET method
        data = proc.run(GET, '/get-test/xml')
        # data must be a dict with only one entry 'resourcetype' 
        self.assertTrue(isinstance(data, dict))
        for field in ['resourcetype']:
            self.assertTrue(data.has_key(field))
            self.assertTrue(isinstance(data.get(field), list))
        self.assertEquals(len(data.keys()), 1)
        # check entries in resourcetypes
        self.assertTrue('/get-test/xml/vc' in data.get('resourcetype'))
        self.assertTrue('/get-test/xml/notvc' in data.get('resourcetype'))
    
    def test_dontHijackResources(self):
        """Don't hijack resources from different packages - see #65."""
        # deinstall resource type 2 and install resource type 1
        self.env.disableComponent(AResourceType2)
        self.env.disableComponent(AVersionControlledResourceType)
        self.env.enableComponent(AResourceType)
        proc = Processor(self.env)
        proc.run(PUT, '/get-test/xml/notvc/1', StringIO(XML_DOC))
        # disable resource type 1
        self.env.disableComponent(AResourceType)
        # install resource type 2
        self.env.enableComponent(AResourceType2)
        PackageInstaller.install(self.env)
        # try to fetch existing resource from disabled resource type 1
        try:
            proc.run(GET, '/get-test/xml/notvc/1')
            self.fail("Expected ProcessorError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # try to fetch non existing resource from enabled resource type 2
        try:
            proc.run(GET, '/get-test2/xml/notvc/muh')
            self.fail("Expected ProcessorError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # try to fetch non existing resource from enabled resource type 2
        try:
            proc.run(GET, '/get-test2/xml/notvc/1')
            self.fail("Expected ProcessorError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        self.env.enableComponent(AResourceType)
        proc.run(DELETE, '/get-test/xml/notvc/1')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ProcessorGETTest, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')