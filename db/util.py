# -*- coding: utf-8 -*-
"""
Database related utilities.
"""


from lxml.etree import Element, SubElement as Sub, tostring
from seishub.util.xmlwrapper import toString
from sqlalchemy import sql, Table
import datetime
import json


def compileStatement(stmt, bind=None, params={}, **kwargs):
    """
    Compiles a statement with inlines bindparams and additional arguments.

    WARNING: This doesn't do any escaping!
    
    @see L{http://www.sqlalchemy.org/trac/wiki/DebugInlineParams}
    """
    if not bind:
        bind = stmt.bind
    compiler = bind.dialect.statement_compiler(bind.dialect, stmt)
    compiler.bindtemplate = "[[[%(name)s]]]"
    compiler.compile()
    d = compiler.params
    d.update(params)
    d.update(kwargs)
    s = compiler.string
    for id, value in d.iteritems():
        s = s.replace('[[[' + id + ']]]', repr(value))
    # this omits an annoying warning
    if bind.engine.name == 'postgres':
        s = s.replace('%%', '%')
    return s


def querySingleColumn(request, table, column, **kwargs):
    """
    """
    tab = Table(table, request.env.db.metadata, autoload=True)
    # fetch arguments
    order = request.args0.get('order', 'ASC').upper()
    if order == 'ASC':
        order_by = [sql.asc(tab.c[column])]
    else:
        order_by = [sql.desc(tab.c[column])]
    try:
        limit = int(request.args0.get('limit'))
        offset = int(request.args0.get('offset', 0))
    except:
        limit = None
        offset = 0
    oncl = sql.and_(1 == 1)
    if kwargs:
        for key, value in kwargs.iteritems():
            if value:
                oncl = sql.and_(oncl, tab.c[key] == value)
    # build up query
    query = sql.select([tab.c[column].distinct()], oncl, limit=limit,
                       offset=offset, order_by=order_by)
    # execute query
    try:
        results = request.env.db.query(query)
    except:
        results = []
    # format results
    if not limit:
        return formatResults(request, results)
    # ok count all distinct values
    query = sql.select([sql.func.count(tab.c[column].distinct())])
    # execute query
    try:
        count = request.env.db.query(query).fetchone()[0]
    except:
        count = 0
    return formatResults(request, results, limit=limit, offset=offset,
                         count=count)


class DateTimeAwareJSONEncoder(json.JSONEncoder):
    """ 
    """
    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, datetime.time):
            return obj.strftime('%H:%M:%S')
        elif isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%dT%H:%M:%SZ')
        elif isinstance (obj, datetime.timedelta):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)


def formatResults(request, results, count=None, limit=None, offset=0):
    """
    Fetches results from database and creates either a XML resource or a JSON 
    document. It also takes care of limit and offset requests.
    """
    # create stats
    stats = {}
    stats['firstResultPosition'] = offset
    if isinstance(results, list):
        stats['totalResultsReturned'] = len(results)
    else:
        try:
            stats['totalResultsReturned'] = results.rowcount
        except:
            stats['totalResultsReturned'] = len([r for r in results])
    if count:
        stats['totalResultsAvailable'] = count
    else:
        stats['totalResultsAvailable'] = stats['totalResultsReturned']
    # get format
    formats = request.args.get('format', []) or request.args.get('output', [])
    if 'json' in formats:
        # build up JSON string
        data = stats
        data['Result'] = [dict(r) for r in results]
        # generate correct header
        request.setHeader('content-type', 'application/json; charset=UTF-8')
        # create output
        return json.dumps({'ResultSet': data},
                          cls=DateTimeAwareJSONEncoder, indent=4)
    elif 'xhtml' in formats:
        # build up a XHTML table
        xml = Element("table", border="1")
        s = Sub(xml, "tr")
        for key in results.keys:
            Sub(s, "th").text = str(key)
        for result in results:
            s = Sub(xml, "tr")
            for value in result:
                if value == None:
                    value = ''
                Sub(s, "td").text = str(value)
        # generate correct header
        request.setHeader('content-type', 'text/html; charset=UTF-8')
        return tostring(xml, method='html', encoding='utf-8')
    else:
        # build up XML document
        for key, value in stats.iteritems():
            stats[key] = str(value)
        xml = Element("ResultSet", **stats)
        for result in results:
            s = Sub(xml, "Item")
            for (key, value) in dict(result).iteritems():
                if value == None:
                    value = ''
                Sub(s, key).text = str(value)
        return toString(xml)
