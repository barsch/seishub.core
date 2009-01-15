# -*- coding: utf-8 -*-
"""
Processor and resources related test suite.
"""

import doctest
import unittest


def suite():
    from seishub.processor.tests import test_processor, test_rest_PUT, \
        test_rest, test_rest_DELETE, test_rest_POST, test_mapper, \
        test_rest_GET, test_rest_MOVE, test_tree, test_rest_PUT_validation
    suite = unittest.TestSuite()
    suite.addTest(test_processor.suite())
    suite.addTest(test_rest_PUT.suite())
    suite.addTest(test_rest_PUT_validation.suite())
    suite.addTest(test_rest_POST.suite())
    suite.addTest(test_rest_MOVE.suite())
    suite.addTest(test_rest_GET.suite())
    suite.addTest(test_rest_DELETE.suite())
    suite.addTest(test_rest.suite())
    suite.addTest(test_tree.suite())
    suite.addTest(test_mapper.suite())
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')