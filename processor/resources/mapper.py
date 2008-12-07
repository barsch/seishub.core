# -*- coding: utf-8 -*-
"""
Mapper resources.
"""

from seishub.exceptions import NotImplementedError, SeisHubError
from seishub.processor.interfaces import IFolderish
from seishub.processor.resources.resource import Resource
from twisted.web import http


class MapperResource(Resource):
    """
    Processor handler of a mapping resource.
    """
    def __init__(self, mapper, folderish=True, category='mapping'):
        Resource.__init__(self)
        self.is_leaf = True
        self.mapper = mapper
        if IFolderish.providedBy(mapper):
            self.folderish = folderish
        else:
            self.folderish = False
        self.category = category
    
    def getMetadata(self):
        if self.folderish:
            # should be a directory
            return {'permissions': 040755}
        else:
            # we got some file
            return {'permissions': 0100644}
    
    def render_GET(self, request):
        func = getattr(self.mapper, 'process_GET')
        if not func:
            msg = "Method process_GET is not implemented."
            raise NotImplementedError(msg)
        result = func(request)
        # result must be either a string or a dictionary of categories and ids
        if isinstance(result, basestring):
            # basestring 
            return result
        elif isinstance(result, dict):
            # dictionary of categories and ids for this category
            temp = {}
            for category, ids in result.items():
                if category in ['folder']:
                    folderish = True
                else:
                    folderish = False
                for id in ids:
                    temp[id] = self._clone(folderish=folderish, 
                                           category=category)
            return temp
        msg = "A mapper must return a dictionary of categories and ids or " + \
              "a basestring for a resulting document."
        raise SeisHubError(msg, code=http.INTERNAL_SERVER_ERROR)
    
    def render_POST(self, request):
        func = getattr(self.mapper, 'process_POST')
        if not func:
            msg = "Method process_POST is not implemented."
            raise NotImplementedError(msg)
        func(request)
        request.code = http.NO_CONTENT
        return ''
    
    def render_DELETE(self, request):
        func = getattr(self.mapper, 'process_DELETE')
        if not func:
            msg = "Method process_DELETE is not implemented."
            raise NotImplementedError(msg)
        func(request)
        request.code = http.NO_CONTENT
        return ''
    
    def render_PUT(self, request):
        func = getattr(self.mapper, 'process_PUT')
        if not func:
            msg = "Method process_PUT is not implemented."
            raise NotImplementedError(msg)
        result = func(request)
        request.code = http.CREATED
        request.headers['Location'] = str(result)
        return ''
    
    def _clone(self, **kwargs):
        return self.__class__(self.mapper, **kwargs)
