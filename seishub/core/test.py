#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SeisHub's test runner.

This script will run every test included into SeisHub.
"""

from seishub.core.config import Configuration
from seishub.core.db import DEFAULT_PREFIX
from seishub.core.env import Environment
import copy
import doctest
import sys
import unittest


USE_TEST_DB = 'sqlite://'
#USE_TEST_DB = 'postgres://seishub:seishub@localhost:5432/seishub-test'
#USE_TEST_DB = 'mysql://seishub:seishub@localhost:3306/seishub-test'


# use this options below only for debugging test cases
CHECK_DATABASE = True
CLEAN_DATABASE = True
DISPOSE_CONNECTION = True
VERBOSE_DATABASE = False


class SeisHubEnvironmentTestCase(unittest.TestCase):
    """
    Generates a temporary SeisHub environment without any service.

    We generate a temporary configuration file, an environment object and
    disable logging at all. Any class inheriting from this test case may
    overwrite the _config method to preset additional options to the test
    environment.

    Don't ever overwrite the __init__ or run methods!
    """

    def __init__(self, methodName='runTest', filename=None):  # @UnusedVariable
        """
        Initialize the test procedure.
        """
        unittest.TestCase.__init__(self, methodName)
        self.default_config = Configuration()
        #set a few standard settings
        self.default_config.set('seishub', 'log_level', 'OFF')
        self.default_config.set('seishub', 'auth_uri', 'sqlite://')
        self.default_config.set('db', 'uri', USE_TEST_DB)
        self.default_config.set('db', 'verbose', VERBOSE_DATABASE)

    def _config(self):
        """
        Method to write into the temporary configuration file.

        This method may be overwritten from any test case to set up
        configuration parameters needed for the test case.
        """
        pass

    def __setUp(self):
        """
        Sets the environment up before each test case.
        """
        # generate a copy of default configuration
        self.config = copy.copy(self.default_config)
        # apply user defined options
        self._config()
        self.config.save()
        # create environment
        self.env = Environment('', config_file=self.config, log_file=None)
        self.env.initComponent(self)
        # read number of data in tables auto-generated
        if CHECK_DATABASE:
            self.tables = {}
            sql = "SELECT * FROM %s;"
            tables = self.env.db.engine.table_names()
            tables = [t for t in tables if t.startswith(DEFAULT_PREFIX)]
            for table in tables:
                res = self.env.db.engine.execute(sql % str(table)).fetchall()
                self.tables[table] = len(res)
        # enforcement foreign key constraints in SQLite
        if self.env.db.isSQLite():
            self.env.db.engine.execute('PRAGMA FOREIGN_KEYS=ON')

    def __tearDown(self):
        """
        Clean up database and remove environment objects after each test case.
        """
        # check for left over data and warn
        if CHECK_DATABASE:
            sql = "SELECT * FROM %s;"
            tables = self.env.db.engine.table_names()
            tables = [t for t in tables if t.startswith(DEFAULT_PREFIX)]
            for table in tables:
                res = self.env.db.engine.execute(sql % str(table)).fetchall()
                if len(res) != self.tables.get(table, 0):
                    print "table %s: %d!=%d in %s" % (table,
                        self.tables.get(table, 0), len(res), str(self))
        # clean up DB
        if CLEAN_DATABASE:
            # disable foreign key constraints in SQLite
            if self.env.db.isSQLite():
                self.env.db.engine.execute('PRAGMA FOREIGN_KEYS=OFF')
                sql = "DROP TABLE %s;"
            else:
                sql = "DROP TABLE %s CASCADE;"
            tables = self.env.db.engine.table_names()
            tables = [t for t in tables if t.startswith(DEFAULT_PREFIX)]
            for table in tables:
                try:
                    self.env.db.engine.execute(sql % str(table))
                except:
                    pass
        # manually dispose DB connection
        if DISPOSE_CONNECTION:
            self.env.db.engine.pool.dispose()
        # remove objects
        del(self.config)
        del(self.env)

    def run(self, result=None):
        """
        Calls unittest.TestCase.run() adopted for our uses.
        """
        self.__setUp()
        unittest.TestCase.run(self, result)
        self.__tearDown()


def getSuite():
    """
    This methods calls all test suites.
    """
    from seishub.core.registry.tests import suite as registry_suite
    from seishub.core.processor.tests import suite as processor_suite
    from seishub.core.tests import suite as tests_suite
    from seishub.core.util.tests import suite as util_suite
    from seishub.core.xmldb.tests import suite as xmldb_suite
    from seishub.core.db.tests import suite as db_suite

    suite = unittest.TestSuite()
    suite.addTest(registry_suite())
    suite.addTest(processor_suite())
    suite.addTest(tests_suite())
    suite.addTest(util_suite())
    suite.addTest(xmldb_suite())
    suite.addTest(db_suite())

    return suite


if __name__ == '__main__':
    doctest.testmod(sys.modules[__name__])
    unittest.main(module='seishub.core.test', defaultTest='getSuite')
