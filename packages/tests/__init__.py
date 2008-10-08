# -*- coding: utf-8 -*-

import doctest
import unittest

from seishub.packages.tests import test_registry
from seishub.packages.tests import test_processor
from seishub.packages.tests import test_processor_MOVE


def suite():
    suite = unittest.TestSuite()
    suite.addTest(test_registry.suite())
    suite.addTest(test_processor.suite())
    suite.addTest(test_processor_MOVE.suite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')