#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest, sys, doctest, os, tempfile
from seishub.env import Environment
from seishub.config import Configuration
from seishub.util.path import rglob
from twisted.trial.unittest import TestCase


class SeisHubTestCase(TestCase):
    """Base class used for SeisHub test cases"""
    def __init__(self,methodName):
        TestCase.__init__(self, methodName)
        self.filename = os.path.join(tempfile.gettempdir(), 'seishub-test.ini')
        self.config = Configuration(self.filename)
        #set a few standard settings
        self.config.set('logging', 'log_level', 'OFF')
        self.config.set('seishub', 'database', 'sqlite://')
        self._config()
        self._start()
    
    def _config(self):
        """Method to write into temporary config file."""
    
    def _start(self):
        """Method to set the Environment."""
        self.config.save()
        self.env=Environment(self.filename)
        self.env.initComponent(self)
    
    def _printRes(self,res):
        """little helper for debugging callbacks"""
        print res
    


class TestProgram(unittest.TestProgram):
    def __init__(self,**kwargs):
        unittest.TestProgram.__init__(self,**kwargs)
        
    def runTests(self):
        if self.testRunner is None:
            self.testRunner = unittest.TextTestRunner(verbosity=self.verbosity)
        result = self.testRunner.run(self.test)
        #sys.exit(not result.wasSuccessful())

main=TestProgram

def doctestsuite():
    suite = unittest.TestSuite()
    import seishub
    # get all .txt filenames in current dir and subdirs:
    txts=rglob(base_path=os.path.split(seishub.__file__)[0],
               search_path=os.path.abspath(sys.path[0]),
               ext=".txt")
    
    for txt in txts:
        suite.addTest(doctest.DocFileSuite(txt))
    
    return suite

def trialsuite():
    sys.path.insert(0, os.curdir)
    sys.path[:] = map(os.path.abspath, sys.path)

    from twisted.scripts.trial import run
    # say trial which tests to run:
    sys.argv.append(sys.path[0])
    run()

if __name__ == '__main__':
    doctest.testmod(sys.modules[__name__])
    main(defaultTest='doctestsuite')
    
    trialsuite()
    
    