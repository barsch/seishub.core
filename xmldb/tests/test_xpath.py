# -*- coding: utf-8 -*-

import unittest

from seishub.test import SeisHubTestCase
from seishub.xmldb.xpath import RestrictedXpathExpression, \
                                RestrictedXpathError


class XpathTest(SeisHubTestCase):
    #TODO: testIndexDefiningXpathExpression
    
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


def suite():
    return unittest.makeSuite(XpathTest, 'test')

if __name__ == '__main__':
    unittest.main(defaultTest='suite')