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
        queries = ["/testtype[./element1]",
                   "/package[./element1]",
                   "/pkg/rt[rootnode/child[blah]]",
                   "[/rootnode/child]",
                   ]
        _ = [self.assertRaises(InvalidParameterError, self.parser.parse, q)
             for q in queries]

    def testLocationStepOnly(self):
        queries = ['/package/resourcetype',
                   '/package/*',
                   '/*/*']
        # location path is stored into the parser object
        self.parser.parse(queries[0])
        self.assertEqual(self.parser.package_id, 'package')
        self.assertEqual(self.parser.resourcetype_id, 'resourcetype')
        self.parser.parse(queries[1])
        self.assertEqual(self.parser.package_id, 'package')
        self.assertEqual(self.parser.resourcetype_id, '*')
        self.parser.parse(queries[2])
        self.assertEqual(self.parser.package_id, '*')
        self.assertEqual(self.parser.resourcetype_id, '*')

    def testKeyLessQuery(self):
        queries = ['/pid/rid[rn/attr]',
                   '/pid/rid[rn/node/./attr]',
                   '/pid/rid[./rn/node/attr]',
                   '/pid/rid[../rt/*/node/attr]',
                   '/pid/rid[rn/@attr]',
                   '/pid/rid[rn/./@attr]',
                   '/pid/rid[rn/./node/@attr]',
                   '/seismology/station[xseed/volume_index_control_header/' + \
                     'volume_identifier/beginning_time]',
                   '/seismology/station[*/volume_index_control_header/' + \
                     'volume_identifier/beginning_time]'
                   ]
        results = [[['pid', 'rid', 'rn/attr']],
                   [['pid', 'rid', 'rn/node/attr']],
                   [['pid', 'rid', 'rn/node/attr']],
                   [['pid', 'rt', '*/node/attr']],
                   [['pid', 'rid', 'rn/@attr']],
                   [['pid', 'rid', 'rn/@attr']],
                   [['pid', 'rid', 'rn/node/@attr']],
                   [['seismology', 'station',
                     'xseed/volume_index_control_header/volume_identifier/' + \
                     'beginning_time']],
                   [['seismology', 'station',
                     '*/volume_index_control_header/volume_identifier/' + \
                     'beginning_time']]
                   ]
        res = [self.parser.parse(q) for q in queries]
        for i, r in enumerate(res):
            self.assertEqual(r.predicates.asList(), results[i])

    def testSingleKeyQuery(self):
        queries = ['/pid/rid[rn/attr = "blah"]',
                   '/pid/rid[rn/node/attr = "blah"]',
                   '/pid/rid[rn/./node/attr = "blah"]',
                   '/pid/rid[rn/@attr = "blah"]',
                   '/pid/rid[rn/./@attr = "blah"]',
                   '/pid/rid[rn/./node/@attr = "blah"]',
                   '/pid/rid[/pid2/rt2/rn2/node/@attr = "blah"]',
                   '/pid/rid[../../pid2/rid2/*/node/attr = "blah"]',
                   '/pid/rid[../rid2/*/node/attr = "blah"]',
                   '/pid/rid[*/node/attr = "blah"]',
                   '/pid/rid[rn/attr = -1.5]'
                   ]
        results = [[['pid', 'rid', 'rn/attr'], '=', 'blah'],
                   [['pid', 'rid', 'rn/node/attr'], '=', 'blah'],
                   [['pid', 'rid', 'rn/node/attr'], '=', 'blah'],
                   [['pid', 'rid', 'rn/@attr'], '=', 'blah'],
                   [['pid', 'rid', 'rn/@attr'], '=', 'blah'],
                   [['pid', 'rid', 'rn/node/@attr'], '=', 'blah'],
                   [['pid2', 'rt2', 'rn2/node/@attr'], '=', 'blah'],
                   [['pid2', 'rid2', '*/node/attr'], '=', 'blah'],
                   [['pid', 'rid2', '*/node/attr'], '=', 'blah'],
                   [['pid', 'rid', '*/node/attr'], '=', 'blah'],
                   [['pid', 'rid', 'rn/attr'], '=', '-1.5']
                   ]
        res = [self.parser.parse(q) for q in queries]
        for i, r in enumerate(res):
            self.assertEqual(r.predicates.asList(), results[i])

    def testSingleKeyNamespaceQuery(self):
        queries = ['/pid/rid[rn/ns:attr = "blah"]',
                   '/pid/rid[rn/node/ns:attr = "blah"]',
                   '/pid/rid[rn/@ns:attr = "blah"]',
                   '/pid/rid[ns:rn/attr = "blah"]'
                   ]
        results = [[['pid', 'rid', 'rn/ns:attr'], '=', 'blah'],
                   [['pid', 'rid', 'rn/node/ns:attr'], '=', 'blah'],
                   [['pid', 'rid', 'rn/@ns:attr'], '=', 'blah'],
                   [['pid', 'rid', 'ns:rn/attr'], '=', 'blah']
                   ]
        res = [self.parser.parse(q) for q in queries]
        for i, r in enumerate(res):
            self.assertEqual(r.predicates.asList(), results[i])

    def testRelationalOperators(self):
        queries = {'/pid/rid[rn/attr1 = "blah"]' : '=',
                   '/pid/rid[rn/attr1 == "blah"]' : '=',
                   '/pid/rid[rn/attr1 < "blah"]' : '<',
                   '/pid/rid[rn/attr1 > "blah"]' : '>',
                   '/pid/rid[rn/attr1 <= "blah"]' : '<=',
                   '/pid/rid[rn/attr1 >= "blah"]' : '>=',
                   '/pid/rid[rn/attr1 != "blah"]' : '!=',
                   }
        res = [(self.parser.parse(q), t) for q, t in queries.iteritems()]
        for r, t in res:
            self.assertEqual(r.predicates[1], t)

    def testLogicalOperators(self):
        queries = ['/pid/rid[rn/attr1 = "blah" and rn/attr2 = "bluh"]',
                   '/pid/rid[rn/attr1 = "blah" or rn/attr2 = "bluh"]',
                   ]
        res = [self.parser.parse(q) for q in queries]
        self.assertEqual(res[0].predicates[1], 'and')
        self.assertEqual(res[1].predicates[1], 'or')

    def testMultipleKeyQuery(self):
        queries = ['/pid/rid[rn/attr1 = "blah" and rn/attr2 = "bluh"]',
                   '/pid/rid[rn/attr1 = "blah" and (rn/attr2 = "bluh" or' + \
                   ' rn/attr2 = "bloh")]',
                   '/pid/rid[(rn/attr1 = "blah" and rn/attr2 = "bluh") or ' + \
                   'rn/attr2 = "bloh"]',
                   '/pid/rid[(rn/attr1 = "blah" and rn/attr2 = "bluh") or ' + \
                   'rn/attr2 = "bloh"]',
                   '/pid/rid[rn/attr1 = "blah" and (rn/attr2 = "bluh" and ' + \
                   '(rn/attr2 = "bloh" or rn/attr3 = "moep"))]',
                   '/package/rt[station/lat>49 and station/lat<56 and ' + \
                   'station/lon=22.51200]'
                   ]
        results = [[[['pid', 'rid', 'rn/attr1'], '=', 'blah'], 'and',
                     [['pid', 'rid', 'rn/attr2'], '=', 'bluh']],
                   [[['pid', 'rid', 'rn/attr1'], '=', 'blah'], 'and',
                     [[['pid', 'rid', 'rn/attr2'], '=', 'bluh'], 'or',
                       [['pid', 'rid', 'rn/attr2'], '=', 'bloh']]],
                   [[[['pid', 'rid', 'rn/attr1'], '=', 'blah'], 'and',
                      [['pid', 'rid', 'rn/attr2'], '=', 'bluh']], 'or',
                       [['pid', 'rid', 'rn/attr2'], '=', 'bloh']],
                   [[[['pid', 'rid', 'rn/attr1'], '=', 'blah'], 'and',
                      [['pid', 'rid', 'rn/attr2'], '=', 'bluh']], 'or',
                       [['pid', 'rid', 'rn/attr2'], '=', 'bloh']],
                   [[['pid', 'rid', 'rn/attr1'], '=', 'blah'], 'and',
                     [[['pid', 'rid', 'rn/attr2'], '=', 'bluh'], 'and',
                       [[['pid', 'rid', 'rn/attr2'], '=', 'bloh'], 'or',
                         [['pid', 'rid', 'rn/attr3'], '=', 'moep']]]],
                   [[['package', 'rt', 'station/lat'], '>', '49'], 'and',
                     [[['package', 'rt', 'station/lat'], '<', '56'], 'and',
                       [['package', 'rt', 'station/lon'], '=', '22.51200']]]
                   ]
        res = [self.parser.parse(q) for q in queries]
        for i, r in enumerate(res):
            self.assertEqual(r.predicates.asList(), results[i])

    def testJoinedPathQuery(self):
        queries = ['/pid/rid[rn/node1 = rn/node2]',
                   '/pid/rid[rn/node1 = ./rn/node2/@id]',
                   '/pid/rid[rn/node1 = ../rt2/*/node2]',
                   ]
        res = [self.parser.parse(q) for q in queries]
        results = [[['pid', 'rid', 'rn/node1'], '=',
                    ['pid', 'rid', 'rn/node2']],
                   [['pid', 'rid', 'rn/node1'], '=',
                    ['pid', 'rid', 'rn/node2/@id']],
                   [['pid', 'rid', 'rn/node1'], '=',
                    ['pid', 'rt2', '*/node2']]
                   ]
        for i, r in enumerate(res):
            self.assertEqual(r.predicates.asList(), results[i])

    def testOrderByLimitOffsetQuery(self):
        queries = ['/pid/rid order by rn/node1',
                   '/pid/rid order by rn/node1 asc',
                   '/pid/rid order by rn/node1 desc',
                   '/pid/rid order by rn/node1 desc, rn/node2',
                   '/pid/rid order by rn/node1 asc limit 5',
                   '/pid/rid order by rn/node1 limit 5,10',
                   '/pid/rid order by rn/node1/@id',
                   '/pid/rid order by ./rn/node1/node2',
                   '/pid/rid order by rn/node1/@id limit 5,10',
                   '/pid/rid[rn/node1 = "blah"] order by rn/node2, ' + \
                   'rn/node3/@id desc limit 5,10',
                   ]
        results = [[[[['pid', 'rid', 'rn/node1'], 'asc']], '', ''],
                   [[[['pid', 'rid', 'rn/node1'], 'asc']], '', ''],
                   [[[['pid', 'rid', 'rn/node1'], 'desc']], '', ''],
                   [[[['pid', 'rid', 'rn/node1'], 'desc'],
                     [['pid', 'rid', 'rn/node2'], 'asc']], '', ''],
                   [[[['pid', 'rid', 'rn/node1'], 'asc']], '5', ''],
                   [[[['pid', 'rid', 'rn/node1'], 'asc']], '5', '10'],
                   [[[['pid', 'rid', 'rn/node1/@id'], 'asc']], '', ''],
                   [[[['pid', 'rid', 'rn/node1/node2'], 'asc']], '', ''],
                   [[[['pid', 'rid', 'rn/node1/@id'], 'asc']], '5', '10'],
                   [[[['pid', 'rid', 'rn/node2'], 'asc'],
                     [['pid', 'rid', 'rn/node3/@id'], 'desc']], '5', '10']
                   ]
        res = [self.parser.parse(q) for q in queries]
        for i, r in enumerate(res):
            self.assertEqual(r.order_by.asList(), results[i][0])
            self.assertEqual(r.limit, results[i][1])
            self.assertEqual(r.offset, results[i][2])

    def testXMLNodeLevelQuery(self):
        queries = ['/pid/rid/rn/node',
                   '/pid/rid/rn/@attr1',
                   '/pid/rid/*/node',
                   '/*/*/*/node',
                   '/pid/rid/rn/node[@id = "abc"]',
                   '/pid/rid/rn/node[../othernode/@id = "abc"]',
                   '/pid/rid/rn/node[../../otherroot/node/@id = "abc"]',
                   '/pid/rid/rn/node[../../../otherrt/rn/node/@id = "abc"]',
                   '/pid/rid/rn/node[../../../../otherpkg/*/*/node/@id = "abc"]',
                   '/pid/rid/rn/node[../../../../otherpkg/*/*/node/../@id = "abc"]',
                   '/pid/rid/rn/node[/otherpkg/rt/*/node/../@id = "abc"]'
                   ]
        results = [['rn', 'node'],
                   ['rn', '@attr1'],
                   ['*', 'node'],
                   ['*', 'node'],
                   ['rn', 'node', ['pid', 'rid', 'rn/node/@id'], '=', 'abc'],
                   ['rn', 'node',
                    ['pid', 'rid', 'rn/othernode/@id'], '=', 'abc'],
                   ['rn', 'node',
                    ['pid', 'rid', 'otherroot/node/@id'], '=', 'abc'],
                   ['rn', 'node',
                    ['pid', 'otherrt', 'rn/node/@id'], '=', 'abc'],
                   ['rn', 'node',
                    ['otherpkg', '*', '*/node/@id'], '=', 'abc'],
                   ['rn', 'node',
                    ['otherpkg', '*', '*/node/../@id'], '=', 'abc'],
                   ['rn', 'node',
                    ['otherpkg', 'rt', '*/node/../@id'], '=', 'abc']
                   ]
        res = [self.parser.parse(q) for q in queries]
        for i, r in enumerate(res):
            self.assertEqual(r.asList(), results[i])

    def testNotFunction(self):
        queries = ['/pid/rid[not(rn/attr1)]',
                   '/pid/rid[rn/attr1 = "blah" and not(rn/attr2)]',
                   '/pid/rid[not(rn/attr1 = "blah")]',
                   '/pid/rid[not(rn/attr1 = "blah" and rn/attr2 = "bluh") or rn/attr2 = "bloh"]',
                   '/pid/rid[rn/attr1 = "blah" and not(rn/attr2 = "bluh" and (rn/attr2 = "bloh" or not(rn/attr3 = "moep")))]',
                   '/pid/rid[not(rn/XY/paramXY = 2.5) and not(rn/missing)]'
                   ]
        res = [self.parser.parse(q) for q in queries]
        for r in res:
            self.assertTrue(len(r.predicates) <= 3)


class XPathQueryTest(SeisHubEnvironmentTestCase):
    def testXPathQuery(self):
        q = "/testpackage/testtype[./rootnode/element1/element2 = 'blub' " + \
            "and rootnode/./element1/@id <= 5] " + \
            "order by rootnode/element1/element2 desc, rootnode/element3 asc" + \
            " limit 10,20"
        query = XPathQuery(q)
        self.assertEqual(query.getLocationPath(), ['testpackage', 'testtype'])
        self.assertEqual(query.getOrderBy(), [[['testpackage', 'testtype',
                                              'rootnode/element1/element2'],
                                              'desc'],
                                              [['testpackage', 'testtype',
                                               'rootnode/element3'], 'asc']])
        self.assertEqual(query.getLimit(), 10)
        self.assertEqual(query.getOffset(), 20)

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
