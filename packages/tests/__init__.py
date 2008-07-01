# -*- coding: utf-8 -*-

import doctest
import unittest

from seishub.packages.tests import test_registry, test_processor


def suite():
    suite = unittest.TestSuite()
    suite.addTest(test_registry.suite())
    suite.addTest(test_processor.suite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')