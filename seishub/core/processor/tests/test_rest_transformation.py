# -*- coding: utf-8 -*-
"""
A test suite for transformation of REST resources.
"""

from StringIO import StringIO
from seishub.core.core import Component, implements
from seishub.core.packages.builtins import IResourceType, IPackage
from seishub.core.packages.installer import registerStylesheet
from seishub.core.processor import POST, PUT, DELETE, GET, Processor
from seishub.core.processor.resources import RESTFolder
from seishub.core.test import SeisHubEnvironmentTestCase
import os
import unittest


XML_DOC = """<?xml version="1.0" encoding="utf-8"?>

<sales>
  <division id="North">
    <revenue>10</revenue>
    <growth>9</growth>
    <bonus>7</bonus>
  </division>
  <division id="South">
    <revenue>4</revenue>
    <growth>3</growth>
    <bonus>4</bonus>
  </division>
  <division id="West">
    <revenue>6</revenue>
    <growth>-1.5</growth>
    <bonus>2</bonus>
  </division>
</sales>"""

HTML_DOC = """<?xml version="1.0" encoding="utf-8"?>

<html lang="en">
  <head>
    <title>Sales Results By Division</title>
  </head>
  <body>
    <table border="1">
      <tr>
        <th>Division</th>
        <th>Revenue</th>
        <th>Growth</th>
        <th>Bonus</th>
      </tr>
      <tr>
        <td>
          <em>North</em>
        </td>
        <td>10</td>
        <td>9</td>
        <td>7</td>
      </tr>
      <tr>
        <td>
          <em>West</em>
        </td>
        <td>6</td>
        <td style="color:red">-1.5</td>
        <td>2</td>
      </tr>
      <tr>
        <td>
          <em>South</em>
        </td>
        <td>4</td>
        <td>3</td>
        <td>4</td>
      </tr>
    </table>
  </body>
</html>
"""

TXT_DOC = """Sales Results By Division

North,10,9,7
West,6,-1.5,2
South,4,3,4
"""

SVG_DOC = """<?xml version="1.0"?>
<svg xmlns:svg="http://www.w3.org/Graphics/SVG/SVG-19990812.dtd" height="3in" width="3in">
  <g style="stroke: #000000">
    <line x1="0" x2="150" y1="150" y2="150"/>
    <line x1="0" x2="0" y1="0" y2="150"/>
    <text x="0" y="10">Revenue</text>
    <text x="150" y="165">Division</text>
    <rect height="100" width="20" x="10" y="50"/>
    <text x="10" y="165">North</text>
    <text x="10" y="45">10</text>
    <rect height="40" width="20" x="50" y="110"/>
    <text x="50" y="165">South</text>
    <text x="50" y="105">4</text>
    <rect height="60" width="20" x="90" y="90"/>
    <text x="90" y="165">West</text>
    <text x="90" y="85">6</text>
  </g>
</svg>
"""

XML_DOC_2 = """<?xml version="1.0" encoding="utf-8"?>

<test>Sales Results By Division</test>"""


class APackage(Component):
    """
    A test package.
    """
    implements(IPackage)

    package_id = 'transformation-test'


class AResourceType(Component):
    """
    A test resource type including various transformation style sheets.
    """
    implements(IResourceType)

    package_id = 'transformation-test'
    resourcetype_id = 'rt'

    registerStylesheet('data' + os.sep + 'transformation' + os.sep + \
                       'xml2html.xslt', 'xml2html')
    registerStylesheet('data' + os.sep + 'transformation' + os.sep + \
                       'xml2svg.xslt', 'xml2svg')
    registerStylesheet('data' + os.sep + 'transformation' + os.sep + \
                       'html2txt.xslt', 'html2txt')
    registerStylesheet('data' + os.sep + 'transformation' + os.sep + \
                       'html2xml.xslt', 'html2xml')


