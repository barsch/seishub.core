# -*- coding: utf-8 -*-
"""
A test suite for PUT request on REST resources.
"""

from StringIO import StringIO
from seishub.core.core import Component, implements
from seishub.core.packages.builtins import IResourceType, IPackage
from seishub.core.processor import POST, PUT, DELETE, Processor
from seishub.core.processor.resources import RESTFolder
from seishub.core.test import SeisHubEnvironmentTestCase
import glob
import os
import unittest


XML_DOC = """<?xml version="1.0" encoding="UTF-8"?>

<testml>
  <blah1 id="3">
    <blahblah1>üöäß</blahblah1>
  </blah1>
</testml>"""


class AResourceType(Component):
    """
    A non versioned test resource type.
    """
    implements(IResourceType, IPackage)

    package_id = 'post-test'
    resourcetype_id = 'notvc'
    version_control = False


class AVersionControlledResourceType(Component):
    """
    A version controlled test resource type.
    """
    implements(IResourceType, IPackage)

    package_id = 'post-test'
    resourcetype_id = 'vc'
    version_control = True


class RestPUTTests(SeisHubEnvironmentTestCase):
    """
    A test suite for PUT request on REST resources.
    """
    def setUp(self):
        self.env.enableComponent(AVersionControlledResourceType)
        self.env.enableComponent(AResourceType)
        self.env.tree = RESTFolder()

    def tearDown(self):
        self.env.registry.db_deleteResourceType('post-test', 'notvc')
        self.env.registry.db_deleteResourceType('post-test', 'vc')
        self.env.registry.db_deletePackage('post-test')

    def test_postJapaneseXMLDocuments(self):
        """
        Part of the W3C XML conformance test suite.
        
        This covers tests with different encoding and byte orders, e.g. UTF-16 
        with big and little endian. 
        
        @see: L{http://www.w3.org/XML/Test/}.
        """
        proc = Processor(self.env)
        path = os.path.dirname(__file__)
        # read all files
        files = glob.glob(os.path.join(path, 'data', 'japanese', '*.xml'))
        for file in files:
            # create resource
            data = open(file, 'rb').read()
            # first PUT should be handled as POST
            proc.run(POST, '/post-test/notvc/test.xml', StringIO(data))
            # overwrite resource
            proc.run(PUT, '/post-test/notvc/test.xml', StringIO(data))
            # delete resource
            proc.run(DELETE, '/post-test/notvc/test.xml')
        # same as before but using only PUT
        for file in files:
            # create resource
            data = open(file, 'rb').read()
            # first PUT should be handled as POST
            proc.run(PUT, '/post-test/notvc/test.xml', StringIO(data))
            # overwrite resource
            proc.run(PUT, '/post-test/notvc/test.xml', StringIO(data))
            # delete resource
            proc.run(DELETE, '/post-test/notvc/test.xml')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(RestPUTTests, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
