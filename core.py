# -*- coding: utf-8 -*-
#
# Copyright (C) 2003-2005 Edgewall Software
# Copyright (C) 2003-2004 Jonas BorgstrÃ¶m <jonas@edgewall.com>
# Copyright (C) 2004-2005 Christopher Lenz <cmlenz@gmx.de>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://trac.edgewall.org/wiki/TracLicense.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://trac.edgewall.org/log/.
#
# Author: Jonas Borgström <jonas@edgewall.com>
#         Christopher Lenz <cmlenz@gmx.de>

import sys

from zope.interface import Interface #@UnusedImport
from zope.interface.declarations import _implements, classImplements

__all__ = ['Component', 'ExtensionPoint', 'implements', 'Interface',
           'SeisHubError', 'ERROR', 'WARN', 'INFO', 'DEBUG', 'ComponentMeta',
           'ComponentManager', 'PackageManager']

ERROR = 0
WARN = 5
INFO = 10
DEBUG = 20





class SeisHubError(Exception):
    """Exception base class for errors in SeisHub."""
    
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class SeisHubMessageError(SeisHubError):
    """Exception base class for errors in SeisHub which contains at least a 
    simple error message.
    """
    
    def __init__(self, message, *args, **kwargs):
        SeisHubError.__init__(self, message, *args, **kwargs)
        self.message = message


class ExtensionPoint(property):
    """Marker class for extension points in components."""
    
    def __init__(self, interface):
        """Create the extension point.
        
        @param interface: the `Interface` subclass that defines the protocol
            for the extension point
        """
        property.__init__(self, self.extensions)
        self.interface = interface
        self.__doc__ = 'List of components that implement `%s`' % \
                       self.interface.__name__
    
    def extensions(self, component):
        """Return a list of components that declare to implement the extension
        point interface.
        """
        extensions = ComponentMeta._registry.get(self.interface, [])
        return filter(None, [component.compmgr[cls] for cls in extensions])
    
    def __repr__(self):
        """Return a textual representation of the extension point."""
        return '<ExtensionPoint %s>' % self.interface.__name__


class ComponentMeta(type):
    """Meta class for components.
    
    Takes care of component and extension point registration.
    """
    _components = []
    _registry = {}
    
    def __new__(cls, name, bases, d):
        """Create the component class."""
        new_class = type.__new__(cls, name, bases, d)
        if name == 'Component':
            # Don't put the Component base class in the registry
            return new_class

        # Only override __init__ for Components not inheriting ComponentManager
        if True not in [issubclass(x, ComponentManager) for x in bases]:
            # Allow components to have a no-argument initializer so that
            # they don't need to worry about accepting the component manager
            # as argument and invoking the super-class initializer
            init = d.get('__init__')
            if not init:
                # Because we're replacing the initializer, we need to make sure
                # that any inherited initializers are also called.
                for init in [b.__init__._original for b in new_class.mro()
                             if issubclass(b, Component)
                             and '__init__' in b.__dict__]:
                    break
            def maybe_init(self, compmgr, init=init, cls=new_class):
                if cls not in compmgr.components:
                    compmgr.components[cls] = self
                    if init:
                        try:
                            init(self)
                        except:
                            del compmgr.components[cls]
                            raise
            maybe_init._original = init
            new_class.__init__ = maybe_init
        
        if d.get('abstract'):
            # Don't put abstract component classes in the registry
            return new_class
        
        ComponentMeta._components.append(new_class)
        registry = ComponentMeta._registry
        for interface in d.get('_implements', []):
            registry.setdefault(interface, []).append(new_class)
        for base in [base for base in bases if hasattr(base, '_implements')]:
            for interface in base._implements:
                registry.setdefault(interface, []).append(new_class)
                
        # add to package manager
        PackageManager._addClass(new_class)
        
        return new_class


