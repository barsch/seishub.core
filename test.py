#!/usr/bin/env python
# -*- coding: utf-8 -*-

from seishub.config import Configuration
from seishub.env import Environment
import sys
import doctest
import os
import tempfile
import random
import unittest


class SeisHubEnvironmentTestCase(unittest.TestCase):
    """Generates a temporary SeisHub environment without any running service.
    
    We generate a temporary configuration file, a SQLite data base and disable 
    logging at all. Any class inheriting from this test case may overwrite the 
    _config method to preset additional options to the test environment.
    """
    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)
        self.filename = os.path.join(tempfile.gettempdir(), 
                                     'seishub-test.ini' + \
                                     str(random.randint(1, 100000)))
        self.config = Configuration(self.filename)
        #set a few standard settings
        self.config.set('logging', 'log_level', 'OFF')
#        self.config.set('db', 'uri', 
#                        'postgres://seishub:seishub@localhost:5432/seishub')
        self.config.set('db', 'uri', 'sqlite://')
        self.config.set('seishub', 'auth_uri', 'sqlite://')
        self._config()
        self._start()
        
    def __del__(self):
        os.remove(self.filename)
    
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
    from seishub.processor.tests import suite as processor_suite
    from seishub.services.tests import suite as services_suite
    from seishub.tests import suite as tests_suite
    from seishub.util.tests import suite as util_suite
    from seishub.xmldb.tests import suite as xmldb_suite
    from seishub.db.tests import suite as db_suite
    
    suite = unittest.TestSuite()
    suite.addTest(packages_suite())
    suite.addTest(processor_suite())
    suite.addTest(services_suite())
    suite.addTest(tests_suite())
    suite.addTest(util_suite())
    suite.addTest(xmldb_suite())
    suite.addTest(db_suite())
    
    return suite


if __name__ == '__main__':
    doctest.testmod(sys.modules[__name__])
    unittest.main(defaultTest='suite')