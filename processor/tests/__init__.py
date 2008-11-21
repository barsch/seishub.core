# -*- coding: utf-8 -*-

from seishub.processor.tests import test_processor, test_processor_DELETE, \
    test_processor_GET, test_processor_MOVE, test_processor_POST, \
    test_processor_PUT, test_processor_mapper
import doctest
import unittest


def suite():
    suite = unittest.TestSuite()
    suite.addTest(test_processor.suite())
    suite.addTest(test_processor_PUT.suite())
    suite.addTest(test_processor_GET.suite())
    suite.addTest(test_processor_POST.suite())
    suite.addTest(test_processor_MOVE.suite())
    suite.addTest(test_processor_DELETE.suite())
    suite.addTest(test_processor_mapper.suite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')