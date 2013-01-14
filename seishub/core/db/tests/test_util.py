# -*- coding: utf-8 -*-
import re
import unittest

from seishub.core.db import util


class dummy_request(object):
    """
    Dummy request object to test the formatting functions.
    """
    def __init__(self, format):
        self.args = {"format": format, "output": ""}
        self.env = self
        self.env.getRestUrl = self.getRestUrl

    def setHeader(*args, **kwargs):
            pass

    def getRestUrl(*args, **kwargs):
        return "NO/URL"


def normalize_whitespace(string):
    """
    Helper function to normalize all whitespaces to a simple space.
    """
    string = string.strip()
    return re.sub(r'\s+', ' ', string)


class DBUtilTestCase(unittest.TestCase):
    """
    Tests suite for the database utils.
    """
    def test_formatResults_simpleXML(self):
        """
        Tests simple XML formatting.
        """
        result = [{"attrib_1": "1", "attrib_2": 2},
                {"attrib_1": "1", "attrib_2": 2}]
        formatted_result = util.formatResults(dummy_request("xml"), result)

        self.assertEqual(normalize_whitespace(formatted_result),
            normalize_whitespace("""
                <?xml version='1.0' encoding='utf-8'?>
                <ResultSet totalResultsReturned="2" totalResultsAvailable="2"
                    firstResultPosition="0">
                  <Item>
                    <attrib_1>1</attrib_1>
                    <attrib_2>2</attrib_2>
                  </Item>
                  <Item>
                    <attrib_1>1</attrib_1>
                    <attrib_2>2</attrib_2>
                  </Item>
                </ResultSet>"""))

    def test_formatResults_nestedXML(self):
        """
        Tests nested XML formatting.
        """
        result = [{"attrib_1": "a",
            "nested_attribs": {"a": 1, "b": 2}}]
        formatted_result = util.formatResults(dummy_request("xml"), result)
        self.assertEqual(normalize_whitespace(formatted_result),
            normalize_whitespace("""
                <?xml version='1.0' encoding='utf-8'?>
                <ResultSet totalResultsReturned="1" totalResultsAvailable="1"
                    firstResultPosition="0">
                  <Item>
                    <attrib_1>a</attrib_1>
                    <nested_attribs>
                      <a>1</a>
                      <b>2</b>
                    </nested_attribs>
                  </Item>
                </ResultSet>"""))

    def test_formatResults_XML(self):
        """
        Tests nested XML formatting.
        """
        result = [{"attrib_1": "a", "list_of_a": [{"a": "2"}, {"a": "3"}]}]
        formatted_result = util.formatResults(dummy_request("xml"), result)
        self.assertEqual(normalize_whitespace(formatted_result),
            normalize_whitespace("""
                <?xml version='1.0' encoding='utf-8'?>
                <ResultSet totalResultsReturned="1" totalResultsAvailable="1"
                    firstResultPosition="0">
                  <Item>
                    <attrib_1>a</attrib_1>
                    <list_of_a>
                      <a>2</a>
                      <a>3</a>
                    </list_of_a>
                  </Item>
                </ResultSet>"""))


def suite():
    return unittest.makeSuite(DBUtilTestCase, 'test')


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
