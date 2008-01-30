# -*- coding: utf-8 -*-

from seishub.test import SeisHubTestCase
from seishub.xmldb.xpath import *

class XpathTest(SeisHubTestCase):
    def setUp(self):
        pass
    
    def testRestrictedXpathExpression(self):
        valid="/rootnode[./somenode/achild and @anattribute]"
        invalid="/rootnode/childnode"
        
        expr=RestrictedXpathExpression(valid)
        self.assertEqual(expr.node_test,"rootnode")
        self.assertEqual(expr.predicates,"./somenode/achild and @anattribute")
        self.assertRaises(RestrictedXpathError,
                          RestrictedXpathExpression,
                          invalid)