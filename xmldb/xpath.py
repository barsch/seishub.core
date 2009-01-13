# -*- coding: utf-8 -*-
from zope.interface import implements
import re

from seishub.util import pyparsing as pp
from seishub.exceptions import InvalidParameterError
from seishub.xmldb.interfaces import IXPathQuery


class RestrictedXPathQueryParser(object):
    """This class provides a parser for the restricted XPath query grammar.
    
    wildcard     ::= '*'
    sep          ::= '/'
    selfNd       ::= '.'
    parentNd     ::= '..'
    lpar         ::= '('
    rpar         ::= '('
    pstart       ::= '['
    pend         ::= ']'
    nodename     ::= [@][A-Za-z0-9]*[:][A-Za-z0-9]*
    node         ::= wildcard | parentNd | selfNd | nodename
    literalValue ::= '"'[^"]*'"' | '''[^']*'''
    numericValue ::= [0-9]*[.][0-9]*
    
    eqOp         ::= '==' | '=' 
    ltOp         ::= '<'
    gtOp         ::= '>'
    leOp         ::= '<='
    geOp         ::= '>='
    ineqOp       ::= '!='
    orOp         ::= 'or'
    andOp        ::= 'and'
    notOp        ::= 'not'
    relOp        ::= eqOp | ineqOp | leOp | geOp | ltOp | gtOp
    logOp        ::= orOp | andOp
    
    package_id       ::= [A-Za-z0-9]* | wildcard
    resourcetype_id  ::= [A-Za-z0-9]* | wildcard
    rootnode         ::= [A-Za-z0-9]* | wildcard
    location         ::= sep package_id sep resourcetype_id sep rootnode
    pathExpr         ::= [sep] node [sep node]*
    valueExpr        ::= literalValue | numericValue
    relExpr          ::= pathExpr [relOp valueExpr | pathExpr]
    parExpr          ::= lpar pexpr rpar
    pexpr            ::= [notOp] (relExpr | parExpr) [logOp (pexpr | parExpr)]*
    predicates       ::= pstart pexpr pend
    query = location [predicates]
    """
    
    SEP = '/'
    PARENT = '..'
    WILDCARD = '*'
    
    _logical_ops = ['and', 'or']
    _relational_ops = ['=', '<', '>', '<=', '>=', '!=']
    
    _grammar = None
    
    def __init__(self):
        self.parser = self.createParser()
        self.package_id = None
        self.resourcetype_id = None
        self.rootnode = None
        self.predicates = None
        self.order_by = None
        self.limit = None
        self.offset = None
    
    def evalPackage_id(self, s, loc, tokens):
        self.package_id = tokens[0]
        return tokens
        
    def evalResourcetype_id(self, s, loc, tokens):
        self.resourcetype_id = tokens[0]
        return tokens
        
    def evalRootnode(self, s, loc, tokens):
        self.rootnode = tokens[0]
        return tokens
    
    def evalPath(self, s, loc, tokens):
        """add location path as a prefix to path tokens and join the rest
        of the path with again."""
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
        return [[ptokens[0], ptokens[1], self.SEP.join(ptokens[2:])]]
    
    def createParser(self):
        """This function returns a parser for the RestrictedXpathQuery grammar.
        """
#        if RestrictedXPathQueryParser._grammar:
#            self.setParseActions()
#            return RestrictedXPathQueryParser._grammar.parseString
        
