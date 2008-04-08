# -*- coding: utf-8 -*-

import unittest

from seishub.test import SeisHubTestCase
from seishub.xmldb.metaresources import SchemaRegistry, StylesheetRegistry

class SchemaRegistryTest(SeisHubTestCase):
    def testSchemaRegistry(self):
        schema_reg = SchemaRegistry(self.db)
        schema_reg.registerSchema("/seishub/xsd/quakeml/quakeml1.xsd", "quakeml")
        schema_reg.registerSchema("/seishub/xsd/miniseed/seedxml.xsd", "miniseed")
        self.assertEquals(schema_reg.getSchemata("quakeml")[0][0],u'/seishub/xsd/quakeml/quakeml1.xsd')
        schema_reg.unregisterMetaResource("/seishub/xsd/quakeml/quakeml1.xsd")
        schema_reg.unregisterSchema("/seishub/xsd/miniseed/seedxml.xsd")

class StylesheetRegistryTest(SeisHubTestCase):
    def testStylesheetRegistry(self):
        style_reg = StylesheetRegistry(self.db)
        style_reg.registerStylesheet("/seishub/xsd/quakeml/quakeml_to_xhtml.xslt", 
                                     "quakeml1", "text/xhtml")
        style_reg.registerStylesheet("/seishub/xsd/quakeml/quakeml1_to_quakeml2.xslt", 
                                     "quakeml1", "quakeml2.0")
        self.assertEquals(style_reg.getStylesheets(),
                          [(u'/seishub/xsd/quakeml/quakeml_to_xhtml.xslt',), 
                           (u'/seishub/xsd/quakeml/quakeml1_to_quakeml2.xslt',)])
        self.assertEquals(style_reg.getStylesheets(format = "text/xhtml"),
                          [(u'/seishub/xsd/quakeml/quakeml_to_xhtml.xslt',)])
        style_reg.unregisterStylesheet("/seishub/xsd/quakeml/quakeml_to_xhtml.xslt")
        style_reg.unregisterStylesheet("/seishub/xsd/quakeml/quakeml1_to_quakeml2.xslt")

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SchemaRegistryTest, 'test'))
    suite.addTest(unittest.makeSuite(StylesheetRegistryTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')