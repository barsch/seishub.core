# -*- coding: utf-8 -*-

import unittest
from seishub.util.xml import parseXMLDeclaration

TEST_BASE = """<seishub xml:base="http://localhost:8080" xmlns:xlink="http://www.w3.org/1999/xlink">
    <mapping xlink:type="simple" xlink:href="/seishub/schema/browser">browser</mapping>
    <resource xlink:type="simple" xlink:href="/seishub/schema/3">/seishub/schema/3</resource>
    <resource xlink:type="simple" xlink:href="/seishub/schema/4">/seishub/schema/4</resource>
</seishub>"""

TEST_U_W_ENC = u'<?xml version="1.0" encoding="UTF-8"?>' + unicode(TEST_BASE)

TEST_U_WO_ENC = u'<?xml version="1.0"?>' + unicode(TEST_BASE)

TEST_STR_W_ENC = '<?xml version="1.0" encoding="UTF-8"?>' + TEST_BASE

TEST_STR_WO_ENC = '<?xml version="1.0"?>' + TEST_BASE


class XMLUtilTest(unittest.TestCase):
    def testParseXMLDeclaration(self):
        data, enc = parseXMLDeclaration(TEST_U_W_ENC, True)
        assert data == TEST_BASE
        assert enc == "UTF-8"
        data, enc = parseXMLDeclaration(TEST_U_WO_ENC, True)
        assert data == TEST_BASE
        assert enc == "UTF-8"
        data, enc = parseXMLDeclaration(TEST_STR_W_ENC, True)
        assert data == TEST_BASE
        assert enc == "UTF-8"
        data, enc = parseXMLDeclaration(TEST_STR_WO_ENC, True)
        assert data == TEST_BASE
        assert enc == "UTF-8"


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(XMLUtilTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')