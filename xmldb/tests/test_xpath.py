# -*- coding: utf-8 -*-

from seishub.exceptions import InvalidParameterError
from seishub.test import SeisHubEnvironmentTestCase
from seishub.xmldb.xpath import RestrictedXpathExpression, XPathQuery, \
    RestrictedXPathQueryParser
import unittest


class XPathQueryParserTest(SeisHubEnvironmentTestCase):
    def __init__(self, *args, **kwargs):
        SeisHubEnvironmentTestCase.__init__(self, *args, **kwargs)
        self.parser = RestrictedXPathQueryParser()
        
    def testLocationStepOnly(self):
        queries = ['/package/resourcetype/rootnode',
                   '/package/resourcetype/*',
                   '/package/*/*',
                   '/*/*/*']
        res = [self.parser.parse(q) for q in queries]
        # print res
        
    def testKeyLessQuery(self):
        queries = ['/pid/rid/rn[attr]',
                   '/pid/rid/rn[node/./attr]',
                   '/pid/rid/rn[./node/attr]',
                   '/pid/rid/rn[../../rt/*/node/attr]',
                   '/pid/rid/rn[@attr]',
                   '/pid/rid/rn[./@attr]',
                   '/pid/rid/rn[./node/@attr]',
                   ]
        res = [self.parser.parse(q) for q in queries]
#        for r in res:
#            print '\n' + str(r.predicates)
        
    def testSingleKeyQuery(self):
        queries = ['/pid/rid/rn[attr = blah]',
                   '/pid/rid/rn[node/attr = blah]',
                   '/pid/rid/rn[./node/attr = blah]',
                   '/pid/rid/rn[@attr = blah]',
                   '/pid/rid/rn[./@attr = blah]',
                   '/pid/rid/rn[./node/@attr = blah]',
                   '/pid/rid/rn[/pid2/rt2/rn2/node/@attr = blah]',
                   '/pid/rid/rn[../../../pid2/rid2/*/node/attr = blah]',
                   '/pid/rid/rn[../../rid2/*/node/attr = blah]',
                   '/pid/rid/rn[../*/node/attr = blah]',
                   ]
        res = [self.parser.parse(q) for q in queries]
#        for r in res:
#            print '\n' + str(r.predicates)
            
    def testXPathFunctionQuery(self):
        queries = ['/pid/rid/rn[attr = blah]',
                   ]
        res = [self.parser.parse(q) for q in queries]
#        for r in res:
#            print '\n' + str(r.predicates)

    def testRelationalOperators(self):
        queries = {'/pid/rid/rn[attr1 = blah]' : '=',
                   '/pid/rid/rn[attr1 == blah]' : '==',
                   '/pid/rid/rn[attr1 < blah]' : '<',
                   '/pid/rid/rn[attr1 > blah]' : '>',
                   '/pid/rid/rn[attr1 <= blah]' : '<=',
                   '/pid/rid/rn[attr1 >= blah]' : '>=',
                   '/pid/rid/rn[attr1 != blah]' : '!=',
                   }
        res = [(self.parser.parse(q), t) for q, t in queries.iteritems()]
        for r, t in res:
            self.assertEqual(r.predicates[0][3], t)
            
    def testLogicalOperators(self):
        queries = ['/pid/rid/rn[attr1 = blah and attr2 = bluh]',
                   '/pid/rid/rn[attr1 = blah or attr2 = bluh]',
                   '/pid/rid/rn[attr1 = blah and not attr2 = bluh]',
                   '/pid/rid/rn[attr1 = blah or not attr2 = bluh]',
                   '/pid/rid/rn[not attr1 = blah]',
                   ]
        res = [self.parser.parse(q) for q in queries]
        self.assertEqual(res[0].predicates[1], 'and')
        self.assertEqual(res[1].predicates[1], 'or')
        self.assertEqual(res[2].predicates[1:3], ['and', 'not'])
        self.assertEqual(res[3].predicates[1:3], ['or', 'not'])
        self.assertEqual(res[4].predicates[0], 'not')
           
    def testMultipleKeyQuery(self):
        queries = ['/pid/rid/rn[attr1 = blah and attr2 = bluh]',
                   '/pid/rid/rn[attr1 = blah and (attr2 = bluh or attr2 = bloh)]',
                   '/pid/rid/rn[(attr1 = blah and attr2 = bluh) or attr2 = bloh]',
                   '/pid/rid/rn[(attr1 = blah and attr2 = bluh) or attr2 = bloh]',
                   '/pid/rid/rn[attr1 = blah and (attr2 = bluh and (attr2 = bloh or attr3 = moep))]'
                   ]
        res = [self.parser.parse(q) for q in queries]
