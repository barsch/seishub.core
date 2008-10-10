# -*- coding: utf-8 -*-
import unittest
from StringIO import StringIO

from twisted.web import http

from seishub.test import SeisHubEnvironmentTestCase
from seishub.packages.processor import Processor, ProcessorError
from seishub.packages.processor import PUT, POST, DELETE, GET, MOVE
from seishub.packages.processor import MAX_URI_LENGTH, ALLOWED_HTTP_METHODS
from seishub.packages.processor import NOT_IMPLEMENTED_HTTP_METHODS
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
    mapping_url = '/test2/testmapping'
    
    def processGET(self, request):
        pass


class TestMapper3(Component):
    """And one more test mapper."""
    implements(IGETMapper)
    
    mapping_url = '/test/vc/muh'
    
    def processGET(self, request):
        pass


class ProcessorMapperTest(SeisHubEnvironmentTestCase):
    """Test case for processing of mappers."""
    
    def setUp(self):
        self.env.enableComponent(APackage)
        self.env.enableComponent(TestMapper)
        self.env.enableComponent(TestMapper2)
        PackageInstaller.install(self.env)
        
    def tearDown(self):
        self.env.disableComponent(APackage)
        self.env.disableComponent(TestMapper)
        self.env.disableComponent(TestMapper2)
    
    def test_failes(self):
        pass


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ProcessorMapperTest, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')