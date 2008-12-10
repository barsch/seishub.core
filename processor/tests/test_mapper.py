# -*- coding: utf-8 -*-
"""
A test suite for mapper resources.
"""

from seishub.core import Component, implements
from seishub.exceptions import SeisHubError
from seishub.packages.builtins import IPackage
from seishub.processor import GET, PUT, DELETE, POST, HEAD, Processor
from seishub.processor.interfaces import IMapperResource
from seishub.test import SeisHubEnvironmentTestCase
from twisted.web import http
import unittest


XML_DOC = """<?xml version="1.0" encoding="utf-8"?>

<testml>
  <blah1 id="3">
    <blahblah1>üöäß</blahblah1>
  </blah1>
</testml>"""


class APackage(Component):
    """
    A test package.
    """
    implements(IPackage)
    
    package_id = 'mapper-test'


class TestMapper(Component):
    """
    A test mapper.
    """
    implements(IMapperResource)
    
    mapping_url = '/mapper-test/testmapping'
    
    def process_GET(self, request):
        return "muh"
    
    def process_PUT(self, request):
        pass

    def process_DELETE(self, request):
        pass
    
    def process_POST(self, request):
        pass


class TestMapper2(Component):
    """
    Another test mapper.
    """
    implements(IMapperResource)
    
    mapping_url = '/mapper-test/testmapping2'
    
    def process_GET(self, request):
        pass


class TestMapper3(Component):
    """
    And one more test mapper.
    """
    implements(IMapperResource)
    
    mapping_url = '/mapper-test/testmapping3'
    
    def process_GET(self, request):
        pass


class TestMapper4(Component):
    """
    And one more test mapper.
    """
    implements(IMapperResource)
    
    mapping_url = '/testmapping4'
    
    def process_GET(self, request):
        return u"MÜH"


class TestMapper5(Component):
    """
    An unregistered mapper.
    """
    implements(IMapperResource)
    
    mapping_url = '/mapper-test/testmapping5'
    
    def process_GET(self, request):
        pass


class MapperTests(SeisHubEnvironmentTestCase):
    """
    A test suite for mapper resources.
    """
    def setUp(self):
        self.env.enableComponent(APackage)
        self.env.enableComponent(TestMapper)
        self.env.enableComponent(TestMapper2)
        self.env.enableComponent(TestMapper3)
        self.env.enableComponent(TestMapper4)
        self.env.tree.update()
        
    def tearDown(self):
        self.env.disableComponent(APackage)
        self.env.disableComponent(TestMapper)
        self.env.disableComponent(TestMapper2)
        self.env.disableComponent(TestMapper3)
        self.env.disableComponent(TestMapper4)
    
    def test_checkRegisteredMappers(self):
        """
        Fetch mapper resource at different levels.
        """
        proc = Processor(self.env)
        # root level
        data = proc.run(GET, '/')
        self.assertTrue('mapper-test' in data.keys())
        self.assertTrue('testmapping4' in data.keys())
        # virtual level
        proc = Processor(self.env)
        data = proc.run(GET, '/mapper-test')
        # registered mappers
        self.assertTrue('testmapping' in data.keys())
        self.assertTrue('testmapping2' in data.keys())
        self.assertTrue('testmapping3' in data.keys())
        # unregistered mapper
        self.assertFalse('testmapping5' in data.keys())
        # content
        proc = Processor(self.env)
        data = proc.run(GET, '/mapper-test/testmapping')
        self.assertEqual(data, 'muh')
        # HEAD equals GET
        data = proc.run(HEAD, '/testmapping4')
        self.assertEquals(data, 'MÜH')
    
    def test_dontReturnUnicodeFromMapper(self):
        """
        Unicodes returned from a mapper should be encoded into UTF-8 strings.
        """
        proc = Processor(self.env)
        data = proc.run(GET, '/testmapping4')
        self.assertFalse(isinstance(data, unicode))
        self.assertTrue(isinstance(data, basestring))
        self.assertEqual('MÜH', data)
    
    def test_notAllowedMethods(self):
        """
        Not allowed methods should raise an error.
        """
        proc = Processor(self.env)
        try:
            proc.run(PUT, '/testmapping4')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_ALLOWED)
        try:
            proc.run(POST, '/testmapping4')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_ALLOWED)
        try:
            proc.run(DELETE, '/testmapping4')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_ALLOWED)
    
    def test_notImplementedMethods(self):
        """
        Not implemented methods should raise an error.
        """
        proc = Processor(self.env)
        try:
            proc.run('MUH', '/testmapping4')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_IMPLEMENTED)
        try:
            proc.run('KUH', '/testmapping4')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_IMPLEMENTED)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(MapperTests, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')