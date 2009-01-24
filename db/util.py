# -*- coding: utf-8 -*-


def compileStatement(stmt, bind=None, params={}, **kwargs):
    """
    Compiles a statement with inlines bindparams and additional arguments.

    WARNING: This doesn't do any escaping!
    
    @see L{http://www.sqlalchemy.org/trac/wiki/DebugInlineParams}
    """
    if not bind:
        bind = stmt.bind 
    compiler = bind.dialect.statement_compiler(bind.dialect, stmt)
    compiler.bindtemplate = "%%(%(name)s)s"
    compiler.compile()
    d = dict((k,repr(v)) for k,v in compiler.params.items())
    d.update(params)
    d.update(kwargs)
    return compiler.string % d
