# -*- coding: utf-8 -*-

import unittest
from seishub.test import SeisHubEnvironmentTestCase

class DbUtilTest(SeisHubEnvironmentTestCase):
#    def _config(self):
#        self.config.set('db', 'verbose', True)

    def testPickup(self):
        pass


def suite():
    return unittest.makeSuite(DbUtilTest, 'test')

if __name__ == '__main__':
    unittest.main(defaultTest='suite')