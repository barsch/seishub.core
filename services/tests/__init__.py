# -*- coding: utf-8 -*-

import doctest
import unittest


def suite():
    suite = unittest.TestSuite()
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')