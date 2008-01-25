# -*- coding: utf-8 -*-

import inspect
import sys

from twisted.web import server
from twisted.internet import reactor, defer
from twisted.application import service

from seishub.core import Component, implements
from seishub.services.admin.interfaces import IAdminPanel
from seishub.util.text import getTextUntilDot


class BasicPanel(Component):
    """Basic configuration."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('admin', 'General', 'basic', 'Basic settings')
    
    def renderPanel(self, request):
        if request.method == 'POST':
            for option in ('url', 'default_charset', 'description'):
                self.config.set('seishub', option, request.args.get(option,[])[0])
            self.config.save()
            request.redirect(request.path)
        data = {
          'url': self.config.get('seishub', 'url'),
          'default_charset': self.config.get('seishub', 'default_charset'),
          'description': self.config.get('seishub', 'description'),
        }
        return ('general_basic.tmpl', data)

class ConfigPanel(Component):
    """General configuration."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('admin', 'General', 'config', 'Config')
    
    def renderPanel(self, request):
        data = {}
        sections = self.config.sections()
        data['sections'] = sections
        data['options'] = {}
        for s in sections:
            options = self.config.options(s)
            data['options'][s] = options
        return ('general_config.tmpl', data)


class RESTRedirect(Component):
    """REST redirect."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('rest', 'REST', 'rest', 'REST')
    
    def renderPanel(self, request):
        request.redirect('http://localhost:8080/')
        return ('',{})


class LogsPanel(Component):
    """Web based log viewer."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('admin', 'General', 'logs', 'Logs')
    
    def renderPanel(self, request):
        data = {
          'logs': 'testdaten', 
        }
        return ('general_logs.tmpl', data)


class PluginsPanel(Component):
    """Administration of plugins."""
    implements(IAdminPanel)
    
    required_components = ('seishub.services.admin.general.PluginsPanel', 
                           'seishub.env.Environment',)
    
    def getPanelId(self):
        return ('admin', 'General', 'plugins', 'Plugins')
    
    def renderPanel(self, request):
        if request.method == 'POST':
            if 'update' in request.args:
                self._updatePlugins(request)
            request.redirect(request.path)
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
                # enable components activated during runtime manually:
                if not component in self.env:
                    self.env.enabled[component]=True
                    self.env[component]
                    self.config.set('components', fullname, 'enabled')
                    self.log.info('Enabling component %s', fullname)
            else:
                # disable components
                if component in self.env:
                    self.env.enabled[component]=False
                    del self.env[component]
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
            description = getTextUntilDot(inspect.getdoc(component)) 
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
        return ('general_plugins.tmpl', data)


class ServicesPanel(Component):
    """Administration of services."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('admin', 'General', 'services', 'Services')
    
    def renderPanel(self, request):
        data = {
          'services': service.IServiceCollection(self.env.app),
        }
        if request.method == 'POST':
            if request.args.has_key('shutdown'):
                self._shutdownSeisHub()
            elif request.args.has_key('reload'):
                self._changeServices(request)
            elif request.args.has_key('restart'):
                self._restartSeisHub()
        return ('general_services.tmpl', data)
    
    def _shutdownSeisHub(self):
        reactor.stop()
    
    def _restartSeisHub(self):
        pass
    
    def _changeServices(self, request):
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
        defer.DeferredList(actions).addCallback(self._finishedActions, request)
        return server.NOT_DONE_YET
    
    def _finishedActions(self, results, request):
        request.redirect(request.path)
        request.finish()
