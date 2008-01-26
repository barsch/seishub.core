# -*- coding: utf-8 -*-

from twisted.trial.unittest import TestCase
from seishub.xmldb.xpath import *

class XpathTest(TestCase):
    def testRestrictedXpathExpression(self):
        valid="/rootnode[./somenode/achild and @anattribute]"
        invalid="/rootnode/childnode"
        
        expr=RestrictedXpathExpression(valid)
        self.assertEqual(expr.node_test,"rootnode")
        self.assertEqual(expr.predicates,"./somenode/achild and @anattribute")
        self.assertRaises(RestrictedXpathError,
                          RestrictedXpathExpression,
                          invalid)