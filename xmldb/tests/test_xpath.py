# -*- coding: utf-8 -*-

import unittest

from seishub.test import SeisHubTestCase
from seishub.xmldb.xpath import RestrictedXpathExpression, \
                                RestrictedXpathError, \
                                XPathQuery


class XpathTest(SeisHubTestCase):
    #TODO: testIndexDefiningXpathExpression
    
    def testRestrictedXpathExpression(self):
        valid="/rootnode[./somenode/achild and @anattribute]"
        invalid="/rootnode/childnode"
        
        expr=RestrictedXpathExpression(valid)
        self.assertEqual(expr.node_test,"rootnode")
        self.assertEqual(expr.predicates,"./somenode/achild and @anattribute")
        self.assertRaises(RestrictedXpathError,
                          RestrictedXpathExpression,
                          invalid)
        
class XPathQueryTest(SeisHubTestCase):
    test_expr = "/rootnode[./element1/element2 = 'blub' and ./element1/@id = 5]"
    
    def testXPathQuery(self):
        q = XPathQuery(self.test_expr)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(XpathTest, 'test'))
    suite.addTest(unittest.makeSuite(XPathQueryTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')