# -*- coding: utf-8 -*-

from seishub.exceptions import NotImplementedError, SeisHubError
from seishub.processor.resources.resource import Resource
from twisted.web import http


class MapperResource(Resource):
    """Processor handler of a mapping folder."""
    
    def __init__(self, mapper, folderish=True, category='mapping'):
        Resource.__init__(self)
        self.is_leaf = True
        self.mapper = mapper
        self.category = category
        self.folderish = folderish
    
    def render_GET(self, request):
        func = getattr(self.mapper, 'process_' + request.method)
        if not func:
            msg = "Method process_%s is not implemented." % (request.method)
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
        func = getattr(self.mapper, 'process_' + request.method)
        if not func:
            msg = "Method process_%s is not implemented." % (request.method)
            raise NotImplementedError(msg)
        func(request)
        request.response_code = http.NO_CONTENT
        return ''
    
    def render_DELETE(self, request):
        func = getattr(self.mapper, 'process_' + request.method)
        if not func:
            msg = "Method process_%s is not implemented." % (request.method)
            raise NotImplementedError(msg)
        func(request)
        request.response_code = http.NO_CONTENT
        return ''
    
    def render_PUT(self, request):
        func = getattr(self.mapper, 'process_' + request.method)
        if not func:
            msg = "Method process_%s is not implemented." % (request.method)
            raise NotImplementedError(msg)
        result = func(request)
        request.response_code = http.CREATED
        request.response_header['Location'] = str(result)
        return ''
    
    def _clone(self, **kwargs):
        return self.__class__(self.mapper, **kwargs)
