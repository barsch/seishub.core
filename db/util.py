# -*- coding: utf-8 -*-
"""
Database related utilities.
"""

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
        s=s.replace('[[['+id+']]]',  repr(value))
    # this omits an annoying warning
    if bind.engine.name=='postgres':
        s=s.replace('%%','%')
    return s
