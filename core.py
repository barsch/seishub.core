# -*- coding: utf-8 -*-
from seishub.interfaces import IComponent

__all__ = ['Component','ComponentManager','SeisHubError']


class SeisHubError(Exception):
    """Exception base class for errors in SeisHub."""

    def __init__(self, message, title=None, show_traceback=False):
        Exception.__init__(self, message)
        self.message = message
        self.title = title
        self.show_traceback = show_traceback


class ComponentManager(object):
    """The component manager keeps a pool of active components."""

    def __init__(self):
        """Initialize the component manager."""
        self.components = {}
        self.enabled = {}
        if isinstance(self, Component):
            self.components[self.__class__] = self

    def __contains__(self, cls):
        """Return wether the given class is in the list of active components."""
        return cls in self.components

    def __getitem__(self, cls):
        """Activate the component instance for the given class, or return the
        existing the instance if the component has already been activated.
        """
        if self.enabled.has_key(cls):
            if not self.enabled[cls]:
                return None
        component = self.components.get(cls)
        if not component:
            if cls not in ComponentMeta._components:
                raise SeisHubError('Component "%s" not registered' % cls.__name__)
            try:
                component = cls(self)
            except TypeError, e:
                raise SeisHubError('Unable to instantiate component %r (%s)' %
                                (cls, e))
        return component

class ComponentMeta(type):
    """Meta class for components.
    
    Takes care of component and extension point registration.
    """
    _components = []

    def __new__(cls, name, bases, d):
        """Create the component class."""

        new_class = type.__new__(cls, name, bases, d)
        
        if name == 'Component':
            # Don't put the Component base class in the registry
            return new_class
        
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

        ComponentMeta._components.append(new_class)
        
        return new_class



class Component(object):
    __metaclass__= ComponentMeta
    
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
        compmgr = args[0]
        self = compmgr.components.get(cls)
        if self is None:
            self = super(Component, cls).__new__(cls)
            self.compmgr = compmgr
            compmgr.component_activated(self)
        return self
