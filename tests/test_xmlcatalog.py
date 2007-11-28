# -*- coding: utf-8 -*-

from zope.interface.exceptions import DoesNotImplement

from twisted.trial.unittest import TestCase

from seishub.xmldb.xmlcatalog import XmlCatalog
from seishub.xmldb.xmldbms import XmlDbManager


class XmlCatalogTest(TestCase):
    def testRegisterIndex(self):
        pass
        #catalog=XmlCatalog()