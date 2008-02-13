# -*- coding: utf-8 -*-

from seishub.test import SeisHubTestCase


class XmlCatalogTest(SeisHubTestCase):
    def test_default(self):
        print self.config.get('seishub','database')


def suite():
    return unittest.makeSuite(XMLTestCase, 'test')

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
