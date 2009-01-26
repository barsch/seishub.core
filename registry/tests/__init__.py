# -*- coding: utf-8 -*-

import doctest
import unittest

from seishub.registry.tests import test_registry
from seishub.registry.tests import test_registry_fromfilesystem


def suite():
    suite = unittest.TestSuite()
    suite.addTest(test_registry.suite())
    suite.addTest(test_registry_fromfilesystem.suite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')