#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys, doctest, os, tempfile

from seishub.env import Environment
from seishub.config import Configuration


class SeisHubEnvironmentTestCase(unittest.TestCase):
    """This class is a unit test incoporating a valid SeisHub environment 
    without any service running. We generate a temporary configuration file, a
    sqlite data base and disable logging at all. Any class inheriting from 
    this test case may overwrite the _config method to preset additional
    options to the test environment."""
    def __init__(self, methodName):
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
        res = self.env.db.engine.execute("SELECT * from default_packages")
#        print self.__class__
#        print res.fetchall()
#        print "---------"
    
    def _config(self):
        """Method to write into temporary config file."""
    
    def _start(self):
        """Method to set the Environment."""
        self.config.save()
        self.env=Environment(self.filename)
        self.env.initComponent(self)


def suite():
    """This methods calls all test suites."""
    from seishub.packages.tests import suite as packages_suite
    from seishub.services.tests import suite as services_suite
    from seishub.tests import suite as tests_suite
    from seishub.util.tests import suite as util_suite
    from seishub.xmldb.tests import suite as xmldb_suite
    
    suite = unittest.TestSuite()
    suite.addTest(packages_suite())
    suite.addTest(services_suite())
    suite.addTest(tests_suite())
    suite.addTest(util_suite())
    suite.addTest(xmldb_suite())
    
    return suite


if __name__ == '__main__':
    doctest.testmod(sys.modules[__name__])
    unittest.main(defaultTest='suite')