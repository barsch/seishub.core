from zope.interface.exceptions import DoesNotImplement

from twisted.trial.unittest import TestCase

from seishub.core import SeishubError
from seishub.xmldb.xmlresource import XmlResource
from seishub.xmldb.xmlindex import XmlIndex

RAW_XML1="""<station rel_uri="bern">
    <station_code>BERN</station_code>
    <chan_code>1</chan_code>
    <stat_type>0</stat_type>
    <lon>12.51200</lon>
    <lat>50.23200</lat>
    <stat_elav>0.63500</stat_elav>
</station>"""

class XmlIndexTest(TestCase):
    def testEval(self):
        test_index=XmlIndex()
        empty_resource=XmlResource()
        test_resource=XmlResource(uri='/stations/bern',
                                  xml_data=RAW_XML1)
        
        class Foo(object):
            pass
        
        # pass Foo() object:
        self.assertRaises(DoesNotImplement,
                          test_index.eval,
                          Foo())
        #pass empty XmlDoc:
        self.assertRaises(SeishubError,
                          test_index.eval,
                          empty_resource)
        
        print test_index.eval(test_resource)
        
        
        