# -*- coding: utf-8 -*-
import unittest
from StringIO import StringIO

from twisted.web import http

from seishub.test import SeisHubEnvironmentTestCase
from seishub.packages.processor import Processor
from seishub.exceptions import SeisHubError
from seishub.packages.processor import PUT, POST, DELETE, GET, MOVE
from seishub.core import Component, implements
from seishub.packages.builtins import IResourceType, IPackage
from seishub.packages.interfaces import IGETMapper, IPUTMapper, \
                                        IDELETEMapper, IPOSTMapper
from seishub.packages.installer import PackageInstaller


XML_DOC = """<?xml version="1.0" encoding="utf-8"?>

<testml>
  <blah1 id="3">
    <blahblah1>üöäß</blahblah1>
  </blah1>
</testml>"""


class APackage(Component):
    """A test package."""
    implements(IPackage)
    
    package_id = 'mapper-test'


class TestMapper(Component):
    """A test mapper."""
    implements(IGETMapper, IPUTMapper, IDELETEMapper, IPOSTMapper)
    
    package_id = 'mapper-test'
    mapping_url = '/test/testmapping'
    
    def processGET(self, request):
        pass
    
    def processPUT(self, request):
        pass

    def processDELETE(self, request):
        pass
    
    def processPOST(self, request):
        pass


class TestMapper2(Component):
    """Another test mapper."""
    implements(IGETMapper)
    
    package_id = 'mapper-test'
    mapping_url = '/mapper-test/testmapping2'
    
    def processGET(self, request):
        pass


class TestMapper3(Component):
    """And one more test mapper."""
    implements(IGETMapper)
    
    package_id = 'mapper-test'
    mapping_url = '/mapper-test/testmapping3'
    
    def processGET(self, request):
        pass


class TestMapper4(Component):
    """And one more test mapper."""
    implements(IGETMapper)
    
    package_id = 'mapper-test'
    mapping_url = '/testmapping4'
    
    def processGET(self, request):
        pass


class TestMapper5(Component):
    """An unregistered mapper."""
    implements(IGETMapper)
    
    package_id = 'mapper-test'
    mapping_url = '/mapper-test/testmapping5'
    
    def processGET(self, request):
        pass


class ProcessorMapperTest(SeisHubEnvironmentTestCase):
    """Test case for processing of mappers."""
    
    def setUp(self):
        self.env.enableComponent(APackage)
        self.env.enableComponent(TestMapper)
        self.env.enableComponent(TestMapper2)
        self.env.enableComponent(TestMapper3)
        self.env.enableComponent(TestMapper4)
        PackageInstaller.install(self.env)
        
    def tearDown(self):
        self.env.disableComponent(APackage)
        self.env.disableComponent(TestMapper)
        self.env.disableComponent(TestMapper2)
        self.env.disableComponent(TestMapper3)
        self.env.disableComponent(TestMapper4)
    
    def test_getRootMappers(self):
        proc = Processor(self.env)
        # root level
        data = proc.run(GET, '/')
        uris = data.get('mapping')
        self.assertTrue('/test' in uris)
        self.assertTrue('/testmapping4' in uris)
        # virtual level
        proc = Processor(self.env)
        data = proc.run(GET, '/test')
        uris = data.get('mapping')
        self.assertTrue('/test/testmapping' in uris)
    
    def test_getResourceTypeMappers(self):
        proc = Processor(self.env)
        data = proc.run(GET, '/mapper-test')
        uris = data.get('mapping')
        self.assertTrue('/mapper-test/testmapping2' in uris)
        self.assertTrue('/mapper-test/testmapping3' in uris)
        self.assertFalse('/mapper-test/testmapping5' in uris)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ProcessorMapperTest, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')