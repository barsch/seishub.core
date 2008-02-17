# -*- coding: utf-8 -*-

import doctest
import unittest

from seishub.util.tests import test_libxmlwrapper


def suite():
    suite = unittest.TestSuite()
    suite.addTest(test_libxmlwrapper.suite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')