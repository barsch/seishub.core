# -*- coding: utf-8 -*-

from seishub.core.core import implements
from seishub.core.exceptions import InvalidParameterError
from seishub.core.xmldb.interfaces import IXPathQuery
import pyparsing as pp


class RestrictedXPathQueryParser(object):
    """
    This class provides a parser for the restricted XPath query grammar.
    
    NameStartChar ::= ":" | [A-Z] | "_" | [a-z] | [#xC0-#xD6] | [#xD8-#xF6] | 
                      [#xF8-#x2FF] | [#x370-#x37D] | [#x37F-#x1FFF] | 
                      [#x200C-#x200D] | [#x2070-#x218F] | [#x2C00-#x2FEF] | 
                      [#x3001-#xD7FF] | [#xF900-#xFDCF] | [#xFDF0-#xFFFD] | 
                      [#x10000-#xEFFFF]
    NameChar ::= NameStartChar | "-" | "." | [0-9] | #xB7 | [#x0300-#x036F] | 
                [#x203F-#x2040]
    this is taken from the XML 1.0 specification, 
    see: L{http://www.w3.org/TR/REC-xml/#NT-Name}

    wildcard     ::= '*'
    sep          ::= '/'
    selfNd       ::= '.'
    parentNd     ::= '..'
    lpar         ::= '('
    rpar         ::= '('
    pstart       ::= '['
    pend         ::= ']'
    nodename     ::= [@][NameStartChar[NameChar]*][:]NameStartChar[NameChar]*
    label        ::= NameStartChar[NameChar]
    node         ::= wildcard | parentNd | selfNd | nodename
    literalValue ::= '"'[^"]*'"' | '''[^']*'''
    numericValue ::= [-][0-9]*[.][0-9]*
    
    eqOp         ::= '==' | '=' 
    ltOp         ::= '<'
    gtOp         ::= '>'
    leOp         ::= '<='
    geOp         ::= '>='
    ineqOp       ::= '!='
    orOp         ::= 'or'
    andOp        ::= 'and'
    relOp        ::= eqOp | ineqOp | leOp | geOp | ltOp | gtOp
    logOp        ::= orOp | andOp
    
    package_id       ::= [A-Za-z0-9]* | wildcard
    resourcetype_id  ::= [A-Za-z0-9]* | wildcard
    # rootnode         ::= [A-Za-z0-9]* | wildcard
    locationStep     ::= sep (nodename | wildcard) 
    location         ::= sep package_id sep resourcetype_id [loactionStep]*
    pathExpr         ::= [sep] node [sep node]*
    valueExpr        ::= literalValue | numericValue
    relExpr          ::= pathExpr [relOp valueExpr | pathExpr]
    parExpr          ::= lpar pexpr rpar
    
    notFunc          ::= not(pexpr)
    func             ::= notFunc
    
    pexpr            ::= (func | relExpr | parExpr) [logOp (pexpr | parExpr)]*
    predicates       ::= pstart pexpr pend
    query = location [predicates]
    """

    SEP = '/'
    PARENT = '..'
    WILDCARD = '*'

    _logical_ops = ['and', 'or']
    _relational_ops = ['=', '<', '>', '<=', '>=', '!=']

    def __init__(self):
        self.parser = self.createParser()
        self._init_parser()

    def _init_parser(self):
        self.package_id = None
        self.resourcetype_id = None
        self.location_steps = None
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

    def evalLocationSteps(self, s, loc, tokens):
        self.location_steps = tokens.asList()
        return tokens

    def remove_list(self, s, loc, tokens):
        if len(tokens) == 1:
            return tokens[0]

    def evalPath(self, s, loc, tokens):
        """
        add location path as a prefix to path tokens and join the rest
        of the path again.
        """
        if tokens[0] == self.SEP:
            # path is relative to root (package level)
            return [[tokens[1], tokens[2], self.SEP.join(tokens[3:])]]
        # count the number of '..' nodes at the beginning of the path and move 
        # the appropriate number of steps in path to the left
        steps = 0
        for t in tokens:
            if not t == self.PARENT:
                break
            steps += 1
        # steps = len(filter(lambda t: t == self.PARENT, tokens))
        ptokens = [self.package_id, self.resourcetype_id]
        ptokens.extend(self.location_steps)
        ptokens = ptokens[:len(ptokens) - steps]
        ptokens.extend(tokens[steps:])
        return [[ptokens[0], ptokens[1], self.SEP.join(ptokens[2:])]]

    def createParser(self):
        """This function returns a parser for the RestrictedXpathQuery grammar.
        """
        # xml standard tokens (see: http://www.w3.org/TR/REC-xml)
        xmlNameStartChar = pp.alphas + ":" + "_" + \
                           pp.srange("[\u00C0-\u00D6]") + \
                           pp.srange("[\u00D8-\u00F6]") + \
                           pp.srange("[\u00F8-\u02FF]") + \
                           pp.srange("[\u0370-\u037D]") + \
                           pp.srange("[\u037F-\u1FFF]") + \
                           pp.srange("[\u200C-\u200D]") + \
                           pp.srange("[\u2070-\u218F]") + \
                           pp.srange("[\u2C00-\u2FEF]") + \
                           pp.srange("[\u3001-\uD7FF]") + \
                           pp.srange("[\uF900-\uFDCF]") + \
                           pp.srange("[\uFDF0-\uFFFD]") + \
                           pp.srange("[\u10000-\uEFFFF]")
        xmlNameChar = xmlNameStartChar + "-" + "." + pp.nums + \
                      unichr(0xB7) + pp.srange("[\u0300-\u036F]") + \
                      pp.srange("[\u203F-\u2040]")
        # custom tokens
        wildcard = pp.Literal(self.WILDCARD)        # node wildcard operator
        sep = pp.Literal(self.SEP)                  # path separator
        selfNd = pp.Literal('.').suppress()         # current node
        parentNd = pp.Literal(self.PARENT)          # parent of current node
        lpar = pp.Literal('(').suppress()           # left parenthesis literal
        rpar = pp.Literal(')').suppress()           # right parenthesis literal
        pstart = pp.Literal('[').suppress()         # beginning of predicates 
        pend = pp.Literal(']').suppress()           # end of predicates
        ncPrefix = pp.Word(xmlNameStartChar, xmlNameChar) + ':' # namespace prefix
        # node name, may contain a namespace prefix and may start with '@' for 
        # attribute nodes
        ndName = pp.Combine(pp.Optional('@') + pp.Optional(ncPrefix) + \
                 pp.Word(xmlNameStartChar, xmlNameChar))
        node = wildcard | parentNd | selfNd | ndName # node
        literalValue = pp.Literal('"').suppress() + \
                           pp.CharsNotIn('"') + \
                       pp.Literal('"').suppress() \
                       | \
                       pp.Literal("'").suppress() + \
                           pp.CharsNotIn("'") + \
                       pp.Literal("'").suppress()   # literal value delimited
                                                    # by either "" or ''
        numericValue = pp.Combine(pp.Optional('-') + \
                                  pp.Word(pp.nums) + \
                                  pp.Optional('.' + pp.Word(pp.nums)))# Numbers

        # keywords
        orderBy = pp.CaselessKeyword('order by')
        asc = pp.CaselessKeyword('asc')
        desc = pp.CaselessKeyword('desc')
        limit = pp.CaselessKeyword('limit')
        offset = pp.CaselessKeyword('offset')

        # operators
        eqOp = pp.Literal('==').setParseAction(pp.replaceWith("=")) | \
               pp.Literal('=')
        ltOp = pp.Literal('<')
        gtOp = pp.Literal('>')
        leOp = pp.Literal('<=')
        geOp = pp.Literal('>=')
        ineqOp = pp.Literal('!=')
        orOp = pp.CaselessKeyword('or')
        andOp = pp.CaselessKeyword('and')
        relOp = eqOp | ineqOp | leOp | geOp | ltOp | gtOp
        logOp = orOp | andOp

        # functions
        notFunc = pp.CaselessKeyword('not')

        # location step
        package_id = (pp.Word(pp.alphanums + "-") | wildcard).\
                     setResultsName('package_id').\
                     setParseAction(self.evalPackage_id).suppress()
        resourcetype_id = (pp.Word(pp.alphanums + "-") | wildcard).\
                          setResultsName('resourcetype_id').\
                          setParseAction(self.evalResourcetype_id).suppress()

        locationStep = (sep.suppress() + (ndName | wildcard)).\
                       setResultsName('locationStep', True)
        location = (sep.suppress() + package_id + \
                   sep.suppress() + resourcetype_id + \
                   pp.ZeroOrMore(locationStep)).\
                   setParseAction(self.evalLocationSteps)

        # predicate expression
        pexpr = pp.Forward().setParseAction(self.remove_list)
        pathExpr = (pp.Optional(sep) + node + \
                    pp.ZeroOrMore(sep.suppress() + node)).\
                    setParseAction(self.evalPath)
        valueExpr = literalValue | numericValue
        relExpr = pathExpr + pp.Optional(relOp + (valueExpr | pathExpr))
        parExpr = pp.Group(lpar + pexpr + rpar)
        notExpr = pp.Group(notFunc + parExpr)
        pexpr << (notExpr | pp.Group(relExpr) | parExpr) + \
                 pp.Optional(logOp + (pp.Group(pexpr) | parExpr))

        # order by clause
        obItem = (pathExpr + pp.Optional(asc | desc, 'asc')).\
                 setResultsName('order_by', listAllMatches=True)
        orderByExpr = orderBy + pp.delimitedList(obItem, ',')

        # limit and offset
        limitExpr = limit + pp.Word(pp.nums).setResultsName('limit') + \
                    pp.Optional(',' + \
                                pp.Word(pp.nums).setResultsName('offset'))
        offsetExpr = offset + pp.Word(pp.nums).setResultsName('offset')

        # query
        predicates = (pstart + pexpr + pend).setResultsName('predicates')
        query = pp.StringStart() + \
                location + \
                pp.Optional(predicates) + \
                pp.Optional(orderByExpr) + \
                pp.Optional(limitExpr) + \
                pp.Optional(offsetExpr) + \
                pp.StringEnd()

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
        self._init_parser()
        try:
            return self.setAttributes(self.parser(expr))
        except pp.ParseException, e:
            msg = "Error parsing query: Unexpected or invalid token at " + \
                  "position %s: %s"
            raise InvalidParameterError(msg % (str(e.loc),
                                               str(e.markInputline())))

class XPathQuery(RestrictedXPathQueryParser):
    """
    XPath query complying with the restricted XPath query grammar.
    """

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
        location_path = [pkg, rt]
        if self.location_steps:
            location_path.extend(self.location_steps)
        return location_path

    def getPredicates(self):
        return self.predicates

    def getOrderBy(self):
        return self.order_by

    def getLimit(self):
        return self.limit

    def getOffset(self):
        return self.offset
