# -*- coding: utf-8 -*-

import unittest

from seishub.test import SeisHubEnvironmentTestCase
from seishub.xmldb.xpath import RestrictedXpathExpression, \
                                RestrictedXpathError, InvalidXpathQuery, \
                                XPathQuery


class XpathTest(SeisHubEnvironmentTestCase):
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
        
class XPathQueryTest(SeisHubEnvironmentTestCase):
    test_expr = "/testpackage/testtype/rootnode[./element1/element2 = 'blub' and ./element1/@id <= 5]"
    wildcard_expr = "/*/*/rootnode[./element1/element2 = 'blub']"
    invalid_expr = "/testtype/rootnode[./element1]"
    invalid2_expr = "/rootnode[./element1]"
    
    def testXPathQuery(self):
        # valid expression
        q = XPathQuery(self.test_expr)
        self.assertEqual(q.package_id, "testpackage")
        self.assertEqual(q.resourcetype_id, "testtype")
        self.assertEqual(q.getValue_path(), "testpackage/testtype/rootnode")
        p = q.getPredicates()
        self.assertEqual(str(p['op']), "and")
        self.assertEqual(str(p['left']), "element1/element2 = blub")
        self.assertEqual(str(p['right']), "element1/@id <= 5")
        self.assertEqual(str(p['left']['left']), "element1/element2")
        self.assertEqual(str(p['left']['op']), "=")
        self.assertEqual(str(p['left']['right']), "blub")
        self.assertEqual(str(p['right']['left']), "element1/@id")
        self.assertEqual(str(p['right']['op']), "<=")
        self.assertEqual(str(p['right']['right']), "5")
        
        # wildcard expression:
        q1 = XPathQuery(self.wildcard_expr)
        self.assertEqual(q1.package_id, None)
        self.assertEqual(q1.resourcetype_id, None)
        self.assertEqual(q1.getValue_path(), "None/None/rootnode")
        
        # invalid expression:
        self.assertRaises(InvalidXpathQuery,
                          XPathQuery, self.invalid_expr)
        self.assertRaises(InvalidXpathQuery,
                          XPathQuery, self.invalid2_expr)
        
def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(XpathTest, 'test'))
    suite.addTest(unittest.makeSuite(XPathQueryTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')