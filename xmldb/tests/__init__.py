# -*- coding: utf-8 -*-

import doctest
import unittest

from seishub.xmldb.tests import test_xmlcatalog, test_xmldbms, test_xmlindex, \
                                test_xmlindexcatalog, test_xpath


def suite():
    suite = unittest.TestSuite()
    suite.addTest(test_xmlcatalog.suite())
    suite.addTest(test_xmldbms.suite())
    suite.addTest(test_xmlindex.suite())
    suite.addTest(test_xmlindexcatalog.suite())
    #suite.addTest(doctest.DocFileSuite('test_xmlindexcatalog.txt'))
    suite.addTest(test_xpath.suite())
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')