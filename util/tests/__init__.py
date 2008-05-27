# -*- coding: utf-8 -*-

import doctest
import unittest

from seishub.util.tests import test_xml, test_json


def suite():
    suite = unittest.TestSuite()
    suite.addTest(test_xml.suite())
    suite.addTest(test_json.suite())
    suite.addTest(doctest.DocFileSuite('test_http.txt'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')