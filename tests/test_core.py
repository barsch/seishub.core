import unittest
from seishub.core import ComponentManager, Component, ComponentMeta

class ComponentManagerTestCase(unittest.TestCase):
    def test_component(self):
        cmpmgr = ComponentManager()
        class ComponentA(Component):
            pass
        assert ComponentA in ComponentMeta._components
        assert cmpmgr[ComponentA]
        assert cmpmgr.components.has_key(ComponentA)
        
def suite():
    return unittest.makeSuite(ComponentManagerTestCase, 'test')
        
if __name__ == '__main__':
    unittest.main()