# -*- coding: utf-8 -*-
"""
General configuration panels for the web-based administration service.
"""

import inspect
import sys
import os

from twisted.internet import reactor
from twisted.application import service

from seishub.core import Component, implements
from seishub.services.admin.interfaces import IAdminPanel
from seishub.defaults import DEFAULT_COMPONENTS
from seishub.util.text import getFirstSentence
from seishub.exceptions import SeisHubError


class BasicPanel(Component):
    """Basic configuration."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('admin', 'General', 'basic', 'Basic Settings')
    
    def renderPanel(self, request):
        if request.method == 'POST':
            for option in ('host', 'description'):
                self.config.set('seishub', option, 
                                request.args.get(option,[])[0])
            for option in ('theme',):
                self.config.set('webadmin', option, 
                                request.args.get(option,[])[0])
            self.config.save()
            request.redirect(request.path)
        data = {
          'host': self.config.get('seishub', 'host'),
          'description': self.config.get('seishub', 'description'),
          'theme': self.config.get('webadmin', 'theme'),
          'themes': request.getAllAdminThemes(),
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
        return ('rest-redirect', 'REST', 'rest-redirect', 'REST')
    
    def renderPanel(self, request):
        url = self.env.getRestUrl()
        request.redirect(url)
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


class PermissionsPanel(Component):
    """Administration of users and groups."""
    implements(IAdminPanel)
    
    def getPanelId(self):
        return ('admin', 'General', 'permissions', 'Permissions')
    
    def renderPanel(self, request):
        data = {}
        # process POST request
        if request.method == 'POST':
            args = request.args
            if 'delete' in args.keys():
                data = self._deleteUser(args)
            elif 'add' in args.keys():
                data = self._addUser(args)
        # default values
        result = {
            'id': '',
            'name': '',
            'email': '',
            'institution': '',
            'users': self.auth.users 
        }
        result.update(data)
        return ('general_permissions.tmpl', result)
    
    def _addUser(self, args):
        """Adds a new user."""
        data = {}
        id = data['id'] = args.get('id', [''])[0]
        password = args.get('password', [''])[0]
        confirmation = args.get('confirmation', [''])[0]
        name = data['name'] = args.get('name', [''])[0]
        email = data['email'] = args.get('email', [''])[0]
        institution = data['institution'] = args.get('institution', [''])[0]
        if not id:
            data['error'] = "No user id given."
        elif not name:
            data['error'] = "No user name given."
        elif password != confirmation:
            data['error'] = "Password and password confirmation are not equal!"
        else:
            try:
                self.auth.addUser(id=id, name=name, password=password, 
                                  email=email, institution=institution)
            except SeisHubError, e:
                # password checks are made in self.auth.addUser method 
                data['error'] = e.message
            except Exception, e:
                self.log.error("Error adding new user", e)
                data['error'] = "Error adding new user", e
            else:
                data = {'info': "New user has been added."}
        return data
    
    def _deleteUser(self, args):
        """Deletes on or multiple users."""
        data = {}
        id = args.get('id', [''])[0]
        if not id:
            data['error'] = "No user selected."
        else:
            try:
                self.auth.deleteUser(id=id)
            except SeisHubError(), e:
                # checks are made in self.auth.deleteUser method 
                data['error'] = e.message
            except Exception, e:
                self.log.error("Error deleting user", e)
                data['error'] = "Error deleting user", e
            else:
                data = {'info': "User has been deleted."}
        return data


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
            modulename = module.__name__
            classname = modulename + '.' + component.__name__
            if classname in enabled or classname in DEFAULT_COMPONENTS or \
               modulename in DEFAULT_COMPONENTS:
                if not self.env.isComponentEnabled(classname):
                    self.env.enableComponent(component)
            else:
                if self.env.isComponentEnabled(classname):
                    self.env.disableComponent(component)
    
    def _viewPlugins(self, request):
        plugins = {}
        from seishub.core import ComponentMeta
        for component in ComponentMeta._components:
            module = sys.modules[component.__module__]
            description = getFirstSentence(inspect.getdoc(module))
            modulename = module.__name__
            classname = modulename + '.' + component.__name__
            plugin = {
              'name': component.__name__, 
              'module': module.__name__,
              'file': module.__file__,
              'classname': classname,
              'description': getFirstSentence(inspect.getdoc(component)),
              'enabled': self.env.isComponentEnabled(classname),
              'required': classname in DEFAULT_COMPONENTS or \
                          modulename in DEFAULT_COMPONENTS,
            }
            plugins.setdefault(modulename,{})
            plugins[modulename].setdefault('plugins',[]).append(plugin)
            plugins[modulename]['description'] = description
        sorted_plugins = plugins.keys()
        sorted_plugins.sort()
        data = {
          'sorted_plugins': sorted_plugins, 
          'plugins': plugins,
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
        reactor.stop() #@UndefinedVariable
    
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