class PackageManager(object):
    """Takes care of package registration."""
    
    # from seishub.packages.interfaces import IPackage
    
    _registry = {}
    
    @staticmethod
    def _addClass(cls):
        if not hasattr(cls, 'package_id'):
            return
        registry = PackageManager._registry
        registry.setdefault(cls.package_id, []).append(cls)
    
    @staticmethod
    def getClasses(interface, package_id = None):
        """get classes implementing interface within specified package"""
        registry = PackageManager._registry
        # get all classes that declare to implement interface
        classes = ComponentMeta._registry.get(interface, [])
        # filter for classes with correct package id
        if package_id:
            classes = [cls for cls in classes if cls in registry[package_id]]
        return classes
    
    @staticmethod
    def getComponents(interface, package_id, component):
        """get objects providing interface within specified package,
        if package_id is None, this is the same as a call to 
        seishub.core.ExtensionPoint(interface).extensions(component)
        """
        classes = PackageManager.getClasses(interface, package_id)
        # get, activate and return objects 
        return filter(None, [component.compmgr[cls] for cls in classes])
    
    @staticmethod
    def getPackageIds():
        """get a list of id's of all packages (enabled and disabled ones) 
        without activating any components"""
        return PackageManager._registry.keys()
    

class Component(object):
    """Base class for components.
    
    Every component can declare what extension points it provides, as well as
    what extension points of other components it extends.
    """
    __metaclass__ = ComponentMeta
    
    def __new__(cls, *args, **kwargs):
        """Return an existing instance of the component if it has already been
        activated, otherwise create a new instance.
        """
        # If this component is also the component manager, just invoke that
        if issubclass(cls, ComponentManager):
            self = super(Component, cls).__new__(cls)
            self.compmgr = self
            return self
        
        # The normal case where the component is not also the component manager
        try:
            compmgr = args[0]
        except IndexError:
            raise TypeError("Component takes a component manager instance " +\
                            "as first argument.")
        self = compmgr.components.get(cls)
        if self is None:
            self = super(Component, cls).__new__(cls)
            self.compmgr = compmgr
            compmgr.initComponent(self)
        return self


def implements(*interfaces):
    """Can be used in the class definition of `Component` subclasses to
    declare the extension points that are extended.
    """
    frame = sys._getframe(1)
    locals_ = frame.f_locals
    
    # Some sanity checks
    assert locals_ is not frame.f_globals and '__module__' in locals_, \
           'implements() can only be used in a class definition'
    
    locals_.setdefault('_implements', []).extend(interfaces)
    
    # zope.interfaces compatibility
    _implements("implements", interfaces, classImplements)


class ComponentManager(object):
    """The component manager keeps a pool of active components."""
    
    def __init__(self):
        """Initialize the component manager."""
        self.components = {}
        self.enabled = {}
        if isinstance(self, Component):
            self.components[self.__class__] = self
    
    def __contains__(self, cls):
        """Return if the given class is in the list of active components."""
        return cls in self.components
    
    def __getitem__(self, cls):
        """Activate the component instance for the given class, or return the
        existing the instance if the component has already been activated.
        """
        if cls not in self.enabled:
            self.enabled[cls] = self.isComponentEnabled(cls)
        if not self.enabled[cls]:
            return None
        component = self.components.get(cls)
        if not component:
            if cls not in ComponentMeta._components:
                raise SeisHubError('Component "%s" not registered' % 
                                   cls.__name__)
            try:
                component = cls(self)
            except TypeError, e:
                raise SeisHubError('Unable to instantiate component %r (%s)' %
                                (cls, e))
        return component
    
    def __delitem__(self,cls):
        del self.components[cls]
    
    def initComponent(self, component):
        """Can be overridden by sub-classes so that special initialization for
        components can be provided.
        """
    
    def isComponentEnabled(self, cls):
        """Can be overridden by sub-classes to veto the activation of a
        component.
        
        If this method returns False, the component with the given class will
        not be available.
        """
        return True