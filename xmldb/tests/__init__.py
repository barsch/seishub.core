#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import seishub.test
from seishub.test import doctestsuite,trialsuite

if __name__ == '__main__':
    import doctest, sys
    doctest.testmod(sys.modules[__name__])
    seishub.test.main(defaultTest='doctestsuite')
    trialsuite()
    
    