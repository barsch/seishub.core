# -*- coding: utf-8 -*-

from datetime import datetime
from seishub.db import DEFAULT_PREFIX
from seishub.db.manager import meta as metadata
from sqlalchemy import Integer, String, Text, Unicode, DateTime, Boolean, Float, \
    Numeric, Table, Column, UniqueConstraint
from sqlalchemy.sql import text


DOCUMENT_TABLE = 'document'
DOCUMENT_META_TABLE = 'document_meta'
INDEX_TABLE = 'index'
INDEX_DEF_TABLE = 'index_def'
METADATA_TABLE = 'meta'
METADATA_DEF_TABLE = 'meta_def'
RESOURCE_TABLE = 'resource'

#class MyFloat(TypeDecorator):
#    impl = Float
#    
#    def process_bind_param(self, value, dialect):
#        a = 1
#        return value
#        
##    def result_processor(self, dialect):
##        a = 1
##        import pdb;pdb.set_trace()
#        
#    def process_result_value(self, value, dialect):
#        a = 1
#        import pdb;pdb.set_trace()

# xmldbms tables:

def revision_default(ctx):
    resource_id = ctx.compiled_parameters[0]['resource_id'] 
    q = text('SELECT coalesce(max(revision), 0) + 1 FROM '+\
             DEFAULT_PREFIX + DOCUMENT_TABLE + ' WHERE resource_id = %s' %\
             resource_id)
    return ctx.connection.scalar(q)

document_tab = Table(DEFAULT_PREFIX + DOCUMENT_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('resource_id', Integer),
    Column('revision', Integer, autoincrement = True, 
           default = revision_default),
    Column('data', Unicode),
    UniqueConstraint('resource_id', 'revision'),
    useexisting = True,
    )

document_meta_tab = Table(DEFAULT_PREFIX + DOCUMENT_META_TABLE, metadata,
    Column('id', Integer, primary_key = True), 
    Column('size', Integer),
    Column('datetime', DateTime, default = datetime.now, 
           onupdate = datetime.now),
    Column('uid', Integer),
    Column('hash', String(56)),
    useexisting = True,
    )

# XXX: sqlite does not support autoincrement on combined primary keys
# default does not work on Text columns, that's why String is used for name col 
resource_tab = Table(DEFAULT_PREFIX + RESOURCE_TABLE, metadata,
    Column('id', Integer, autoincrement = True, primary_key = True,
           default = text('(SELECT coalesce(max(id), 0) + 1 FROM '+\
                          DEFAULT_PREFIX + RESOURCE_TABLE +')')),
    Column('resourcetype_id', Integer),
    Column('name', String(255), 
           default = text('(SELECT coalesce(max(id), 0) + 1 FROM '+\
                          DEFAULT_PREFIX + RESOURCE_TABLE +')')
           ),
    UniqueConstraint('resourcetype_id', 'name'),
    useexisting=True,
    )

resource_meta_def_tab = Table(DEFAULT_PREFIX + METADATA_DEF_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('name', Text),
    Column('type', Text),
    # Column('maxcount', Integer),
    useexisting=True,
    )

resource_meta_tab = Table(DEFAULT_PREFIX + METADATA_TABLE, metadata,
    Column('resource_id', Integer),
    Column('metadata_id', Integer),
    Column('value', Text),
    useexisting=True,
    )

# xmlindexcatalog tables:
index_def_tab = Table(DEFAULT_PREFIX + INDEX_DEF_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('resourcetype_id', Integer),
    Column('xpath', Text),
    Column('type', Integer),
    Column('options', Text),
    UniqueConstraint('resourcetype_id', 'xpath'),
    useexisting=True,
)

# the following tables correspond to the different possible index types
index_text_tab = Table(DEFAULT_PREFIX + 'text_' + INDEX_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('index_id', Integer),
    Column('keyval', Unicode),
    Column('document_id', Integer),
    UniqueConstraint('index_id','keyval','document_id'),
    useexisting=True
)

index_numeric_tab = Table(DEFAULT_PREFIX + 'numeric_'+ INDEX_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('index_id', Integer),
    # Column('key', Numeric(precision = 23, scale = 9, asdecimal = True)),
    Column('keyval', Numeric(precision = 53, scale = 11)),
    # Column('key', Float(precision = 53)),
    # Column('key', Numeric),
    Column('document_id', Integer),
    UniqueConstraint('index_id','keyval','document_id'),
    useexisting=True
)

index_float_tab = Table(DEFAULT_PREFIX + 'float_'+ INDEX_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('index_id', Integer),
    Column('keyval', Float(precision = 52, asdecimal = False)),
    Column('document_id', Integer),
    UniqueConstraint('index_id','keyval','document_id'),
    useexisting=True
)

index_datetime_tab = Table(DEFAULT_PREFIX + 'datetime_'+ INDEX_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('index_id', Integer),
    Column('keyval', DateTime),
    Column('document_id', Integer),
    UniqueConstraint('index_id','keyval','document_id'),
    useexisting=True
)

index_boolean_tab = Table(DEFAULT_PREFIX + 'boolean_'+ INDEX_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('index_id', Integer),
    Column('keyval', Boolean),
    Column('document_id', Integer),
    UniqueConstraint('index_id','keyval','document_id'),
    useexisting=True
)

index_keyless_tab = Table(DEFAULT_PREFIX + 'keyless_'+ INDEX_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('index_id', Integer),
    Column('document_id', Integer),
    UniqueConstraint('index_id','document_id'),
    useexisting=True
)