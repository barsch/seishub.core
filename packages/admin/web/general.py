# -*- coding: utf-8 -*-
"""
General configuration panels for the web-based administration service.
"""

from seishub.core import Component, implements
from seishub.defaults import DEFAULT_COMPONENTS
from seishub.exceptions import SeisHubError
from seishub.packages.interfaces import IAdminPanel
from seishub.util.text import getFirstSentence
from twisted.application import service
from twisted.internet import reactor
import inspect
import os
import sys


class BasicPanel(Component):
    """
    Basic configuration.
    """
    implements(IAdminPanel)
    
    template = 'templates' + os.sep + 'general_basic.tmpl'
    panel_ids = ('admin', 'General', 'basic', 'Basic Settings')
    has_roles = ['SEISHUB_ADMIN']
    
    def render(self, request):
        data = {}
        if request.method == 'POST':
            for option in ('host', 'description'):
                self.config.set('seishub', option, 
                                request.args.get(option,[])[0])
            for option in ('theme',):
                self.config.set('webadmin', option, 
                                request.args.get(option,[])[0])
            self.config.save()
            data['info'] = "Options have been saved."
        temp = {
          'host': self.config.get('seishub', 'host'),
          'description': self.config.get('seishub', 'description'),
          'theme': self.config.get('webadmin', 'theme'),
          'themes': self.root.themes,
        }
        data.update(temp)
        return data


class ConfigPanel(Component):
    """
    General configuration.
    """
    implements(IAdminPanel)
    
    template = 'templates' + os.sep + 'general_config.tmpl'
    panel_ids = ('admin', 'General', 'config', 'Config')
    has_roles = ['SEISHUB_ADMIN']
    
    def render(self, request):
        data = {}
        sections = self.config.sections()
        data['sections'] = sections
        data['options'] = {}
        for s in sections:
            options = self.config.options(s)
            data['options'][s] = options
        return data


class LogsPanel(Component):
    """
    Web based log file viewer.
    """
    implements(IAdminPanel)
    
    template = 'templates' + os.sep + 'general_logs.tmpl'
    panel_ids = ('admin', 'General', 'logs', 'Logs')
    has_roles = ['SEISHUB_ADMIN']
    
    def render(self, request):
        error_log_file = self.env.config.get('logging', 'error_log_file')
        log_dir = os.path.join(self.env.config.path, 'logs')
        log_file = os.path.join(log_dir, error_log_file)
        try:
            fh = open(log_file, 'r')
            logs = fh.readlines()
            fh.close()  
        except:
            logs = ["Can't open log file."]
        error_logs = logs[-500:]
        data = {
          'errorlog': error_logs, 
        }
        return data


class UsersPanel(Component):
    """
    Administration of users.
    """
    implements(IAdminPanel)
    
    template = 'templates' + os.sep + 'general_users.tmpl'
    panel_ids = ('admin', 'General', 'permission-users', 'Users')
    has_roles = ['SEISHUB_ADMIN']
    
    def render(self, request):
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
        return result
    
    def _addUser(self, args):
        """
        Add a new user.
        """
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
        """
        Delete one or multiple users.
        """
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


class RolesPanel(Component):
    """
    Administration of roles.
    """
    implements(IAdminPanel)
    
    template = 'templates' + os.sep + 'general_roles.tmpl'
    panel_ids = ('admin', 'General', 'permission-roles', 'Roles')
    has_roles = ['SEISHUB_ADMIN']
    
    def render(self, request):
        data = {}
        return data


class GroupsPanel(Component):
    """
    Administration of groups.
    """
    implements(IAdminPanel)
    
    template = 'templates' + os.sep + 'general_roles.tmpl'
    panel_ids = ('admin', 'General', 'permission-groups', 'Groups')
    has_roles = ['SEISHUB_ADMIN']
    
    def render(self, request):
        data = {}
        return data


class PluginsPanel(Component):
    """
    Administration of plug-ins.
    """
    implements(IAdminPanel)
    
    template = 'templates' + os.sep + 'general_plugins.tmpl'
    panel_ids = ('admin', 'General', 'plug-ins', 'Plug-ins')
    has_roles = ['SEISHUB_ADMIN']
    
    def render(self, request):
        error = None
        if request.method == 'POST':
            if 'update' in request.args:
                error = self._updatePlugins(request)
                if not error:
                    request.redirect(request.uri)
                    request.finish()
                    return ""
            if 'reload' in request.args:
                self._refreshPlugins()
        return self._viewPlugins(request, error)
    
    def _refreshPlugins(self):
        from seishub.loader import ComponentLoader
        ComponentLoader(self.env)
    
    def _updatePlugins(self, request):
        """
        Update components.
        """
        enabled = request.args.get('enabled', [])
        error = []
        
        from seishub.core import ComponentMeta
        for component in ComponentMeta._components:
            module = sys.modules[component.__module__]
            modulename = module.__name__
            classname = modulename + '.' + component.__name__
            if classname in enabled or classname in DEFAULT_COMPONENTS or \
                modulename in DEFAULT_COMPONENTS:
                if not self.env.isComponentEnabled(classname):
                    msg = self.env.enableComponent(component)
                    if msg and msg not in error:
                        error.append(msg)
            elif self.env.isComponentEnabled(classname):
                msg = self.env.disableComponent(component)
                if msg and msg not in error:
                    error.append(msg)
        return error
    
    def _viewPlugins(self, request, error=None):
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
        data = {
          'sorted_plugins': sorted(plugins), 
          'plugins': plugins,
          'error': error,
        }
        return data


class ServicesPanel(Component):
    """
    Administration of services.
    """
    implements(IAdminPanel)
    
    template = 'templates' + os.sep + 'general_services.tmpl'
    panel_ids = ('admin', 'General', 'services', 'Services')
    has_roles = ['SEISHUB_ADMIN']
    
    def render(self, request):
        if request.method == 'POST':
            if 'shutdown' in request.args:
                self._shutdownSeisHub()
            elif 'reload' in request.args:
                self._changeServices(request)
            elif 'restart' in request.args:
                self._restartSeisHub()
        data = {
          'services': service.IServiceCollection(self.env.app),
        }
        return data
    
    def _shutdownSeisHub(self):
        reactor.stop() #@UndefinedVariable
    
    def _restartSeisHub(self):
        raise NotImplemented
    
    def _changeServices(self, request):
        serviceList = request.args.get('service', [])
        for srv in service.IServiceCollection(self.env.app):
            if srv.running and not srv.name in serviceList:
                self.env.disableService(srv.name)
            elif not srv.running and srv.name in serviceList:
                self.env.enableService(srv.name)