#        for r in res:
#            print '\n' + str(r.predicates)
            
    def testJoinedPathQuery(self):
        queries = ['/pid/rid/rn[attr1 = blah and attr2 = bluh]',
                   '/pid/rid/rn[attr1 = blah and (attr2 = bluh or attr2 = bloh)]',
                   '/pid/rid/rn[(attr1 = blah and attr2 = bluh) or attr2 = bloh]',
                   '/pid/rid/rn[(attr1 = blah and attr2 = bluh) or attr2 = bloh]',
                   '/pid/rid/rn[attr1 = blah and (attr2 = bluh and (attr2 = bloh or attr3 = moep))]'
                   ]
        res = [self.parser.parse(q) for q in queries]
#        for r in res:
#            print '\n' + str(r.predicates)

#class XpathTest(SeisHubEnvironmentTestCase):
#    def testRestrictedXpathExpression(self):
#        valid="/rootnode[./somenode/achild and @anattribute]"
#        invalid=["/rootnode/childnode", # more than one location step
#                 "/rootnode[child[blah]]", # [ ] in predicates
#                 "/rootnode[child1 = blah and (child2 = blub or child3)]", 
#                                                        # ( ) in predicates 
#                 "[/rootnode/child]", # no location step outside predicates
#                 ]
#        
#        
#        expr=RestrictedXpathExpression(valid)
#        self.assertEqual(expr.node_test,"rootnode")
#        self.assertEqual(expr.predicates,"./somenode/achild and @anattribute")
#        for iv in invalid:
#            self.assertRaises(InvalidParameterError,
#                              RestrictedXpathExpression,
#                              iv)
#        
#class XPathQueryTest(SeisHubEnvironmentTestCase):
#    test_expr = "/testpackage/testtype/rootnode[./element1/element2 = 'blub' and ./element1/@id <= 5]"
#    wildcard_expr = "/*/*/rootnode[./element1/element2 = 'blub']"
#    join_expr = "/seispkg/network/*[../event/*/station = ../network/*/station and ./@id = ../station/*/@id and ../event/*/datetime = yesterday]"
#    invalid_expr = "/testtype/rootnode[./element1]"
#    invalid2_expr = "/rootnode[./element1]"
#    
#    def testXPathQuery(self):
#        # valid expression
#        q = XPathQuery(self.test_expr)
#        self.assertEqual(q.package_id, "testpackage")
#        self.assertEqual(q.resourcetype_id, "testtype")
#        self.assertEqual(q.node_test, "rootnode")
#        # self.assertEqual(q.getValue_path(), "testpackage/testtype/rootnode")
#        p = q.getPredicates()
#        self.assertEqual(str(p['op']), "and")
#        self.assertEqual(str(p['left']), "element1/element2 = blub")
#        self.assertEqual(str(p['right']), "element1/@id <= 5")
#        self.assertEqual(str(p['left']['left']), "element1/element2")
#        self.assertEqual(str(p['left']['op']), "=")
#        self.assertEqual(str(p['left']['right']), "blub")
#        self.assertEqual(str(p['right']['left']), "element1/@id")
#        self.assertEqual(str(p['right']['op']), "<=")
#        self.assertEqual(str(p['right']['right']), "5")
#        
#        # wildcard expression:
#        q1 = XPathQuery(self.wildcard_expr)
#        self.assertEqual(q1.package_id, None)
#        self.assertEqual(q1.resourcetype_id, None)
#        self.assertEqual(q1.node_test, "rootnode")
#        
#        # join expression
#        q2 = XPathQuery(self.join_expr)
#        # import pdb;pdb.set_trace()
#        
#        # invalid expression:
#        self.assertRaises(InvalidParameterError,
#                          XPathQuery, self.invalid_expr)
#        self.assertRaises(InvalidParameterError,
#                          XPathQuery, self.invalid2_expr)
        
def suite():
    suite = unittest.TestSuite()
    # suite.addTest(unittest.makeSuite(XpathTest, 'test'))
    # suite.addTest(unittest.makeSuite(XPathQueryTest, 'test'))
    suite.addTest(unittest.makeSuite(XPathQueryParserTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')