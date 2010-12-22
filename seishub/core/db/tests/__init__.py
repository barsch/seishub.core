# -*- coding: utf-8 -*-

from seishub.core.db.tests import test_orm, test_util
import doctest
import unittest


def suite():
    suite = unittest.TestSuite()
    suite.addTest(test_orm.suite())
    suite.addTest(test_util.suite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
