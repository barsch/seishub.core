# -*- coding: utf-8 -*-

from seishub.core.db.tests import test_orm
import doctest
import unittest


def suite():
    suite = unittest.TestSuite()
    suite.addTest(test_orm.suite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
