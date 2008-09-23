# -*- coding: utf-8 -*-

import doctest
import unittest

from seishub.util.tests import test_xmlwrapper, test_demjson, test_text


def suite():
    suite = unittest.TestSuite()
    suite.addTest(test_xmlwrapper.suite())
    suite.addTest(test_text.suite())
    suite.addTest(test_demjson.suite())
    suite.addTest(doctest.DocFileSuite('test_http.txt'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')