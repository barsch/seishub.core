#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

def suite():
    import seishub.tests

    suite = unittest.TestSuite()
    suite.addTest(seishub.tests.suite())

    return suite

if __name__ == '__main__':
    import doctest, sys
    doctest.testmod(sys.modules[__name__])
    unittest.main(defaultTest='suite')