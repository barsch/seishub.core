# -*- coding: utf-8 -*-

from seishub.core.core import Component, implements
from seishub.core.packages.interfaces import IProcessorIndex, IPackage, \
    IResourceType
from seishub.core.test import SeisHubEnvironmentTestCase
from seishub.core.xmldb import index
from seishub.core.xmldb.resource import newXMLDocument
import unittest


RAW_XML1 = u"""
<station rel_uri="bern">
    <station_code>BERN</station_code>
    <chan_code>1</chan_code>
    <stat_type>0</stat_type>
    <lon>12.51200</lon>
    <lat>50.23200</lat>
    <stat_elav>0.63500</stat_elav>
    <XY>
        <paramXY>20.5</paramXY>
        <paramXY>11.5</paramXY>
        <paramXY>blah</paramXY>
    </XY>
    <creation_date>%s</creation_date>
    <bool>%s</bool>
</station>
"""


class ProcessorIndexTestPackage(Component):
    implements(IPackage)
    package_id = 'processorindextest'


class ProcessorIndexTestResourcetype(Component):
    implements(IResourceType)
    package_id = 'processorindextest'
    resourcetype_id = 'testtype'


class TestIndex(Component):
    implements(IProcessorIndex)

    package_id = 'processorindextest'
    resourcetype_id = 'testtype'
    type = index.FLOAT_INDEX
    label = 'testindex'

    def eval(self, document): #@UnusedVariable
        return [1, 2, 3]


class ProcessorIndexTest(SeisHubEnvironmentTestCase):
    def setUp(self):
        self.env.enableComponent(ProcessorIndexTestPackage)
        self.env.enableComponent(ProcessorIndexTestResourcetype)

    def tearDown(self):
        self.env.disableComponent(ProcessorIndexTestResourcetype)
        self.env.disableComponent(ProcessorIndexTestPackage)
        self.env.registry.db_deleteResourceType('processorindextest',
                                                'testtype')
        self.env.registry.db_deletePackage('processorindextest')

    def test_registerProcessorIndex(self):
        self.env.enableComponent(TestIndex)
        indexes = self.env.catalog.index_catalog.getIndexes(
            package_id='processorindextest', resourcetype_id='testtype')
        self.assertEqual(len(indexes), 1)
        idx = indexes[0]
        self.assertEqual(idx.resourcetype.package.package_id,
                         'processorindextest')
        self.assertEqual(idx.resourcetype.resourcetype_id, 'testtype')
        self.assertEqual(idx.type, index.PROCESSOR_INDEX)
        self.assertEqual(idx.options, TestIndex.__module__ + '.' + \
                         TestIndex.__name__)

        test_doc = newXMLDocument(RAW_XML1)
        res = idx.eval(test_doc, self.env)
        self.assertEqual(len(res), 3)
        self.assertEqual(type(res[0]), index.FloatIndexElement)
        self.assertEqual(type(res[1]), index.FloatIndexElement)
        self.assertEqual(type(res[2]), index.FloatIndexElement)
        self.assertEqual(res[0].key, 1)
        self.assertEqual(res[1].key, 2)
        self.assertEqual(res[2].key, 3)
        self.env.disableComponent(TestIndex)
        # cleanup
        self.env.catalog.deleteIndex(idx)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ProcessorIndexTest, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
