# -*- coding: utf-8 -*-

from sqlalchemy import MetaData, Table, Column, Integer, String, \
                       UniqueConstraint, ForeignKey

DEFAULT_PREFIX = 'default_'
RESOURCE_TABLE = 'data'
INDEX_TABLE = 'index'
INDEX_DEF_TABLE = 'index_def'
#METADATA_TABLE = 'meta'
#METADATA_INDEX_TABLE = 'meta_idx'
URI_TABLE = 'uri'

# xmldbms tables:
metadata = MetaData()
resource_tab = Table(DEFAULT_PREFIX + RESOURCE_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('data', String),
)

uri_tab = Table(DEFAULT_PREFIX + URI_TABLE, metadata,
    Column('uri', String, primary_key = True),
    Column('res_id', Integer, ForeignKey(DEFAULT_PREFIX + RESOURCE_TABLE +
                                         '.id')),
    Column('res_type', String),
)

# xmlindexcatalog tables:
index_def_tab = Table(DEFAULT_PREFIX + INDEX_DEF_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('key_path', String),
    Column('value_path', String),
    Column('data_type', String(20)),
    UniqueConstraint('key_path', 'value_path')
)

index_tab = Table(DEFAULT_PREFIX + INDEX_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('index_id', Integer, ForeignKey(DEFAULT_PREFIX + INDEX_DEF_TABLE +
                                           '.id')),
    Column('key', String),
    Column('value', String),
)