#        # xml standard tokens (see: http://www.w3.org/TR/REC-xml)
#        xmlNameStartChar = pp.alphas | ":" | "_" |\
#                           pp.srange("[\0xC0-\0xD6]") |\
#                           pp.srange("[\0xD8-\0xF6]") |\
#                           pp.srange("[\0xF8-\0x2FF]") |\
#                           pp.srange("[\0x370-\0x37D]") |\
#                           pp.srange("[\0x37F-\0x1FFF]") |\
#                           pp.srange("[\0x200C-\0x200D]") |\
#                           pp.srange("[\0x2070-\0x218F]") |\
#                           pp.srange("[\0x2C00-\0x2FEF]") |\
#                           pp.srange("[\0x3001-\0xD7FF]") |\
#                           pp.srange("[\0xF900-\0xFDCF]") |\
#                           pp.srange("[\0xFDF0-\0xFFFD]") |\
#                           pp.srange("[\0x10000-\0xEFFFF]")
#        xmlNameChar = xmlNameStartChar | "-" | "." | pp.nums |\
#                      unichr('0xB7') | pp.srange("[\0x0300-\0x036F]") |\
#                      pp.srange("[\0x203F-\0x2040]")
#            
#        NCNameStartChar = Letter | '_' 
#        NCName = NCNameStartChar + pp.ZeroOrMore(NCNameChar)
#        xmlNameTest = '*' | NCName + ':' + '*' | QName

        # XXX: define a better character class for node names than alphanums
        # most ASCII characters should be allowed 
        # custom tokens
        wildcard = pp.Literal(self.WILDCARD)        # node wildcard operator
        sep = pp.Literal(self.SEP)                  # path separator
        selfNd = pp.Literal('.').suppress()         # current node
        parentNd = pp.Literal(self.PARENT)          # parent of current node
        lpar = pp.Literal('(').suppress()           # left parenthesis literal
        rpar = pp.Literal(')').suppress()           # right parenthesis literal
        pstart = pp.Literal('[').suppress()         # beginning of predicates 
        pend = pp.Literal(']').suppress()           # end of predicates
        ncPrefix = pp.Word(pp.alphanums) + ':'      # namespace prefix
        ndName = pp.Combine(pp.Optional('@') + pp.Optional(ncPrefix) +\
                   pp.Word(pp.alphanums + '_'))     # node name, may contain a
                                                    # namespace prefix and may 
                                                    # start with '@' for 
                                                    # attribute nodes
        node = wildcard | parentNd | selfNd | ndName # node
        literalValue = pp.Literal('"').suppress() +\
                           pp.CharsNotIn('"') +\
                       pp.Literal('"').suppress() \
                       | \
                       pp.Literal("'").suppress() +\
                           pp.CharsNotIn("'") +\
                       pp.Literal("'").suppress()   # literal value delimited
                                                    # by either "" or ''
        numericValue = pp.Combine(pp.Word(pp.nums) +\
                       pp.Optional('.' + pp.Word(pp.nums))) # Numbers
        
        # keywords
        orderBy = pp.CaselessKeyword('order by')
        asc = pp.CaselessKeyword('asc')
        desc = pp.CaselessKeyword('desc')
        limit = pp.CaselessKeyword('limit')
        
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
                     setResultsName('package_id').\
                     setParseAction(self.evalPackage_id).suppress()
        resourcetype_id = (pp.Word(pp.alphanums) | wildcard).\
                          setResultsName('resourcetype_id').\
                          setParseAction(self.evalResourcetype_id).suppress()
        rootnode = (ndName | wildcard).\
                   setResultsName('rootnode').\
                   setParseAction(self.evalRootnode).suppress()
        
        location = sep.suppress() + package_id +\
                   sep.suppress() + resourcetype_id +\
                   sep.suppress() + rootnode
        
        # predicate expression
        pexpr = pp.Forward()
        pathExpr = (pp.Optional(sep) + node +\
                    pp.ZeroOrMore(sep.suppress() + node)).\
                    setParseAction(self.evalPath)
        valueExpr = literalValue | numericValue
        relExpr = pp.Group(pathExpr +\
                           pp.Optional(relOp + (valueExpr | pathExpr)))
        # with grouping of parenthesized expressions
        parExpr = pp.Group(lpar + pexpr + rpar)
        pexpr << pp.Optional(notOp) + (relExpr | parExpr) +\
                 pp.ZeroOrMore(logOp + (pexpr | parExpr))
