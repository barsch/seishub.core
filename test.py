#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest, sys, doctest, os
from seishub.util.path import rglob 


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
    import glob
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
    import os
    sys.path.insert(0, os.curdir)
    sys.path[:] = map(os.path.abspath, sys.path)

    from twisted.scripts.trial import run
    # say trial which tests to run:
    sys.argv.append(sys.path[0])
    run()

if __name__ == '__main__':
    import doctest, sys, os, string
    doctest.testmod(sys.modules[__name__])
    main(defaultTest='doctestsuite')
    
    trialsuite()
    
    