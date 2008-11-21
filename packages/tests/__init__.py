# -*- coding: utf-8 -*-

import doctest
import unittest

from seishub.packages.tests import test_registry


def suite():
    suite = unittest.TestSuite()
    suite.addTest(test_registry.suite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')