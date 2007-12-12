from zope.interface import implements
from twisted.web import resource

from seishub.services.admin.interfaces import IAdminPanel
from seishub.core import Component

class BasicsPanel(Component, resource.Resource):
    #implements(IAdminPanel)
    
    def __init__(self):
        #resource.Resource.__init__(self)
        pass
        
    def render_GET(self, request):
        request.write("blah")
        return ''
