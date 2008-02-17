# -*- coding: utf-8 -*-

import doctest
import unittest

from seishub.tests import test_config, test_core


def suite():
    suite = unittest.TestSuite()
    suite.addTest(test_core.suite())
    suite.addTest(test_config.suite())
    suite.addTest(doctest.DocFileSuite('test_config.txt'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')