class RestTransformationTests(SeisHubEnvironmentTestCase):
    """
    A test suite for transformation of REST resources.
    """
    def setUp(self):
        self.env.enableComponent(APackage)
        self.env.enableComponent(AResourceType)
        self.env.tree = RESTFolder()
        self.path = os.path.dirname(__file__)

    def tearDown(self):
        # delete style sheets
        for key in ['xml2html', 'xml2svg', 'html2txt', 'html2xml']:
            self.env.registry.stylesheets.delete('transformation-test', 'rt',
                                                 key)
        # delete all resource types
        for rt in self.env.registry.getResourceTypeIds('transformation-test'):
            self.env.registry.db_deleteResourceType('transformation-test', rt)
        # delete package
        self.env.registry.db_deletePackage('transformation-test')

    def test_getFormatedResource(self):
        """
        Get resource in a certain format using a single style sheet.
        """
        proc = Processor(self.env)
        # create resource
        proc.run(POST, '/transformation-test/rt/test.xml', StringIO(XML_DOC))
        # without format
        proc.args = {'format': []}
        res = proc.run(GET, '/transformation-test/rt/test.xml')
        data = res.render(proc)
        self.assertEquals(data, XML_DOC)
        # transform to existing format HTML
        proc.args = {'format': ['xml2html']}
        res = proc.run(GET, '/transformation-test/rt/test.xml')
        data = res.render(proc)
        self.assertEquals(data, HTML_DOC)
        # transform to existing format SVG
        proc.args = {'format': ['xml2svg']}
        res = proc.run(GET, '/transformation-test/rt/test.xml')
        data = res.render(proc)
        self.assertEquals(data, SVG_DOC)
        # missing format
        proc.args = {'format': ['XXX']}
        res = proc.run(GET, '/transformation-test/rt/test.xml')
        data = res.render(proc)
        self.assertEquals(data, XML_DOC)
        # delete resource
        proc.run(DELETE, '/transformation-test/rt/test.xml')

    def test_getMultiFormatedResource(self):
        """
        Get resource in a certain format using multiple style sheets.
        """
        proc = Processor(self.env)
        # create resource
        proc.run(POST, '/transformation-test/rt/test.xml', StringIO(XML_DOC))
        # transform using a format chain
        proc.args = {'format': ['xml2html', 'html2txt']}
        res = proc.run(GET, '/transformation-test/rt/test.xml')
        data = res.render(proc)
        self.assertEquals(data, TXT_DOC)
        # missing formats
        proc.args = {'format': ['XXX', 'YYY', 'ZZZ']}
        res = proc.run(GET, '/transformation-test/rt/test.xml')
        data = res.render(proc)
        self.assertEquals(data, XML_DOC)
        # one valid format
        proc.args = {'format': ['XXX', 'xml2html', 'YYY']}
        res = proc.run(GET, '/transformation-test/rt/test.xml')
        data = res.render(proc)
        self.assertEquals(data, HTML_DOC)
        # transform using a format chain but last style sheet is missing
        proc.args = {'format': ['xml2html', 'html2txt', 'XXX']}
        res = proc.run(GET, '/transformation-test/rt/test.xml')
        data = res.render(proc)
        self.assertEquals(data, TXT_DOC)
        # transform using a format chain but one style sheet is missing
        proc.args = {'format': ['xml2html', 'XXX', 'html2txt']}
        res = proc.run(GET, '/transformation-test/rt/test.xml')
        data = res.render(proc)
        self.assertEquals(data, TXT_DOC)
        # delete resource
        proc.run(DELETE, '/transformation-test/rt/test.xml')

    def test_putFormatedResource(self):
        """
        Upload resource in a certain format using a single style sheets.
        """
        proc = Processor(self.env)
        # create + transform resource
        proc.args = {'format': ['xml2html']}
        proc.run(POST, '/transformation-test/rt/test.xml', StringIO(XML_DOC))
        # get uploaded resource
        proc.args = {}
        res = proc.run(GET, '/transformation-test/rt/test.xml')
        data = res.render(proc)
        self.assertEquals(data, HTML_DOC.strip())
        # get uploaded resource with format
        proc.args = {'format': ['html2txt']}
        res = proc.run(GET, '/transformation-test/rt/test.xml')
        data = res.render(proc)
        self.assertEquals(data, TXT_DOC)
        # delete resource
        proc.run(DELETE, '/transformation-test/rt/test.xml')

    def test_putMultiFormatedResource(self):
        """
        Upload resource in a certain format using multiple style sheets.
        """
        proc = Processor(self.env)
        # create + transform resource
        proc.args = {'format': ['xml2html', 'html2xml']}
        proc.run(POST, '/transformation-test/rt/test.xml', StringIO(XML_DOC))
        # get uploaded resource
        proc.args = {}
        res = proc.run(GET, '/transformation-test/rt/test.xml')
        data = res.render(proc)
        self.assertEquals(data, XML_DOC_2)
        # get uploaded resource with format
        proc.args = {'format': ['xml2html', 'html2txt']}
        res = proc.run(GET, '/transformation-test/rt/test.xml')
        data = res.render(proc)
        self.assertEquals(data, 'Sales Results By Division\n\n')
        # delete resource
        proc.run(DELETE, '/transformation-test/rt/test.xml')
        # create + transform resource with missing style sheet
        proc.args = {'format': ['xml2html', 'html2xml', 'XXX']}
        proc.run(POST, '/transformation-test/rt/test.xml', StringIO(XML_DOC))
        # get uploaded resource
        proc.args = {}
        res = proc.run(GET, '/transformation-test/rt/test.xml')
        data = res.render(proc)
        self.assertEquals(data, XML_DOC_2)
        # delete resource
        proc.run(DELETE, '/transformation-test/rt/test.xml')
        # create + transform resource with missing style sheet
        proc.args = {'format': ['xml2html', 'XXX', 'YYY']}
        proc.run(POST, '/transformation-test/rt/test.xml', StringIO(XML_DOC))
        # get uploaded resource
        proc.args = {}
        res = proc.run(GET, '/transformation-test/rt/test.xml')
        data = res.render(proc)
        self.assertEquals(data, HTML_DOC.strip())
        # delete resource
        proc.run(DELETE, '/transformation-test/rt/test.xml')

    def test_postMultiFormatedResource(self):
        """
        Update resource in a certain format using multiple style sheets.
        """
        proc = Processor(self.env)
        # create resource
        proc.run(POST, '/transformation-test/rt/test.xml', StringIO(XML_DOC))
        # update resource with transformation
        proc.args = {'format': ['xml2html', 'html2xml']}
        proc.run(PUT, '/transformation-test/rt/test.xml', StringIO(XML_DOC))
        # get uploaded resource
        proc.args = {}
        res = proc.run(GET, '/transformation-test/rt/test.xml')
        data = res.render(proc)
        self.assertEquals(data, XML_DOC_2)
        # get uploaded resource with format
        proc.args = {'format': ['xml2html', 'html2txt']}
        res = proc.run(GET, '/transformation-test/rt/test.xml')
        data = res.render(proc)
        self.assertEquals(data, 'Sales Results By Division\n\n')
        # delete resource
        proc.run(DELETE, '/transformation-test/rt/test.xml')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(RestTransformationTests, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
