# -*- coding: utf-8 -*-
"""
Alias resources.
"""

from seishub.core.processor.resources.resource import Resource
from seishub.core.processor.resources.rest import RESTResource


class AliasResource(Resource):
    """
    Processor handler of a alias resource.
    """
    def __init__(self, expr, **kwargs):
        Resource.__init__(self, **kwargs)
        self.is_leaf = True
        self.folderish = True
        self.category = 'alias'
        self.expr = expr

    def getMetadata(self):
        return {'permissions': 040755}

    def render_GET(self, request):
        # get resources 
        res_dict = request.env.catalog.query(self.expr, full=False)
        temp = {}
        for id in res_dict['ordered']:
            res = res_dict[id]
            temp[res['resource_name']] = RESTResource(res)
        return temp
