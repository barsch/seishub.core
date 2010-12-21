#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SeisHub's test runner.

This script will run every test included into SeisHub.
"""

import doctest
import sys
import unittest


def main():
    doctest.testmod(sys.modules[__name__])
    unittest.main(module='seishub.test', defaultTest='getSuite')


if __name__ == '__main__':
    main()
