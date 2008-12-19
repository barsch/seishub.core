# -*- coding: utf-8 -*-
from zope.interface import implements
import re

from seishub.util import pyparsing as pp
from seishub.exceptions import InvalidParameterError
from seishub.xmldb.interfaces import IXPathQuery, IXPathExpression



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
            raise InvalidParameterError("Invalid restricted-xpath expression.")
            
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
    "/package_id/resource_type_id/rootnode/childnode1/childnode2/.../@attribute"
    """
    implements(IXPathExpression)
    
    __r_value_path = "^/[^/\[\]]+/[^/\[\]]+/[^/\[\]]+"
    __r_key_path = "[^\[\]]*\Z"
    
    value_path = None
    key_path = None
    
    def __init__(self, expr):
        if not isinstance(expr, basestring):
            raise TypeError("Invalid expression; string expected: %s" % expr)
        if self._parseXpathExpr(expr):
            self._expr = expr
        else:
            raise InvalidParameterError("Invalid xpath expression: %s" % expr)
            
    def _parseXpathExpr(self,expr):
        re_vp = re.compile(self.__r_value_path)
        re_kp = re.compile(self.__r_key_path)
        
        m=re_vp.match(expr)
        if m:
            # extract value path and remove leading slash:
            self.value_path = m.string[m.start() + 1 : m.end()]
        else:
            return False
        m = re_kp.match(expr, m.end())
        if m and m.start() < m.end():
            # extract key path and remove leading slash:
            self.key_path = m.string[m.start() + 1 : m.end()]
        else:
            return False
        
        return True
    
    
class PredicateExpression(object):
    """Representation of a parsed XPath predicates node."""
    
    _logical_ops = ['and', 'or']
    _relational_ops = ['=', '<', '>', '<=', '>=', '!=']
    
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
    
    def __init__(self, predicates = ""):
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

    def _str_expr(self,expr):
        expr = expr.strip()
        # remove string delimiter 
        if expr.startswith("\"") or expr.startswith("'"):
            expr = expr[1:len(expr)-1]
        # remove leading ./
        if expr.startswith("./"):
            expr = expr[2:]
        return expr            
        
    def _parse(self, expr, patterns):
        for pattern in patterns:
            m = pattern.search(expr)
            if m:
                self._op = m.group('op')
                self._left = PredicateExpression(m.group('left'))
                self._right = PredicateExpression(m.group('right'))
                return
        self._left = self._str_expr(expr)
        
    def applyOperator(self, left, right):
        # create sqlalchemy clauses from string operators
        if self._op == '==' or self._op == '=':
            return left == right
        elif self._op == '!=':
            return left != right
        elif self._op == '<':
            return left < right
        elif self._op == '>':
            return left > right
        elif self._op == '<=':
            return left <= right
        elif self._op == '>=':
            return left >= right
        raise InvalidParameterError("Operator '%s' not specified." % self._op)
        
    def getOperation(self):
        return {'left': self._left,
                'op': self._op,
                'right': self._right}
    
    def getOperator(self):
        return self._op
    
#    def getLeftLocationPath(self):
#        return self.location_path

class RestrictedXPathQueryParser(object):
    """RestrictedXPath queries have to cope with the following grammar:
    
     - A query consists of a mandatory location step, followed by an optional 
       predicate expression.
    
     - Location step:
        - starts with '/'
        - the leading '/' is followed by an alphanumeric package_id or 
          the wildcard operator '*'
        - package_id is followed by a '/', followed by an alphanumeric 
          resourcetype_id or the wildcard operator '*'
        - resourcetype_id is followed by a '/', followed by the alphanumeric 
          XML root node name or the wildcard operator '*'
     - Predicates:
        - starts with a '['
        - 
        - ends with a ']'
        
    """
    
    SEP = '/'
    PARENT = '..'
    
    rxpq_grammar = None
    
    def evalPackage_id(self, s, loc, tokens):
        self.package_id = tokens[0]
        
    def evalResourcetype_id(self, s, loc, tokens):
        self.resourcetype_id = tokens[0]
        
    def evalRootnode(self, s, loc, tokens):
        self.rootnode = tokens[0]
    
    def evalPath(self, s, loc, tokens):
        """add location path as a prefix to path tokens"""
        if tokens[0] == self.SEP:
            # path is relative to root (package level)
            return [tokens[1], tokens[2], self.SEP.join(tokens[3:])]
        # path starts with ... 
        # steps = 3, '../../..' => package level
        # steps = 2, '../..'    => resourcetype level
        # steps = 1, '..'       => root node level
        steps = len(filter(lambda t: t == self.PARENT, tokens[0:3]))
        ptokens = [self.package_id, self.resourcetype_id, self.rootnode]
        ptokens = ptokens[:3-steps]
        ptokens.extend(tokens[steps:])
        return [ptokens[0], ptokens[1], '/'.join(ptokens[2:])]
    
    def createParser(self):
        """This function returns a parser for the RestrictedXpathQuery grammar.
        """
        if RestrictedXPathQueryParser.rxpq_grammar:
            return RestrictedXPathQueryParser.rxpq_grammar.parseString
        
        # symbols
        wildcard = pp.Literal('*')                  # node wildcard operator
        sep = pp.Literal(self.SEP)                  # path separator
        selfNd = (pp.Literal('.') + sep).suppress() # current node, 
                                                    # suppressed together with 
                                                    # following '/'
        parentNd = pp.Literal(self.PARENT)          # parent of current node
        lpar = pp.Literal('(').suppress()           # left parenthesis literal
        rpar = pp.Literal(')').suppress()           # right parenthesis literal
        pstart = pp.Literal('[').suppress()         # beginning of predicates 
        pend = pp.Literal(']').suppress()           # end of predicates
        nodename = pp.Word(pp.alphanums + '@',      # alphanumeric node name, 
                           pp.alphanums)            # may start with '@'
        node = nodename | parentNd | selfNd |\
               wildcard                             # node
        value = pp.Word(pp.alphanums)               # alphanumeric value
        
        # operators
        eqOp = pp.Literal('==') | pp.Literal('=') 
        ltOp = pp.Literal('<')
        gtOp = pp.Literal('>')
        leOp = pp.Literal('<=')
        geOp = pp.Literal('>=')
        ineqOp = pp.Literal('!=')
        orOp = pp.CaselessKeyword('or')
        andOp = pp.CaselessKeyword('and')
        notOp = pp.CaselessKeyword('not')
        relOp = eqOp | ineqOp | leOp | geOp | ltOp | gtOp
        logOp = orOp | andOp
        
        # location step
        package_id = (pp.Word(pp.alphanums) | wildcard).\
                     setParseAction(self.evalPackage_id).suppress()
        resourcetype_id = (pp.Word(pp.alphanums) | wildcard).\
                          setParseAction(self.evalResourcetype_id).suppress()
        rootnode = (pp.Word(pp.alphanums) | wildcard).\
                   setParseAction(self.evalRootnode).suppress()
        
        location = sep.suppress() + package_id +\
                   sep.suppress() + resourcetype_id +\
                   sep.suppress() + rootnode
        
        # predicate expression
        pexpr = pp.Forward()
        path = (pp.Optional(sep) + node +\
               pp.ZeroOrMore(pp.Optional(sep.suppress()) + node)).\
               setParseAction(self.evalPath)
        key = value | path
        pathExpr = pp.Group(path + pp.Optional(relOp + key))
        #with grouping of parenthesized expressions
        parExpr = pp.Group(lpar + pexpr + rpar)
        pexpr << pp.Optional(notOp) + (pathExpr | parExpr) +\
                 pp.ZeroOrMore(logOp + (pexpr | parExpr))
#        #without grouping:
#        pexpr << pp.Optional(lpar) + pp.Optional(notOp) + (pathExpr) +\
#                 pp.ZeroOrMore(logOp + pexpr) + pp.Optional(rpar)

        # query
        predicates = (pstart + pexpr + pend).setResultsName('predicates')
        query = location + pp.Optional(predicates, None)
        RestrictedXPathQueryParser.rxpq_grammar = query
        return query.parseString
    
    def parse(self, expr):
        return self.createParser()(expr)


class XPathQuery(RestrictedXpathExpression, RestrictedXPathQueryParser):
    """Query types supported by now:
     - single key queries: /packageid/resourcetype/rootnode[.../key1 = value1]
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
    
    __r_prefix = r"""^/       # leading slash
    (?P<pid>                  # package id
    [^/\[\]]+         
    )
    /
    (?P<rid>                  # resourcetype_id
    [^/\[\]]+
    )
    """
    
    def __init__(self, query, order_by = None, limit = None, offset = None):
        self.order_by = order_by or dict()
        self.limit = limit
        self.offset = offset
        
        # cut off package and resource type from query
        package, resourcetype, query = self._parsePrefix(query)
        self.package_id = package
        self.resourcetype_id = resourcetype
        RestrictedXpathExpression.__init__(self, query)
        self.parsed_predicates = self._parsePredicates(self.predicates)

    def __str__(self):
        return "/" + self.package_id + "/" + self.resourcetype_id + "/" +\
               self.node_test + "[%s]" % str(self.parsed_predicates)
    
    def _parsePrefix(self, expr):
        re_pf = re.compile(self.__r_prefix, re.VERBOSE)
        m = re_pf.match(expr)
        if not m:
            raise InvalidParameterError("Invalid query expression: %s" % expr)
        pid = self._convertWildcards(m.group('pid'))
        rid = self._convertWildcards(m.group('rid'))
        query = expr[m.end():] 
        return pid,rid,query
        
