# -*- coding: utf-8 -*-

from seishub.tests import test_config, test_core, test_core_zope_compatibility, \
    test_core_twisted_compatibility
import doctest
import unittest


def suite():
    suite = unittest.TestSuite()
    suite.addTest(test_core.suite())
    suite.addTest(test_core_zope_compatibility.suite())
    suite.addTest(test_core_twisted_compatibility.suite())
    suite.addTest(doctest.DocFileSuite('test_core_twisted_compatibility.txt'))
    suite.addTest(test_config.suite())
    suite.addTest(doctest.DocFileSuite('test_config.txt'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
