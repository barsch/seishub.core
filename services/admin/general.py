# -*- coding: utf-8 -*-

import inspect
import sys

from twisted.web import server
from twisted.internet import reactor, defer
from twisted.application import service

from seishub.core import Component, implements
from seishub.services.admin.interfaces import IAdminPanel


class BasicsPanel(Component):
    """Basic settings."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('general', 'General', 'basics', 'Basic Settings')
    
    def renderPanel(self, request):
        return {'template': 'basics.tmpl', }


class LogsPanel(Component):
    """Web based log viewer."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('general', 'General', 'logs', 'Logs')
    
    def renderPanel(self, request):
        data = {
          'logs': 'testdaten', 
        }
        return {'template': 'logs.tmpl', 
                'data': data, }


class PluginsPanel(Component):
    """Administration of plugins."""
    implements(IAdminPanel)
    
    required_components = ('seishub.services.admin.general.PluginsPanel', 
                           'seishub.env.Environment', 
                           'seishub.services.admin.admin.AdminService')
    
    def getPanelId(self):
        return ('general', 'General', 'plugins', 'Plugins')
    
    def renderPanel(self, request):
        if request.method == 'POST':
            if 'update' in request.args:
                self._updatePlugins(request)
            request.redirect('plugins')
        return self._viewPlugins(request)

    def _updatePlugins(self, request):
        """Update component enablement."""
        enabled = request.args.get('enabled',[])
        required = self.required_components

        from seishub.core import ComponentMeta
        for component in ComponentMeta._components:
            module = sys.modules[component.__module__]
            fullname = module.__name__+'.'+component.__name__
            
            if fullname in enabled or fullname in required:
                self.config.set('components', fullname, 'enabled')
                self.log.info('Enabling component %s', fullname)
                self.env[component]
            else:
                self.config.set('components', fullname, 'disabled')
                self.log.info('Disabling component %s', fullname)
        self.config.save()
    
    def _viewPlugins(self, request):
        plugins = []
        from seishub.core import ComponentMeta
        for component in ComponentMeta._components:
            module = sys.modules[component.__module__]
            fullname = module.__name__+'.'+component.__name__
            
            # create a one line description
            description = inspect.getdoc(component) 
            if description:
                description = description.split('.', 1)[0] + '.'
            plugins.append({
              'name': component.__name__, 
              'module': module.__name__,
              'full': fullname,
              'description': description,
              'enabled': self.env.is_component_enabled(component),
              'required': fullname in self.required_components,
            })        
        data = {
          'plugins': plugins,
        }
        return {'template': 'plugins.tmpl', 
                'data': data, }


class ServicesPanel(Component):
    """Administration of services."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('general', 'General', 'services', 'Services')
    
    def renderPanel(self, request):
        data = {
          'services': service.IServiceCollection(self.env.app),
        }
        status = ''
        if request.method == 'POST':
            if request.args.has_key('shutdown'):
                self.__shutdownSeisHub()
            elif request.args.has_key('reload'):
                status = self.__changeServices(request)
            elif request.args.has_key('restart'):
                self.__restartSeisHub()
        return {'template': 'services.tmpl', 
                'data': data, 
                'status': status, }
    
    def __shutdownSeisHub(self):
        reactor.stop()
    
    def __restartSeisHub(self):
        pass
    
    def __changeServices(self, request):
        actions = []
        serviceList = request.args.get('service', [])
        for srv in service.IServiceCollection(self.env.app):
            if srv.running and not srv.name in serviceList:
                stopping = defer.maybeDeferred(srv.stopService)
                actions.append(stopping)
                self.log.info('Stopping service %s', srv.name)
            elif not srv.running and srv.name in serviceList:
                starting = defer.maybeDeferred(srv.startService)
                actions.append(starting)
                self.log.info('Starting service %s', srv.name)
        defer.DeferredList(actions).addCallback(self.__finishedActions, request)
        return server.NOT_DONE_YET
    
    def __finishedActions(self, results, request):
        request.redirect('services')
        request.finish()
