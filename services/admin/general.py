# -*- coding: utf-8 -*-

import inspect
import sys
import os
from twisted.internet import reactor
from twisted.application import service

from seishub.core import Component, implements
from seishub.services.admin.interfaces import IAdminPanel
from seishub.defaults import DEFAULT_COMPONENTS


class BasicPanel(Component):
    """Basic configuration."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('admin', 'General', 'basic', 'Basic Settings')
    
    def renderPanel(self, request):
        if request.method == 'POST':
            for option in ('ip', 'default_charset', 'description'):
                self.config.set('seishub', option, 
                                request.args.get(option,[])[0])
            self.config.save()
            request.redirect(request.path)
        data = {
          'ip': self.config.get('seishub', 'ip'),
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
        port = self.env.config.get('rest', 'port')
        ip = self.env.config.get('seishub', 'ip')
        url = 'http://%s:%s/' % (ip, port)
        request.redirect(str(url))
        return ('',{})


class LogsPanel(Component):
    """Web based log viewer."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('admin', 'General', 'logs', 'Logs')
    
    def renderPanel(self, request):
        access_log_file = self.env.config.get('logging', 'access_log_file')
        error_log_file = self.env.config.get('logging', 'error_log_file')
        log_dir = os.path.join(self.env.config.path, 'log')
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
                self.env.enableComponent(component)
            else:
                self.env.disableComponent(component)
    
    def _viewPlugins(self, request):
        plugins = {}
        from seishub.core import ComponentMeta
        for component in ComponentMeta._components:
            module = sys.modules[component.__module__]
            description = inspect.getdoc(component)
            
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
            plugins.setdefault(module.__name__,[]).append(plugin)
        sorted_plugins = plugins.keys()
        sorted_plugins.sort()
        data = {
          'sorted_plugins': sorted_plugins, 
          'plugins': plugins,
        }
        return ('general_plugins.tmpl', data)


class PackagesPanel(Component):
    """Lists all installed packages."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('admin', 'General', 'packages', 'Packages')
    
    def renderPanel(self, request):
        data = {}
        # XXX: we should use a package registry!!!
        from seishub.core import ExtensionPoint
        from seishub.packages.interfaces import IPackage
        data['packages'] = ExtensionPoint(IPackage).extensions(self.env)
        return ('general_packages.tmpl', data)


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
    
    def _changeServices(self, request):
        serviceList = request.args.get('service', [])
        for srv in service.IServiceCollection(self.env.app):
            if srv.running and not srv.name in serviceList:
                self.env.disableService(srv.name)
            elif not srv.running and srv.name in serviceList:
                self.env.enableService(srv.name)
        request.redirect(request.path)
        request.finish()    