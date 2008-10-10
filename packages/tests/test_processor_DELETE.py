# -*- coding: utf-8 -*-

import unittest
from StringIO import StringIO

from twisted.web import http

from seishub.test import SeisHubEnvironmentTestCase
from seishub.packages.processor import Processor, ProcessorError
from seishub.packages.processor import PUT, POST, DELETE, GET
from seishub.core import Component, implements
from seishub.packages.builtins import IResourceType, IPackage
from seishub.packages.installer import PackageInstaller


XML_DOC = """<?xml version="1.0" encoding="utf-8"?>

<testml>
  <blah1 id="3">
    <blahblah1>üöäß</blahblah1>
  </blah1>
</testml>"""


XML_VC_DOC = """<?xml version="1.0" encoding="utf-8"?>

<testml>%d</testml>"""


class AResourceType(Component):
    """A non version controlled test resource type."""
    implements(IResourceType, IPackage)
    
    package_id = 'delete-test'
    resourcetype_id = 'notvc'
    version_control = False


class AVersionControlledResourceType(Component):
    """A version controlled test resource type."""
    implements(IResourceType, IPackage)
    
    package_id = 'delete-test'
    resourcetype_id = 'vc'
    version_control = True


class ProcessorDELETETest(SeisHubEnvironmentTestCase):
    """Test case for HTTP DELETE processing."""
    
    def setUp(self):
        self.env.enableComponent(AVersionControlledResourceType)
        self.env.enableComponent(AResourceType)
        PackageInstaller.install(self.env)
    
    def tearDown(self):
        self.env.disableComponent(AVersionControlledResourceType)
        self.env.disableComponent(AResourceType)
    
    def test_deletePackage(self):
        """SeisHub processor does not allow deletion of packages."""
        proc = Processor(self.env)
        # without trailing slash
        try:
            proc.run(DELETE, '/delete-test')
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
        # with trailing slash
        try:
            proc.run(DELETE, '/delete-test/')
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_deleteResourceType(self):
        """SeisHub processor does not allow deletion of packages."""
        proc = Processor(self.env)
        # without trailing slash
        try:
            proc.run(DELETE, '/delete-test/notvc')
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
        # with trailing slash
        try:
            proc.run(DELETE, '/delete-test/notvc/')
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_deleteNonExistingResource(self):
        """Non existing resource can't be deleted."""
        proc = Processor(self.env)
        # with trailing slash
        try:
            proc.run(DELETE, '/delete-test/notvc/test.xml')
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
    
    def test_deleteBuiltinResource(self):
        """SeisHub builtin resources can't be deleted."""
        proc = Processor(self.env)
        # fetch a seishub stylesheet
        data = proc.run(GET, '/seishub/stylesheet')
        url = str(data.get('resource')[0])
        try:
            proc.run(DELETE, url)
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_deleteResourceInNonExistingResourceType(self):
        """Resource can't be deleted from non existing resource type."""
        proc = Processor(self.env)
        # with trailing slash
        try:
            proc.run(DELETE, '/delete-test/notvc2/test.xml')
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_deleteResourceInNonExistingPackage(self):
        """Resource can't be deleted from non existing package."""
        proc = Processor(self.env)
        # with trailing slash
        try:
            proc.run(DELETE, '/delete-test2/notvc/test.xml')
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
    
    def test_deleteRevision(self):
        """Revisions may not be deleted via the processor."""
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/delete-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/delete-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/delete-test/vc/test.xml', StringIO(XML_DOC))
        # with trailing slash
        try:
            proc.run(DELETE, '/delete-test/vc/test.xml/1')
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.FORBIDDEN)
        # delete resource
        proc.run(DELETE, '/delete-test/vc/test.xml')
    
    def test_deleteVersionControlledResource(self):
        """Successful deletion of version controlled resources."""
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/delete-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/delete-test/vc/test.xml', StringIO(XML_VC_DOC % 1))
        proc.run(POST, '/delete-test/vc/test.xml', StringIO(XML_VC_DOC % 2))
        # check latest resource - should be #20
        data = proc.run(GET, '/delete-test/vc/test.xml')
        self.assertEqual(data, XML_VC_DOC % 2)
        # check oldest resource -> revision start with 1
        data = proc.run(GET, '/delete-test/vc/test.xml/1')
        self.assertEqual(data, XML_DOC)
        # delete resource
        data = proc.run(DELETE, '/delete-test/vc/test.xml')
        self.assertEqual(data, '')
        self.assertEqual(proc.response_code, http.NO_CONTENT)
        # fetch resource again
        try:
            proc.run(GET, '/delete-test/vc/test.xml')
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.GONE)
    
    def test_deleteResource(self):
        """Successful deletion of resources."""
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/delete-test/notvc/test.xml', StringIO(XML_DOC))
        # check resource
        data = proc.run(GET, '/delete-test/notvc/test.xml')
        self.assertEqual(data, XML_DOC)
        # delete resource
        data = proc.run(DELETE, '/delete-test/notvc/test.xml')
        self.assertEqual(data, '')
        self.assertEqual(proc.response_code, http.NO_CONTENT)
        # fetch resource again
        try:
            proc.run(GET, '/delete-test/notvc/test.xml')
            self.fail("Expected ProcessorError")
        except ProcessorError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
    
    def test_postOnDeletedVersionControlledResource(self):
        """XXX: POST on deleted version controlled resource should work."""
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/delete-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/delete-test/vc/test.xml', StringIO(XML_VC_DOC % 2))
        proc.run(POST, '/delete-test/vc/test.xml', StringIO(XML_VC_DOC % 3))
        # delete resource
        proc.run(DELETE, '/delete-test/vc/test.xml')
        # upload again
        proc.run(POST, '/delete-test/vc/test.xml', StringIO(XML_VC_DOC % 1000))
        data=proc.run(GET, '/delete-test/vc/test.xml')
        self.assertEqual(data, XML_VC_DOC % 1000)
        data=proc.run(GET, '/delete-test/vc/test.xml/1')
        self.assertEqual(data, XML_DOC)
        data=proc.run(GET, '/delete-test/vc/test.xml/2')
        self.assertEqual(data, XML_VC_DOC % 2)
        data=proc.run(GET, '/delete-test/vc/test.xml/3')
        self.assertEqual(data, XML_VC_DOC % 3)
        data=proc.run(GET, '/delete-test/vc/test.xml/4')
        # XXX: BUG - see ticket #62
        data=proc.run(GET, '/delete-test/vc/test.xml/5')
        self.assertEqual(data, XML_VC_DOC % 1000)
    
    def test_putOnDeletedVersionControlledResource(self):
        """XXX: PUT on deleted version controlled resource should work."""
        proc = Processor(self.env)
        # create resource
        proc.run(PUT, '/delete-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(POST, '/delete-test/vc/test.xml', StringIO(XML_VC_DOC % 2))
        proc.run(POST, '/delete-test/vc/test.xml', StringIO(XML_VC_DOC % 3))
        # delete resource
        proc.run(DELETE, '/delete-test/vc/test.xml')
        # upload again
        # XXX: BUG - see ticket #62
        proc.run(PUT, '/delete-test/vc/test.xml', StringIO(XML_VC_DOC % 1000))
        data=proc.run(GET, '/delete-test/vc/test.xml')
        self.assertEqual(data, XML_VC_DOC % 1000)
        data=proc.run(GET, '/delete-test/vc/test.xml/1')
        self.assertEqual(data, XML_DOC)
        data=proc.run(GET, '/delete-test/vc/test.xml/2')
        self.assertEqual(data, XML_VC_DOC % 2)
        data=proc.run(GET, '/delete-test/vc/test.xml/3')
        self.assertEqual(data, XML_VC_DOC % 3)
        data=proc.run(GET, '/delete-test/vc/test.xml/4')
        # XXX: BUG - see ticket #62
        data=proc.run(GET, '/delete-test/vc/test.xml/5')
        self.assertEqual(data, XML_VC_DOC % 1000)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ProcessorDELETETest, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')