# -*- coding: utf-8 -*-
import json
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


def normalize_xml_whitespace(string):
    """
    Helper function to normalize all whitespaces to a simple space.

    Also removes all whitespace between XML tags.
    """
    string = string.strip()
    string = re.sub(r"\s+", " ", string)
    return re.sub(r">\s*<", "><", string)


class DBUtilTestCase(unittest.TestCase):
    """
    Tests suite for the database utils.
    """
    def test_formatResults_simple_XML(self):
        """
        Tests simple XML formatting.
        """
        result = [{"attrib_1": "1", "attrib_2": 2},
                {"attrib_1": "1", "attrib_2": 2}]
        formatted_result = util.formatResults(dummy_request("xml"), result)

        self.assertEqual(normalize_xml_whitespace(formatted_result),
            normalize_xml_whitespace("""
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

    def test_formatResults_nested_XML(self):
        """
        Tests nested XML formatting.
        """
        result = [{"attrib_1": "a",
            "nested_attribs": {"a": 1, "b": 2}}]
        formatted_result = util.formatResults(dummy_request("xml"), result)
        self.assertEqual(normalize_xml_whitespace(formatted_result),
            normalize_xml_whitespace("""
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

    def test_formatResults_lists_XML(self):
        """
        Tests nested XML formatting.
        """
        result = [{"attrib_1": "a", "list_of_a": [{"a": "2"}, {"a": "3"}]}]
        formatted_result = util.formatResults(dummy_request("xml"), result)
        self.assertEqual(normalize_xml_whitespace(formatted_result),
            normalize_xml_whitespace("""
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

    def test_formatResults_simple_JSON(self):
        """
        Tests simple JSON formatting.
        """
        result = [{"attrib_1": "1", "attrib_2": 2},
                {"attrib_1": "1", "attrib_2": 2}]
        formatted_result = util.formatResults(dummy_request("json"), result)
        # Read again.
        output = json.loads(formatted_result)["ResultSet"]
        # Test the headers.
        self.assertEqual(output["totalResultsReturned"], 2)
        self.assertEqual(output["totalResultsAvailable"], 2)
        self.assertEqual(output["firstResultPosition"], 0)
        # Assert the actual contents.
        self.assertEqual(result, output["Result"])

    def test_formatResults_nested_JSON(self):
        """
        Tests nested JSON formatting.
        """
        result = [{"attrib_1": "a",
            "nested_attribs": {"a": 1, "b": 2}}]
        formatted_result = util.formatResults(dummy_request("json"), result)
        # Read again.
        output = json.loads(formatted_result)["ResultSet"]
        # Test the headers.
        self.assertEqual(output["totalResultsReturned"], 1)
        self.assertEqual(output["totalResultsAvailable"], 1)
        self.assertEqual(output["firstResultPosition"], 0)
        # Assert the actual contents.
        self.assertEqual(result, output["Result"])

    def test_formatResults_lists_JSON(self):
        """
        Tests nested JSON formatting.
        """
        result = [{"attrib_1": "a", "list_of_a": [{"a": "2"}, {"a": "3"}]}]
        formatted_result = util.formatResults(dummy_request("json"), result)
        # Read again.
        output = json.loads(formatted_result)["ResultSet"]
        # Test the headers.
        self.assertEqual(output["totalResultsReturned"], 1)
        self.assertEqual(output["totalResultsAvailable"], 1)
        self.assertEqual(output["firstResultPosition"], 0)
        # Assert the actual contents.
        self.assertEqual(result, output["Result"])

    def test_formatResults_simple_XHTML(self):
        """
        Tests simple XHTML formatting.
        """
        result = [{"attrib_1": "1", "attrib_2": 2},
                {"attrib_1": "1", "attrib_2": 2}]
        formatted_result = util.formatResults(dummy_request("xhtml"), result)
        self.assertEqual(normalize_xml_whitespace(formatted_result),
            normalize_xml_whitespace("""
                <html>
                    <body>
                        <table border="1">
                            <tr>
                                <th>attrib_1</th>
                                <th>attrib_2</th>
                            </tr>
                            <tr>
                                <td>1</td>
                                <td>2</td>
                            </tr>
                            <tr>
                                <td>1</td>
                                <td>2</td>
                            </tr>
                        </table>
                    </body>
                </html>"""))

    def test_formatResults_simple_XHTML_order(self):
        """
        Tests simple XHTML formatting and checks that the fields are ordered
        correctly.
        """
        result = [{"attrib_a": "1", "attrib_b": 2, "attrib_c": 3},
                  {"attrib_a": "1", "attrib_c": 3, "attrib_b": 2},
                  {"attrib_b": "2", "attrib_a": 1, "attrib_c": 3},
                  {"attrib_c": "3", "attrib_b": 2, "attrib_a": 1}]
        formatted_result = util.formatResults(dummy_request("xhtml"), result)
        self.assertEqual(normalize_xml_whitespace(formatted_result),
            normalize_xml_whitespace("""
                <html>
                    <body>
                        <table border="1">
                            <tr>
                                <th>attrib_a</th>
                                <th>attrib_b</th>
                                <th>attrib_c</th>
                            </tr>
                            <tr>
                                <td>1</td>
                                <td>2</td>
                                <td>3</td>
                            </tr>
                            <tr>
                                <td>1</td>
                                <td>2</td>
                                <td>3</td>
                            </tr>
                            <tr>
                                <td>1</td>
                                <td>2</td>
                                <td>3</td>
                            </tr>
                            <tr>
                                <td>1</td>
                                <td>2</td>
                                <td>3</td>
                            </tr>
                        </table>
                    </body>
                </html>"""))

    def test_formatResults_simple_XHTML_missing_field(self):
        """
        One of the later entries is missing a field. The function should be
        able to deal with it.
        """
        result = [{"attrib_1": "1", "attrib_2": 2},
                {"attrib_1": "1"}]
        formatted_result = util.formatResults(dummy_request("xhtml"), result)
        self.assertEqual(normalize_xml_whitespace(formatted_result),
            normalize_xml_whitespace("""
                <html>
                    <body>
                        <table border="1">
                            <tr>
                                <th>attrib_1</th>
                                <th>attrib_2</th>
                            </tr>
                            <tr>
                                <td>1</td>
                                <td>2</td>
                            </tr>
                            <tr>
                                <td>1</td>
                                <td></td>
                            </tr>
                        </table>
                    </body>
                </html>"""))


def suite():
    return unittest.makeSuite(DBUtilTestCase, 'test')


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
