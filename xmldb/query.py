# -*- coding: utf-8 -*-


class QueryNode(object):
    def __init__(self, left, right, op):
        self.left = left
        self.right = right
        self.op = op
        
class IndexQuery(object):
    def __init__(self, package_id, resourcetype_id):
        pass