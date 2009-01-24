# -*- coding: utf-8 -*-

from seishub.util.tests import test_xml, test_xmlwrapper, test_text
import doctest
import unittest


def suite():
    suite = unittest.TestSuite()
    suite.addTest(test_xmlwrapper.suite())
    suite.addTest(test_text.suite())
    suite.addTest(test_xml.suite())
    suite.addTest(doctest.DocFileSuite('test_http.txt'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')