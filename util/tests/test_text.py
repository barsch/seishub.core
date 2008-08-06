# -*- coding: utf-8 -*-

import unittest
from seishub.util.text import validate_id

class TextUtilTest(unittest.TestCase):
    def testValidate_id(self):
        good = "aValidId_1"
        bad0 = ""
        #bad1 = "1invalidId"
        #bad2 = "_invalid_too"
        self.assertEquals(validate_id(good), good)
        self.assertRaises(ValueError, validate_id, bad0)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TextUtilTest, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')