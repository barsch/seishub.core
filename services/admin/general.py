# -*- coding: utf-8 -*-

import inspect
import sys
import os
from twisted.internet import reactor, defer
from twisted.application import service

from seishub.core import Component, implements
from seishub.services.admin.interfaces import IAdminPanel
from seishub.util.text import getTextUntilDot
from seishub.defaults import DEFAULT_COMPONENTS
from seishub.config import Option


class BasicPanel(Component):
    """Basic configuration."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('admin', 'General', 'basic', 'Basic Settings')
    
    def renderPanel(self, request):
        if request.method == 'POST':
            for option in ('url', 'default_charset', 'description'):
                self.config.set('seishub', option, 
                                request.args.get(option,[])[0])
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
        data['opt1'] = self.config.defaults()
        data['opt2'] = Option.registry
        return ('general_config.tmpl', data)


class RESTRedirect(Component):
    """REST redirect."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('rest', 'REST', 'rest', 'REST')
    
    def renderPanel(self, request):
        # XXX: should not be fixed
        request.redirect('http://localhost:8080/')
        return ('',{})


class LogsPanel(Component):
    """Web based log viewer."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('admin', 'General', 'logs', 'Logs')
    
    def renderPanel(self, request):
        access_log_file = self.env.access_log_file
        error_log_file = self.env.error_log_file
        log_dir = os.path.join(self.env.path, 'log')
        log_file = os.path.join(log_dir, access_log_file)
        try:
            fh = open(log_file, 'r')
            logs = fh.readlines()
            fh.close()  
        except:
            logs = ["Can't open log file."]
        access_logs = logs[-500:]
        log_file = os.path.join(log_dir, error_log_file)
        try:
            fh = open(log_file, 'r')
            logs = fh.readlines()
            fh.close()  
        except:
            logs = ["Can't open log file."]
        error_logs = logs[-500:]
        data = {
          'accesslog': access_logs, 
          'errorlog': error_logs, 
        }
        return ('general_logs.tmpl', data)


class PluginsPanel(Component):
    """Administration of plugins."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('admin', 'General', 'plugins', 'Plugins')
    
    def renderPanel(self, request):
        if request.method == 'POST':
            if 'update' in request.args:
                self._updatePlugins(request)
            if 'reload' in request.args:
                self._refreshPlugins()
            request.redirect(request.path)
            request.finish()
            return
        return self._viewPlugins(request)
    
    def _refreshPlugins(self):
        from seishub.loader import ComponentLoader
        ComponentLoader(self.env)
    
    def _updatePlugins(self, request):
        """Update components."""
        enabled = request.args.get('enabled',[])
        
        from seishub.core import ComponentMeta
        for component in ComponentMeta._components:
            module = sys.modules[component.__module__]
            fullname = module.__name__+'.'+component.__name__
            
            if fullname in enabled or fullname in DEFAULT_COMPONENTS:
                # enable components activated during runtime manually:
                if not component in self.env:
                    self.env.enabled[component]=True
                    self.env[component]
                    self.config.set('components', fullname, 'enabled')
                    self.log.info('Enabling component %s' % fullname)
            else:
                # disable components
                if component in self.env:
                    self.env.enabled[component]=False
                    del self.env[component]
                    self.config.set('components', fullname, 'disabled')
                    self.log.info('Disabling component %s' % fullname)
        
        self.config.save()
    
    def _viewPlugins(self, request):
        packages = {}
        from seishub.core import ComponentMeta
        for component in ComponentMeta._components:
            module = sys.modules[component.__module__]
            # create a one line description
            description = getTextUntilDot(inspect.getdoc(component)) 
            
            classname = module.__name__+'.'+component.__name__
            plugin = {
              'name': component.__name__, 
              'module': module.__name__,
              'file': module.__file__,
              'classname': classname,
              'description': description,
              'enabled': self.env.isComponentEnabled(component),
              'required': classname in DEFAULT_COMPONENTS,
            }
            packages.setdefault(module.__name__,[]).append(plugin)
        sorted_packages = packages.keys()
        sorted_packages.sort()
        data = {
          'sorted_packages': sorted_packages, 
          'packages': packages,
        }
        return ('general_plugins.tmpl', data)


class ServicesPanel(Component):
    """Administration of services."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('admin', 'General', 'services', 'Services')
    
    def renderPanel(self, request):
        if request.method == 'POST':
            if request.args.has_key('shutdown'):
                self._shutdownSeisHub()
            elif request.args.has_key('reload'):
                self._changeServices(request)
                return
            elif request.args.has_key('restart'):
                self._restartSeisHub()
        data = {
          'services': service.IServiceCollection(self.env.app),
        }
        return ('general_services.tmpl', data)
    
    def _shutdownSeisHub(self):
        reactor.stop()
    
    def _restartSeisHub(self):
        pass
    
    @defer.inlineCallbacks
    def _changeServices(self, request):
        serviceList = request.args.get('service', [])
        for srv in service.IServiceCollection(self.env.app):
            if srv.running and not srv.name in serviceList:
                yield defer.maybeDeferred(srv.stopService)
                self.log.info('Stopping service %s' % srv.name)
            elif not srv.running and srv.name in serviceList:
                yield defer.maybeDeferred(srv.startService)
                self.log.info('Starting service %s' % srv.name)
        request.redirect(request.path)
        request.finish()    