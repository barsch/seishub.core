# -*- coding: utf-8 -*-

import doctest
import unittest

from seishub.packages.tests import test_registry
from seishub.packages.tests import test_registry_fails
from seishub.packages.tests import test_processor
from seishub.packages.tests import test_processor_PUT
from seishub.packages.tests import test_processor_GET
from seishub.packages.tests import test_processor_POST
from seishub.packages.tests import test_processor_MOVE
from seishub.packages.tests import test_processor_DELETE
from seishub.packages.tests import test_processor_mapper


def suite():
    suite = unittest.TestSuite()
    suite.addTest(test_registry.suite())
    suite.addTest(test_processor.suite())
    suite.addTest(test_processor_PUT.suite())
    suite.addTest(test_processor_GET.suite())
    suite.addTest(test_processor_POST.suite())
    suite.addTest(test_processor_MOVE.suite())
    suite.addTest(test_processor_DELETE.suite())
    suite.addTest(test_processor_mapper.suite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')