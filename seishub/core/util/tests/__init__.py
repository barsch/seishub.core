# -*- coding: utf-8 -*-

from seishub.core.util.tests import test_xml, test_xmlwrapper, test_text
import unittest


def suite():
    suite = unittest.TestSuite()
    suite.addTest(test_xmlwrapper.suite())
    suite.addTest(test_text.suite())
    suite.addTest(test_xml.suite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')