#    def _parsePredicates(self, predicates):
#        self.parse(predicates)
#        if len(predicates) > 0:
#            return PredicateExpression(predicates)
#        return None
    
    def _convertWildcards(self, expr):
        if expr == '*':
            return None
        return expr
    
    # methods from IXPathQuery    
#    def getValue_path(self):
#        """@see: L{seishub.xmldb.interfaces.IXPathQuery}"""
#        #XXX: maybe completely remove value path from indexes and replace by seperate
#        # packageid resourcetypeid fields; rootnode is needed as XXML Schema allows
#        # different rootnodes for different files
#        return str(self.package_id) + '/' + str(self.resourcetype_id) + '/' +\
#               self.node_test

    def getQueryBase(self):
        return (self.package_id, self.resourcetype_id, self.node_test)
    
    def getPredicates(self):
        """@see: L{seishub.xmldb.interfaces.IXPathQuery}"""
        return self.parsed_predicates
    
    def has_predicates(self):
        """@see: L{seishub.xmldb.interfaces.IXPathQuery}"""
        return self.parsed_predicates != None
    
    def getOrderBy(self):
        """@see: L{seishub.xmldb.interfaces.IXPathQuery}"""
        return self.order_by
    
    def getLimit(self):
        """@see: L{seishub.xmldb.interfaces.IXPathQuery}"""
        return self.limit
    
    def getOffset(self):
        """@see: L{seishub.xmldb.interfaces.IXPathQuery}"""
        return self.offset