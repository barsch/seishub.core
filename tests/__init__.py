# -*- coding: utf-8 -*-

import unittest
import doctest

from seishub.tests import test_config

def suite():
    suite = unittest.TestSuite()
    suite.addTest(test_config.suite())
    suite.addTest(doctest.DocFileSuite('test_config.txt'))
    suite.addTest(doctest.DocFileSuite('test_basics.txt'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
