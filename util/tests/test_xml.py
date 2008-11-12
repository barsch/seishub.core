# -*- coding: utf-8 -*-

import unittest
from seishub.util.xml import parseXMLDeclaration

TEST_BASE = """<seishub xml:base="http://localhost:8080" xmlns:xlink="http://www.w3.org/1999/xlink">
    <mapping xlink:type="simple" xlink:href="/seishub/schema/browser">browser</mapping>
    <resource xlink:type="simple" xlink:href="/seishub/schema/3">/seishub/schema/3</resource>
    <resource xlink:type="simple" xlink:href="/seishub/schema/4">/seishub/schema/4</resource>
</seishub>"""

TEST_W_ENC = '<?xml version="1.0" encoding="%s"?>' + TEST_BASE

TEST_WO_ENC = '<?xml version="1.0" ?>' + TEST_BASE


class XMLUtilTest(unittest.TestCase):
    """Test case for various XML helper tools."""
    
    def test_parseXMLDeclaration_unicode(self):
        """Tests parsing the XML declaration of an unicode object."""
        # with cutting declaration
        data, enc = parseXMLDeclaration(unicode(TEST_W_ENC % 'UTF-8'), True)
        assert data == TEST_BASE
        assert enc == 'UTF-8'
        data, enc = parseXMLDeclaration(unicode(TEST_WO_ENC), True)
        assert data == TEST_BASE
        assert enc == 'UTF-8'
        # without cutting declaration
        data, enc = parseXMLDeclaration(unicode(TEST_W_ENC % 'UTF-8'), False)
        assert data == TEST_W_ENC % 'UTF-8'
        assert enc == 'UTF-8'
        data, enc = parseXMLDeclaration(unicode(TEST_WO_ENC), False)
        assert data == TEST_WO_ENC
        assert enc == 'UTF-8'
    
    def test_parseXMLDeclaration_str(self):
        """Tests parsing the XML declaration of a str object."""
        # with cutting declaration
        data, enc = parseXMLDeclaration(TEST_W_ENC % 'UTF-8', True)
        assert data == TEST_BASE
        assert enc == 'UTF-8'
        data, enc = parseXMLDeclaration(TEST_WO_ENC, True)
        assert data == TEST_BASE
        assert enc == 'UTF-8'
        # without cutting declaration
        data, enc = parseXMLDeclaration(TEST_W_ENC % 'UTF-8', False)
        assert data == TEST_W_ENC % 'UTF-8'
        assert enc == 'UTF-8'
        data, enc = parseXMLDeclaration(TEST_WO_ENC, False)
        assert data == TEST_WO_ENC
        assert enc == 'UTF-8'
    
    def test_parseXMLDeclaration_utf8(self):
        """Tests parsing the XML declaration of an utf-8 encoded string."""
        temp = unicode(TEST_W_ENC % 'UTF-8').encode('UTF-8')
        # with cutting declaration
        data, enc = parseXMLDeclaration(temp, True)
        assert data == TEST_BASE
        assert enc == 'UTF-8'
        # without cutting declaration
        data, enc = parseXMLDeclaration(temp, False)
        assert data == TEST_W_ENC % 'UTF-8'
        assert enc == 'UTF-8'
        # without encoding
        temp = unicode(TEST_WO_ENC).encode('UTF-8')
        # with cutting declaration
        data, enc = parseXMLDeclaration(temp, True)
        assert data == TEST_BASE
        assert enc == 'UTF-8'
        # without cutting declaration
        data, enc = parseXMLDeclaration(temp, False)
        assert data == TEST_WO_ENC
        assert enc == 'UTF-8'
    
    def test_parseXMLDeclaration_UTF16(self):
        """XXX: these tests fail, see ticket #76 
        Tests parsing the XML declaration of an utf-16 encoded string."""
        temp = unicode(TEST_W_ENC % 'UTF-16').encode('UTF-16')
        # with cutting declaration
        data, enc = parseXMLDeclaration(temp, True)
        assert enc == 'UTF-16'
        assert data == TEST_BASE
        # without cutting declaration
        data, enc = parseXMLDeclaration(temp, False)
        assert enc == 'UTF-16'
        assert data == TEST_W_ENC % 'UTF-16'


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(XMLUtilTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')