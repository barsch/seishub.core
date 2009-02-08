# -*- coding: utf-8 -*-

from seishub.exceptions import InvalidParameterError
from seishub.test import SeisHubEnvironmentTestCase
from seishub.xmldb.xpath import XPathQuery, RestrictedXPathQueryParser
import unittest


class XPathQueryParserTest(SeisHubEnvironmentTestCase):
    def setUp(self):
        self.parser = RestrictedXPathQueryParser()
        
    def tearDown(self):
        del self.parser
        
    def testInvalid(self):
        queries = ["/testtype/rootnode[./element1]",
                   "/rootnode[./element1]",
                   "/pkg/rt/rootnode[child[blah]]",
                   "[/rootnode/child]",
                   ]
        _ = [self.assertRaises(InvalidParameterError, self.parser.parse, q) 
             for q in queries]
        
    def testLocationStepOnly(self):
        queries = ['/package/resourcetype/rootnode',
                   '/package/resourcetype/*',
                   '/package/*/*',
                   '/*/*/*']
        # location path is stored into the parser object
        self.parser.parse(queries[0])
        self.assertEqual(self.parser.package_id, 'package')
        self.assertEqual(self.parser.resourcetype_id, 'resourcetype')
        self.assertEqual(self.parser.rootnode, 'rootnode')
        self.parser.parse(queries[1])
        self.assertEqual(self.parser.package_id, 'package')
        self.assertEqual(self.parser.resourcetype_id, 'resourcetype')
        self.assertEqual(self.parser.rootnode, '*')
        self.parser.parse(queries[2])
        self.assertEqual(self.parser.package_id, 'package')
        self.assertEqual(self.parser.resourcetype_id, '*')
        self.assertEqual(self.parser.rootnode, '*')
        self.parser.parse(queries[3])
        self.assertEqual(self.parser.package_id, '*')
        self.assertEqual(self.parser.resourcetype_id, '*')
        self.assertEqual(self.parser.rootnode, '*')
        
    def testKeyLessQuery(self):
        queries = ['/pid/rid/rn[attr]',
                   '/pid/rid/rn[node/./attr]',
                   '/pid/rid/rn[./node/attr]',
                   '/pid/rid/rn[../../rt/*/node/attr]',
                   '/pid/rid/rn[@attr]',
                   '/pid/rid/rn[./@attr]',
                   '/pid/rid/rn[./node/@attr]',
                   '/seismology/station/xseed[volume_index_control_header/' +\
                     'volume_identifier/beginning_time]',
                   '/seismology/station/*[volume_index_control_header/' +\
                     'volume_identifier/beginning_time]'
                   ]
        res = [self.parser.parse(q) for q in queries]
#        for r in res:
#            print '\n' + str(r.predicates)
#        
    def testSingleKeyQuery(self):
        queries = ['/pid/rid/rn[attr = "blah"]',
                   '/pid/rid/rn[node/attr = "blah"]',
                   '/pid/rid/rn[./node/attr = "blah"]',
                   '/pid/rid/rn[@attr = "blah"]',
                   '/pid/rid/rn[./@attr = "blah"]',
                   '/pid/rid/rn[./node/@attr = "blah"]',
                   '/pid/rid/rn[/pid2/rt2/rn2/node/@attr = "blah"]',
                   '/pid/rid/rn[../../../pid2/rid2/*/node/attr = "blah"]',
                   '/pid/rid/rn[../../rid2/*/node/attr = "blah"]',
                   '/pid/rid/rn[../*/node/attr = "blah"]',
                   '/pid/rid/rn[attr = -1.5]'
                   ]
        res = [self.parser.parse(q) for q in queries]
#        for r in res:
#            print '\n' + str(r.predicates)
#            
    def testSingleKeyNamespaceQuery(self):
        queries = ['/pid/rid/rn[ns:attr = "blah"]',
                   '/pid/rid/rn[node/ns:attr = "blah"]',
                   '/pid/rid/rn[@ns:attr = "blah"]',
                   '/pid/rid/ns:rn[attr = "blah"]'
                   ]
        res = [self.parser.parse(q) for q in queries]
#        for r in res:
#            print '\n' + str(r.predicates)

#    def testXPathFunctionQuery(self):
#        queries = ['/pid/rid/rn[attr = "blah"]',
#                   ]
#        res = [self.parser.parse(q) for q in queries]
##        for r in res:
##            print '\n' + str(r.predicates)

    def testRelationalOperators(self):
        queries = {'/pid/rid/rn[attr1 = "blah"]' : '=',
                   '/pid/rid/rn[attr1 == "blah"]' : '=',
                   '/pid/rid/rn[attr1 < "blah"]' : '<',
                   '/pid/rid/rn[attr1 > "blah"]' : '>',
                   '/pid/rid/rn[attr1 <= "blah"]' : '<=',
                   '/pid/rid/rn[attr1 >= "blah"]' : '>=',
                   '/pid/rid/rn[attr1 != "blah"]' : '!=',
                   }
        res = [(self.parser.parse(q), t) for q, t in queries.iteritems()]
        for r, t in res:
            self.assertEqual(r.predicates[1], t)
           
    def testLogicalOperators(self):
        queries = ['/pid/rid/rn[attr1 = "blah" and attr2 = "bluh"]',
                   '/pid/rid/rn[attr1 = "blah" or attr2 = "bluh"]',
                   ]
        res = [self.parser.parse(q) for q in queries]
        self.assertEqual(res[0].predicates[1], 'and')
        self.assertEqual(res[1].predicates[1], 'or')
     
    def testMultipleKeyQuery(self):
        queries = ['/pid/rid/rn[attr1 = "blah" and attr2 = "bluh"]',
                   '/pid/rid/rn[attr1 = "blah" and (attr2 = "bluh" or attr2 = "bloh")]',
                   '/pid/rid/rn[(attr1 = "blah" and attr2 = "bluh") or attr2 = "bloh"]',
                   '/pid/rid/rn[(attr1 = "blah" and attr2 = "bluh") or attr2 = "bloh"]',
                   '/pid/rid/rn[attr1 = "blah" and (attr2 = "bluh" and (attr2 = "bloh" or attr3 = "moep"))]',
                   '/package/rt/station[lat>49 and lat<56 and lon=22.51200]'
                   ]
        res = [self.parser.parse(q) for q in queries]