#        #without grouping:
#        pexpr << pp.Optional(lpar) + pp.Optional(notOp) + (relExpr) +\
#                 pp.ZeroOrMore(logOp + pexpr) + pp.Optional(rpar)

        # order by clause
        limitExpr = limit + pp.Word(pp.nums).setResultsName('limit') +\
                    pp.Optional(',' + pp.Word(pp.nums).\
                                setResultsName('offset'))
        obItem = (pathExpr + pp.Optional(asc | desc, 'asc')).\
                 setResultsName('order_by', listAllMatches = True)
        orderByExpr = orderBy + pp.delimitedList(obItem, ',') +\
                      pp.Optional(limitExpr)

        # query
        predicates = (pstart + pexpr + pend).setResultsName('predicates')
        query = pp.StringStart() +\
                location +\
                pp.Optional(predicates) +\
                pp.Optional(orderByExpr) +\
                pp.StringEnd()
        RestrictedXPathQueryParser._grammar = query
        return query.parseString
    
    def setAttributes(self, parsed):
        predicates = parsed.get('predicates')
        if isinstance(predicates, pp.ParseResults):
            self.predicates = predicates.asList()
        order_by = parsed.get('order_by')
        if isinstance(order_by, pp.ParseResults):
            self.order_by = order_by.asList()
        limit = parsed.get('limit')
        if isinstance(limit, basestring):
            self.limit = int(limit)
        offset = parsed.get('offset')
        if isinstance(offset, basestring):
            self.offset = int(offset)
        return parsed
    
    def parse(self, expr):
        try:
            return self.setAttributes(self.parser(expr))
        except pp.ParseException, e:
            msg = "Error parsing query: Unexpected or invalid token at position %s: %s"
            raise InvalidParameterError(msg % (str(e.loc), str(e.markInputline())))

class XPathQuery(RestrictedXPathQueryParser):
    """XPath query complying with the restricted XPath query grammar."""
    
    implements(IXPathQuery)
    
    def __init__(self, query):
        RestrictedXPathQueryParser.__init__(self)
        self.query = query
        self.parsed_query = self.parse(query)
        
    def getLocationPath(self):
        pkg = self.package_id
        if pkg == self.WILDCARD:
            pkg = None
        rt = self.resourcetype_id
        if rt == self.WILDCARD:
            rt = None
        rn = self.rootnode
        if rn == self.WILDCARD:
            rn = None
        return pkg, rt, rn
    
    def getPredicates(self):
        # TODO: sometimes there's an unneeded additional [ ] wrapped around predicates ?
        if self.predicates and len(self.predicates) == 1: 
            return self.predicates[0]
        return self.predicates
    
    def getOrderBy(self):
        return self.order_by
    
    def getLimit(self):
        return self.limit
    
    def getOffset(self):
        return self.offset


#class XPathQuery(RestrictedXpathExpression, RestrictedXPathQueryParser):
#    """- A query consists of a mandatory location step, followed by an optional 
#       predicate expression.
#    
#     - Location step:
#        - starts with '/'
#        - the leading '/' is followed by an alphanumeric package_id or 
#          the wildcard operator '*'
#        - package_id is followed by a '/', followed by an alphanumeric 
#          resourcetype_id or the wildcard operator '*'
#        - resourcetype_id is followed by a '/', followed by the alphanumeric 
#          XML root node name or the wildcard operator '*'
#     - Predicates:
#        - starts with a '['
#        - 
#        - ends with a ']'
#    
#    For further information on XPath see also: http://www.w3.org/TR/xpath
#    
#    Query types supported by now:
#     - single key queries: /packageid/resourcetype/rootnode[.../key1 = value1]
#     - multi key queries with logical operators ('and', 'or')
#       but no nested logical operations like ( ... and ( ... or ...))
#     - relational operators: =, !=, <, >, <=, >=
#     
#    Queries may have a order by clause, which is a list of the following form:
#    order_by = [["1st order-by expression","asc"|"desc"],
#                ["2nd order-by expression","asc"|"desc"],
#                ... ]
#    where 'order-by expression' is an index defining xpath expression, note that
#    one can order by nodes only, one has registered an index for.
#    
#    Size of resultsets may be limited via 'limit = ... ' 
#    """
#    implements(IXPathQuery)
#    
#    __r_prefix = r"""^/       # leading slash
#    (?P<pid>                  # package id
#    [^/\[\]]+         
#    )
#    /
#    (?P<rid>                  # resourcetype_id
#    [^/\[\]]+
#    )
#    """
