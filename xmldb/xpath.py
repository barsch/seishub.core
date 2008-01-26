# -*- coding: utf-8 -*-

"""For xml resource indexing purposes there's some restrictions made to xpath
expressions. In particular node selection is restricted to the root node.
Restricted expressions are of the following form: 
/rootnode[prediactes]
 - starts with / (absolute path)
 - has only one single location step followed by at most one block of predicates
 - node-test matches rootnode
"""

from seishub.core import SeisHubError

class RestrictedXpathError(SeisHubError):
    pass

# XXX: requires PyXML (_xmlplus.xpath)
# from xml import xpath
#class RestrictedXpathExpression(object):
#    axis=None
#    node_test=None
#    predicates=None
#    
#    def __init__(self,expr):
#        if self._parseXpathExpr(expr):
#            self._expr=expr
#        else:
#            self._expr=None
#            raise RestrictedXpathError("%s is not a valid restricted-xpath" + \
#                                       " expression." % expr)
#            
#    def _parseXpathExpr(self,expr):        
#        p=xpath.Compile(expr)
#        try:
#            self.axis=p._child._axis
#            self.node_test=p._child._nodeTest
#            self.predicates=p._child._predicates
#        except AttributeError:
#            return False
#        
#        return True

# or do the same via regexp:
import re

class RestrictedXpathExpression(object):
    __r_node_test="^/[^/\[\]]+"
    __r_predicates="(\[.*\])?\Z"
    
    node_test=None
    predicates=None
    
    def __init__(self,expr):
        if self._parseXpathExpr(expr):
            self._expr=expr
        else:
            raise RestrictedXpathError("Invalid restricted-xpath expression.")
            
    def _parseXpathExpr(self,expr):
        re_nt=re.compile(self.__r_node_test)
        re_pre=re.compile(self.__r_predicates)
        
        m=re_nt.match(expr)
        if m:
            # extract node test and remove leading slash:
            self.node_test=m.string[m.start()+1:m.end()]
        else:
            return False
        m=re_pre.match(expr,m.end())
        if m:
            # extract predicates and remove brackets:
            self.predicates=m.string[m.start()+1:m.end()-1]
        else:
            return False
        
        return True




