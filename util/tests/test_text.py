# -*- coding: utf-8 -*-

from seishub.util.text import validate_id, getFirstSentence
import unittest


class TextUtilTest(unittest.TestCase):
    """
    """
    def test_validateId(self):
        """
        """
        good = "aValidId_1"
        bad0 = ""
        self.assertEquals(validate_id(good), good)
        self.assertRaises(ValueError, validate_id, bad0)

    def test_getFirstSentence(self):
        """
        """
        # example 1
        original = " muh. "
        expected = "muh."
        self.assertEquals(getFirstSentence(original), expected)
        # example 2
        original = """
            muh maeh. blub
        """
        expected = "muh maeh."
        self.assertEquals(getFirstSentence(original), expected)
        # example 3
        original = "muh.maeh.blub."
        expected = "muh."
        self.assertEquals(getFirstSentence(original), expected)
        # example 4
        original = "m" * 600
        expected = "m" * 255
        self.assertEquals(getFirstSentence(original), expected)
        # example 4
        original = "m" * 600
        expected = "m" * 5
        self.assertEquals(getFirstSentence(original, 5), expected)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TextUtilTest, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
