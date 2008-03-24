# -*- coding: utf-8 -*-
from zope.interface import implements

from seishub.xmldb.errors import RestrictedXpathError
from seishub.xmldb.interfaces import IXPathQuery, IXPathExpression

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
    """For xml index querying purposes there are some restrictions made to xpath
    expressions. In particular node selection is restricted to the root node.
    Restricted expressions are of the following form: 
    /rootnode[prediactes]
     - starts with / (absolute path)
     - has only one single location step followed by at most one block of predicates
     - first node-test matches rootnode
     - (only axes allowed are default axis (child) and attribute (@))
    """
    __r_node_test="""^/    # leading slash
    [^/\[\]]+              # all, but no /, [, ]
    """
    __r_predicates="""(\[  # [
    [^\[\]\(\)]*               # all but no [, ], (, )
    \])?                   # ]
    \Z
    """
    implements(IXPathExpression)
    
    node_test=None
    predicates=None
    
    def __init__(self,expr):
        if not isinstance(expr,basestring):
            raise TypeError("String expected")
        if self._parseXpathExpr(expr):
            self._expr=expr
        else:
            raise RestrictedXpathError("Invalid restricted-xpath expression.")
            
    def _parseXpathExpr(self,expr):
        re_nt=re.compile(self.__r_node_test, re.VERBOSE)
        re_pre=re.compile(self.__r_predicates, re.VERBOSE)
        
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

class IndexDefiningXpathExpression(object):
    """XPath expression defining an XmlIndex.
    IndexDefiningXpathExpressions mustn't contain any predicate blocks,
    but are of the form:
    "/resource_type/childnode1/childnode2/.../@attribute"
    """
    implements(IXPathExpression)
    
    __r_value_path = "^/[^/\[\]]+"
    __r_key_path = "[^\[\]]*\Z"
    
    value_path = None
    key_path = None
    
    def __init__(self,expr):
        if not isinstance(expr,basestring):
            raise TypeError("String expected")
        if self._parseXpathExpr(expr):
            self._expr=expr
        else:
            raise RestrictedXpathError("Invalid xpath expression: %s" % expr)
            
    def _parseXpathExpr(self,expr):
        re_vp=re.compile(self.__r_value_path)
        re_kp=re.compile(self.__r_key_path)
        
        m=re_vp.match(expr)
        if m:
            # extract value path and remove leading slash:
            self.value_path = m.string[m.start() + 1 : m.end()]
        else:
            return False
        m=re_kp.match(expr, m.end())
        if m:
            # extract key path and remove leading slash:
            self.key_path = m.string[m.start() + 1 : m.end()]
        else:
            return False
        
        return True
    
class PredicateExpression(object):
    """Representation of a parsed XPath predicates node."""
    
    # logical operators
    _logOp = r"""
    (?P<left>                # left operand
      .*?
    )
    (?P<op>                  # operators
        (?<=\s)\band\b(?=\s) | # and 
        (?<=\s)\bor\b(?=\s)    # or
    )                                                 
    (?P<right>               # right operand
      .*
    )
    """
    _logOpExpr = re.compile(_logOp, re.VERBOSE)
    
    # relational operators
    _relOp = r"""
    (?P<left>                            # left operand
      .*?
    )
    (?P<op> 
        = | <(?!=) | >(?!=) |            # operators =, <, >
        <= | >= | !=                     # <=, >=, !=
    )
    (?P<right>                           # right operand
      .*
    )
    """
    _relOpExpr = re.compile(_relOp, re.VERBOSE)
    
    # operator expression precedence is handled by _patterns
    # first expression is evaluated first
    _patterns = (_logOpExpr,_relOpExpr)
    
    _left = _right = _op = ""
    
    def __init__(self, predicates):
        self._parse(predicates, self._patterns)
        
    def __str__(self):
        left = op = right = ""
        if self._left:
            left = str(self._left)
        if self._op:
            op = " " + str(self._op) + " "
        if self._right:
            right = str(self._right)
        return left + op + right
    
    def __getitem__(self, key):
        return self.getOperation()[key]
    
#    def __iter__(self):
#        return self._get_nodes(self)
#    
#    @staticmethod
#    def _get_nodes(node):
##        print node
##        print node.__class__
#        if node and not isinstance(node,basestring):
#            for x in PredicateExpression._get_nodes(node._left):
#                yield x
#            yield node
#            if hasattr(node,'_right'):
#                for x in PredicateExpression._get_nodes(node._right):
#                    yield x

    def _str_expr(self,expr):
        expr = expr.strip()
        # remove string delimiter 
        if expr.startswith("\"") or expr.startswith("'"):
            expr = expr[1:len(expr)-1]
        # remove leading ./
        if expr.startswith("./"):
            expr = expr[2:]
        return expr            
        
    def _parse(self,expr,patterns):
        for pattern in patterns:
            m = pattern.search(expr)
            if m: 
                self._left = PredicateExpression(m.group('left'))
                self._right = PredicateExpression(m.group('right'))
                self._op = m.group('op')
                return

        self._left = self._str_expr(expr)
        
    def getOperation(self):
        return {'left': self._left,
                'op': self._op,
                'right': self._right}
    
    def getOperator(self):
        return self._op

class XPathQuery(RestrictedXpathExpression):
    """Query types supported by now:
     - single key queries: /rootnode[.../key1 = value1]
     - multi key queries with logical operators ('and', 'or')
       but no nested logical operations like ( ... and ( ... or ...))
     - relational operators: =, !=, <, >, <=, >=
     
    Queries may have a order by clause, which is a list of the following form:
    order_by = [["1st order-by expression","asc"|"desc"],
                ["2nd order-by expression","asc"|"desc"],
                ... ]
    where 'order-by expression' is an index defining xpath expression, note that
    one can order by nodes only, one has registered an index for.
    
    Size of resultsets may be limited via 'limit = ... ' 
    """
    implements(IXPathQuery)
    
    def __init__(self,query,order_by=None,limit=None):
        self.order_by = list()
        if order_by:
            order_by = list(order_by)
            for ob in order_by:
                if not isinstance(ob[0],basestring) \
                   or not isinstance(ob[1],basestring):
                    raise TypeError("Invalid order_by clause, string expected.")
                self.order_by.append([IndexDefiningXpathExpression(ob[0]),
                                      ob[1]])
        if limit:
            try:
                limit = int(limit)
            except:
                raise TypeError("Invalid limit, Integer expected.")
        self.limit = limit
        
        super(XPathQuery, self).__init__(query)        
        self.parsed_predicates = self._parsePredicates(self.predicates)

    def __str__(self):
        return "/" + self.node_test + "[%s]" % str(self.parsed_predicates)
        
    def _parsePredicates(self, predicates):
        if len(predicates) > 0:
            return PredicateExpression(predicates)
        return None
    
    # methods from IXPathQuery    
    def getValue_path(self):
        """@see: L{seishub.xmldb.interfaces.IXPathQuery}"""
        return self.node_test
    
    def getPredicates(self):
        """@see: L{seishub.xmldb.interfaces.IXPathQuery}"""
        return self.parsed_predicates
    
    def has_predicates(self):
        """@see: L{seishub.xmldb.interfaces.IXPathQuery}"""
        return self.parsed_predicates != None
    
    def getOrder_by(self):
        """@see: L{seishub.xmldb.interfaces.IXPathQuery}"""
        return self.order_by
    
    def getLimit(self):
        """@see: L{seishub.xmldb.interfaces.IXPathQuery}"""
        return self.limit