#        for r in res:
#            print '\n' + str(r.predicates)
         
    def testJoinedPathQuery(self):
        queries = ['/pid/rid/rn[node1 = node2]',
                   '/pid/rid/rn[node1 = ./node2/@id]',
                   '/pid/rid/rn[node1 = ../../rt2/*/node2]',
                   ]
        res = [self.parser.parse(q) for q in queries]
#        for r in res:
#            print '\n' + str(r.predicates)

    def testOrderByLimitOffsetQuery(self):
        queries = ['/pid/rid/rn order by node1',
                   '/pid/rid/rn order by node1 asc',
                   '/pid/rid/rn order by node1 desc',
                   '/pid/rid/rn order by node1 desc, node2',
                   '/pid/rid/rn order by node1 asc limit 5',
                   '/pid/rid/rn order by node1 limit 5,10',
                   '/pid/rid/rn order by node1/@id',
                   '/pid/rid/rn order by ./node1/node2',
                   '/pid/rid/rn order by node1/@id limit 5,10',
                   '/pid/rid/rn[node1 = "blah"] order by node2, node3/@id desc limit 5,10',
                   ]
        res = [self.parser.parse(q) for q in queries]
#        for r in res:
#            print '\n' + str(r.order_by)
#            print str(r.limit)
#            print str(r.offset)

    def testXMLNodeLevelQuery(self):
        queries = ['/pid/rid/rn/node',
                   '/pid/rid/rn/@attr1',
                   '/pid/rid/*/node',
                   '/*/*/*/node',
                   '/pid/rid/rn/node[@id = "abc"]',
                   ]
        res = [self.parser.parse(q) for q in queries]
        
    def testNotFunction(self):
        queries = ['/pid/rid/rn[not(attr1)]',
                   '/pid/rid/rn[attr1 = "blah" and not(attr2)]',
                   '/pid/rid/rn[not(attr1 = "blah")]',
                   '/pid/rid/rn[not(attr1 = "blah" and attr2 = "bluh") or attr2 = "bloh"]',
                   '/pid/rid/rn[attr1 = "blah" and not(attr2 = "bluh" and (attr2 = "bloh" or not(attr3 = "moep")))]',
                   '/pid/rid/rn[not(XY/paramXY = 2.5) and not(missing)]'
                   ]
        res = [self.parser.parse(q) for q in queries]
        for r in res:
            self.assertTrue(len(r.predicates) <= 3)

     
class XPathQueryTest(SeisHubEnvironmentTestCase):
    def testXPathQuery(self):
        q = "/testpackage/testtype/rootnode[./element1/element2 = 'blub' " +\
            "and ./element1/@id <= 5] "+\
            "order by element1/element2 desc, element3 asc limit 10,20"
        query = XPathQuery(q)
        self.assertEqual(query.getLocationPath(), ['testpackage', 'testtype', 
                                                   'rootnode'])
        self.assertEqual(query.getOrderBy(), [[['testpackage', 'testtype', 
                                              'rootnode/element1/element2'], 
                                              'desc'],
                                              [['testpackage', 'testtype', 
                                               'rootnode/element3'], 'asc']])
        self.assertEqual(query.getLimit(), 10)
        self.assertEqual(query.getOffset(), 20)
        self.assertEqual(query.isTiny(), False)
        
    def testTinyFlag(self):
        q = "t/testpackage/testtype/rootnode[./element1/element2 = 'blub' " +\
            "and ./element1/@id <= 5] "+\
            "order by element1/element2 desc, element3 asc limit 10,20"
        query = XPathQuery(q)
        self.assertEqual(query.isTiny(), True)
        
    def testLocationPath(self):
        q = "/pkg/rt/rootnode"
        query = XPathQuery(q)
        self.assertEqual(query.getLocationPath(), q.split('/')[1:])
        q = "/pkg/rt/rootnode/node1/node2"
        query = XPathQuery(q)
        self.assertEqual(query.getLocationPath(), q.split('/')[1:])
        q = "/pkg/rt/rootnode/node2/node1"
        query = XPathQuery(q)
        self.assertEqual(query.getLocationPath(), q.split('/')[1:])
        
#    test_expr = "/testpackage/testtype/rootnode[./element1/element2 = 'blub' and ./element1/@id <= 5]"
#    wildcard_expr = "/*/*/rootnode[./element1/element2 = 'blub']"
#    join_expr = "/seispkg/network/*[../event/*/station = ../network/*/station and ./@id = ../station/*/@id and ../event/*/datetime = yesterday]"
        
def suite():
    suite = unittest.TestSuite()
    # suite.addTest(unittest.makeSuite(XpathTest, 'test'))
    suite.addTest(unittest.makeSuite(XPathQueryTest, 'test'))
    suite.addTest(unittest.makeSuite(XPathQueryParserTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')