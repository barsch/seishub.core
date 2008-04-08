# -*- coding: utf-8 -*-

import doctest
import unittest

from seishub.util.tests import test_xml


def suite():
    suite = unittest.TestSuite()
    suite.addTest(test_xml.suite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')