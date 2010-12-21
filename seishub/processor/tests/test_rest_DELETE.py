# -*- coding: utf-8 -*-
"""
A test suite for DELETE request on REST resources.
"""

from StringIO import StringIO
from seishub.core import Component, implements
from seishub.exceptions import SeisHubError
from seishub.packages.builtins import IResourceType, IPackage
from seishub.processor import Processor, POST, PUT, DELETE, GET
from seishub.processor.resources import RESTFolder
from seishub.test import SeisHubEnvironmentTestCase
from twisted.web import http
import unittest


XML_DOC = """<?xml version="1.0" encoding="utf-8"?>

<testml>
  <blah1 id="3">
    <blahblah1>üöäß</blahblah1>
  </blah1>
</testml>"""


XML_VCDOC = """<?xml version="1.0" encoding="utf-8"?>

<testml>%d</testml>"""


class AResourceType(Component):
    """
    A non version controlled test resource type.
    """
    implements(IResourceType, IPackage)

    package_id = 'delete-test'
    resourcetype_id = 'notvc'
    version_control = False


class AVersionControlledResourceType(Component):
    """
    A version controlled test resource type.
    """
    implements(IResourceType, IPackage)

    package_id = 'delete-test'
    resourcetype_id = 'vc'
    version_control = True


class RestDELETETests(SeisHubEnvironmentTestCase):
    """
    A test suite for DELETE request on REST resources.
    """
    def setUp(self):
        self.env.enableComponent(AVersionControlledResourceType)
        self.env.enableComponent(AResourceType)
        self.env.tree = RESTFolder()

    def tearDown(self):
        self.env.registry.db_deleteResourceType('delete-test', 'vc')
        self.env.registry.db_deleteResourceType('delete-test', 'notvc')
        self.env.registry.db_deletePackage('delete-test')

    def test_deletePackage(self):
        """
        SeisHub processor does not allow deletion of packages.
        """
        proc = Processor(self.env)
        # without trailing slash
        try:
            proc.run(DELETE, '/delete-test')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_ALLOWED)
        # with trailing slash
        try:
            proc.run(DELETE, '/delete-test/')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_ALLOWED)

    def test_deleteNotExistingPackage(self):
        """
        A not existing resource package can't be deleted.
        """
        proc = Processor(self.env)
        # without trailing slash
        try:
            proc.run(DELETE, '/xxx')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # with trailing slash
        proc = Processor(self.env)
        try:
            proc.run(DELETE, '/xxx')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)

    def test_deleteResourceType(self):
        """
        SeisHub processor does not allow deletion of resource types.
        """
        proc = Processor(self.env)
        # without trailing slash
        try:
            proc.run(DELETE, '/delete-test/notvc')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_ALLOWED)
        # with trailing slash
        try:
            proc.run(DELETE, '/delete-test/notvc/')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_ALLOWED)

    def test_deleteNotExistingResourceType(self):
        """
        A not existing resource type can't be deleted.
        """
        proc = Processor(self.env)
        # without trailing slash
        try:
            proc.run(DELETE, '/delete-test/xxx')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)
        # with trailing slash
        proc = Processor(self.env)
        try:
            proc.run(DELETE, '/delete-test/xxx/')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)

    def test_deleteResource(self):
        """
        Successful deletion of XML resources.
        """
        proc = Processor(self.env)
        # create resource
        proc.run(POST, '/delete-test/notvc/test.xml', StringIO(XML_DOC))
        # check resource
        data = proc.run(GET, '/delete-test/notvc/test.xml').render_GET(proc)
        self.assertEqual(data, XML_DOC)
        # delete resource
        data = proc.run(DELETE, '/delete-test/notvc/test.xml')
        self.assertEqual(data, '')
        self.assertEqual(proc.code, http.NO_CONTENT)
        # fetch resource again
        try:
            proc.run(GET, '/delete-test/notvc/test.xml')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)

    def test_deleteNotExistingResource(self):
        """
        Not existing resource can't be deleted.
        """
        proc = Processor(self.env)
        try:
            proc.run(DELETE, '/delete-test/notvc/test.xml')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)

    def test_deleteBuiltinResource(self):
        """
        SeisHub built-in resources can't be deleted.
        """
        proc = Processor(self.env)
        # fetch a seishub stylesheet
        data = proc.run(GET, '/seishub/stylesheet')
        for id in data:
            # skip indexes
            if id.startswith('/'):
                continue
            try:
                proc.run(DELETE, '/seishub/stylesheet/' + id)
                self.fail("Expected SeisHubError")
            except SeisHubError, e:
                self.assertEqual(e.code, http.FORBIDDEN)

    def test_deleteRevision(self):
        """
        Revisions may not be deleted via the processor.
        """
        proc = Processor(self.env)
        # create resource
        proc.run(POST, '/delete-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(PUT, '/delete-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(PUT, '/delete-test/vc/test.xml', StringIO(XML_DOC))
        try:
            proc.run(DELETE, '/delete-test/vc/test.xml/1')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_ALLOWED)
        # delete resource
        proc.run(DELETE, '/delete-test/vc/test.xml')

    def test_deleteNotExistingRevision(self):
        """
        Also not existing revisions may not be deleted via the processor.
        """
        proc = Processor(self.env)
        # create resource
        proc.run(POST, '/delete-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(PUT, '/delete-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(PUT, '/delete-test/vc/test.xml', StringIO(XML_DOC))
        try:
            proc.run(DELETE, '/delete-test/vc/test.xml/10')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_ALLOWED)
        # delete resource
        proc.run(DELETE, '/delete-test/vc/test.xml')

    def test_deleteResourceInNotExistingResourceType(self):
        """
        Resource can't be deleted from not existing resource type.
        """
        proc = Processor(self.env)
        try:
            proc.run(DELETE, '/delete-test/notvc2/test.xml')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)

    def test_deleteResourceInNotExistingPackage(self):
        """
        Resource can't be deleted from not existing package.
        """
        proc = Processor(self.env)
        # with trailing slash
        try:
            proc.run(DELETE, '/delete-test2/notvc/test.xml')
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)

    def test_deleteVersionControlledResource(self):
        """
        Successful deletion of version controlled resources.
        """
        proc = Processor(self.env)
        # create resource
        proc.run(POST, '/delete-test/vc/test.xml', StringIO(XML_DOC))
        proc.run(PUT, '/delete-test/vc/test.xml', StringIO(XML_VCDOC % 1))
        proc.run(PUT, '/delete-test/vc/test.xml', StringIO(XML_VCDOC % 2))
        # check latest resource - should be #20
        data = proc.run(GET, '/delete-test/vc/test.xml').render_GET(proc)
        self.assertEqual(data, XML_VCDOC % 2)
        # check oldest resource -> revision start with 1
        data = proc.run(GET, '/delete-test/vc/test.xml/1').render_GET(proc)
        self.assertEqual(data, XML_DOC)
        # delete resource
        data = proc.run(DELETE, '/delete-test/vc/test.xml')
        self.assertEqual(data, '')
        self.assertEqual(proc.code, http.NO_CONTENT)
        # fetch resource again
        try:
            proc.run(GET, '/delete-test/vc/test.xml').render_GET(proc)
            self.fail("Expected SeisHubError")
        except SeisHubError, e:
            self.assertEqual(e.code, http.NOT_FOUND)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(RestDELETETests, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
