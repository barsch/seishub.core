# -*- coding: utf-8 -*-
"""
The root resource of the whole resource tree.
"""

from seishub.processor.resources import RESTFolder, MapperResource, \
    FileSystemResource, AdminRootFolder, StaticFolder, AliasResource
from seishub.util.path import splitPath
import os


class ResourceTree(StaticFolder):
    """
    The root node of the the complete resource tree.
    
    This resource should be instantiated only once. It will auto generate a
    resource tree with standard items like a REST, administrative and mapper
    resources. You may add children to this folder resource by using an 
    absolute path at the putChild method.
    """
    def __init__(self, env, **kwargs):
        StaticFolder.__init__(self, **kwargs)
        self.env = env
        self._registry = {}
        self.public = True

    def putChild(self, path, obj):
        """
        Register a static child to the root node.

        The root node also accepts absolute paths. Missing sub folders are
        automatically generated and added to the resource tree.
        """
        if '/' not in path:
            # we got a single id
            self.children[path] = obj
            self._registry['/' + path] = str(obj)
        else:
            # we got some absolute path
            parts = splitPath(path)
            temp = self
            for part in parts[:-1]:
                if part not in temp.children:
                    temp.children[part] = StaticFolder()
                temp = temp.children.get(part)
            temp.children[parts[-1]] = obj
            self._registry[path] = str(obj)

    def update(self):
        """
        Rebuilds the whole resource tree.

        This method should be called, if the status any included resource
        objects changes, e.g. a mapper gets disabled.
        """
        self.env.log.debug('Updating ResourceTree ...')
        self.children = {}
        self._registry = {}
        # set mappings
        for url, cls in self.env.registry.mappers.get().items():
            mapper_obj = cls(self.env)
            self.putChild(url, MapperResource(mapper_obj))
        # set all file system folder
        for url, path in self.env.config.options('fs'):
            if os.path.isdir(path):
                self.putChild(url, FileSystemResource(path))
            else:
                msg = "Can't open %s" % path
                self.env.log.warn(msg)
        # set all aliases
        for alias in self.env.registry.aliases.get():
            expr = alias.getExpr()
            uri = alias.getURI()
            self.putChild(uri, AliasResource(expr))
        # set Administration root folder
        res = AdminRootFolder(self.env, hidden=True)
        self.putChild('manage', res)
        # set XML resource root folder
        self.putChild('xml', RESTFolder())
        # set favicon.ico
        res = self.children['manage'].children['favicon.ico']
        self.putChild('favicon.ico', res)
        # set welcome page
        res = self.children['manage'].children['welcome']
        self.putChild('welcome', res)
        self.env.log.info('ResourceTree has been updated.')
        # set yui2 components
        res = self.children['manage'].children['yui2']
        res.hidden = True
        self.putChild('yui2', res)
