# -*- coding: utf-8 -*-

"""A test suite for mapper resources."""

from seishub.core import Component, implements
from seishub.packages.builtins import IPackage
from seishub.packages.interfaces import IMapper
from seishub.processor import GET, Processor
from seishub.test import SeisHubEnvironmentTestCase
import unittest


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
    implements(IMapper)
    
    mapping_url = '/test/testmapping'
    
    def process_GET(self, request):
        return "muh"
    
    def process_PUT(self, request):
        pass

    def process_DELETE(self, request):
        pass
    
    def process_POST(self, request):
        pass


class TestMapper2(Component):
    """Another test mapper."""
    implements(IMapper)
    
    mapping_url = '/mapper-test/testmapping2'
    
    def process_GET(self, request):
        pass


class TestMapper3(Component):
    """And one more test mapper."""
    implements(IMapper)
    
    mapping_url = '/mapper-test/testmapping3'
    
    def process_GET(self, request):
        pass


class TestMapper4(Component):
    """And one more test mapper."""
    implements(IMapper)
    
    mapping_url = '/testmapping4'
    
    def process_GET(self, request):
        pass


class TestMapper5(Component):
    """An unregistered mapper."""
    implements(IMapper)
    
    mapping_url = '/mapper-test/testmapping5'
    
    def process_GET(self, request):
        pass


class MapperTests(SeisHubEnvironmentTestCase):
    """A test suite for mapper resources."""
    
    def setUp(self):
        self.env.enableComponent(APackage)
        self.env.enableComponent(TestMapper)
        self.env.enableComponent(TestMapper2)
        self.env.enableComponent(TestMapper3)
        self.env.enableComponent(TestMapper4)
        self.env.updateResourceTree()
        
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
        self.assertTrue('test' in data.keys())
        self.assertTrue('testmapping4' in data.keys())
        # virtual level
        proc = Processor(self.env)
        data = proc.run(GET, '/test')
        self.assertTrue('testmapping' in data.keys())
        # content
        proc = Processor(self.env)
        data = proc.run(GET, '/test/testmapping')
        self.assertEqual(data, 'muh')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(MapperTests, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')