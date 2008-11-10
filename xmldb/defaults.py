# -*- coding: utf-8 -*-
from datetime import datetime
from sqlalchemy import Table, Column
from sqlalchemy import Integer, String, Text, Unicode, DateTime
from sqlalchemy import UniqueConstraint, PrimaryKeyConstraint
from sqlalchemy.sql import text, func, select

from seishub.db.dbmanager import meta as metadata

DEFAULT_PREFIX = 'default_'
DOCUMENT_TABLE = 'document'
DOCUMENT_META_TABLE = 'document_meta'
INDEX_TABLE = 'index'
INDEX_DEF_TABLE = 'index_def'
METADATA_TABLE = 'meta'
METADATA_DEF_TABLE = 'meta_def'
RESOURCE_TABLE = 'resource'

# xmldbms tables:

def revision_default(ctx):
    resource_id = ctx.compiled_parameters[0]['resource_id'] 
    q = text('SELECT coalesce(max(revision), 0) + 1 FROM '+\
             DEFAULT_PREFIX + DOCUMENT_TABLE + ' WHERE resource_id = %s' %\
             resource_id)
#    q = select([func.coalesce(func.max(document_tab.c.revision))],
#                document_tab.c.resource_id == resource_id)
    # import pdb;pdb.set_trace()
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
resource_tab = Table(DEFAULT_PREFIX + RESOURCE_TABLE, metadata,
    Column('id', Integer, autoincrement = True, primary_key = True,
           default = text('(SELECT coalesce(max(id), 0) + 1 FROM '+\
                          DEFAULT_PREFIX + RESOURCE_TABLE +')')),
#    Column('revision', Integer, autoincrement = True),
#    Column('resource_id', Integer, 
#            ForeignKey(DEFAULT_PREFIX + DOCUMENT_TABLE + '.id'),
#           ),
#    Column('package_id', Integer),
    Column('resourcetype_id', Integer),
    Column('name', String(255), 
           default = text('(SELECT coalesce(max(id), 0) + 1 FROM '+\
                          DEFAULT_PREFIX + RESOURCE_TABLE +')')
           ),
    UniqueConstraint(#'package_id', 
                     'resourcetype_id', 
                     'name'),
    #PrimaryKeyConstraint('id', 'revision'),
    useexisting=True,
    )

metadata_def_tab = Table(DEFAULT_PREFIX + METADATA_DEF_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('name', Text),
    Column('type', Text),
    useexisting=True,
    )

metadata_tab = Table(DEFAULT_PREFIX + METADATA_TABLE, metadata,
    Column('resource_id', Integer),
    Column('metadata_id', Integer),
    Column('value', Text),
    useexisting=True,
    )

# xmlindexcatalog tables:
index_def_tab = Table(DEFAULT_PREFIX + INDEX_DEF_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
#    Column('package_id', Text),
#    Column('resourcetype_id', Text),
    Column('value_path', Text),
    Column('key_path', Text),
    Column('data_type', String(20)),
    UniqueConstraint('value_path','key_path'),
    useexisting=True,
)

index_tab = Table(DEFAULT_PREFIX + INDEX_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('index_id', Integer),
    Column('key', Text),
    Column('value', Integer),
    UniqueConstraint('index_id','key','value'),
    useexisting=True
)