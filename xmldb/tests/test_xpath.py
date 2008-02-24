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
        invalid=["/rootnode/childnode", # more than one location step
                 "/rootnode[child[blah]]", # [ ] in predicates
                 "/rootnode[child1 = blah and (child2 = blub or child3)]", 
                                                        # ( ) in predicates 
                 "[/rootnode/child]", # no location step outside predicates
                 ]
        
        
        expr=RestrictedXpathExpression(valid)
        self.assertEqual(expr.node_test,"rootnode")
        self.assertEqual(expr.predicates,"./somenode/achild and @anattribute")
        for iv in invalid:
            self.assertRaises(RestrictedXpathError,
                              RestrictedXpathExpression,
                              iv)
        
class XPathQueryTest(SeisHubTestCase):
    test_expr = "/rootnode[./element1/element2 = 'blub' and ./element1/@id <= 5]"
    
    def testXPathQuery(self):
        q = XPathQuery(self.test_expr)
        self.assertEqual(q.getValue_path(), "rootnode")
        p = q.getPredicates()
        self.assertEqual(str(p.getOperation()['op']),
                         "and")
        self.assertEqual(str(p.getOperation()['left']),
                         "element1/element2 = blub")
        self.assertEqual(str(p.getOperation()['right']),
                         "element1/@id <= 5")
        self.assertEqual(str(p.getOperation()['left'].getOperation()['left']),
                         "element1/element2")
        self.assertEqual(str(p.getOperation()['left'].getOperation()['op']),
                         "=")
        self.assertEqual(str(p.getOperation()['left'].getOperation()['right']),
                         "blub")
        self.assertEqual(str(p.getOperation()['right'].getOperation()['left']),
                         "element1/@id")
        self.assertEqual(str(p.getOperation()['right'].getOperation()['op']),
                         "<=")
        self.assertEqual(str(p.getOperation()['right'].getOperation()['right']),
                         "5")


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(XpathTest, 'test'))
    suite.addTest(unittest.makeSuite(XPathQueryTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')