#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys, doctest, os, tempfile
from seishub.env import Environment
from seishub.config import Configuration


class SeisHubTestCase(unittest.TestCase):
    """Base class used for SeisHub test cases"""
    def __init__(self,methodName):
        unittest.TestCase.__init__(self, methodName)
        self.filename = os.path.join(tempfile.gettempdir(), 'seishub-test.ini')
        self.config = Configuration(self.filename)
        #set a few standard settings
        self.config.set('logging', 'log_level', 'OFF')
#        self.config.set('db', 'uri', 
#                        'postgres://seishub:seishub@localhost:5432/seishub')
        self.config.set('db', 'uri', 'sqlite://')
        self._config()
        self._start()
    
    def _config(self):
        """Method to write into temporary config file."""
    
    def _start(self):
        """Method to set the Environment."""
        self.config.save()
        self.env=Environment(self.filename)
        self.env.initComponent(self)
    
#    def _printRes(self,res):
#        """little helper for debugging callbacks"""
#        print res
#        
    


def suite():
    import seishub.tests
    import seishub.services.tests
    import seishub.xmldb.tests
    import seishub.util.tests
    
    suite = unittest.TestSuite()
    suite.addTest(seishub.tests.suite())
    suite.addTest(seishub.services.tests.suite())
    suite.addTest(seishub.xmldb.tests.suite())
    suite.addTest(seishub.util.tests.suite())
    
    return suite


if __name__ == '__main__':
    doctest.testmod(sys.modules[__name__])
    unittest.main(defaultTest='suite')