# -*- coding: utf-8 -*-

from seishub.registry.tests import test_registry, test_processorindex, \
    test_registry_fromfilesystem
import doctest
import unittest


def suite():
    suite = unittest.TestSuite()
    suite.addTest(test_registry.suite())
    suite.addTest(test_registry_fromfilesystem.suite())
    suite.addTest(test_processorindex.suite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')