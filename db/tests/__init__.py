# -*- coding: utf-8 -*-

import doctest
import unittest

from seishub.db.tests import test_orm


def suite():
    suite = unittest.TestSuite()
    suite.addTest(test_orm.suite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')