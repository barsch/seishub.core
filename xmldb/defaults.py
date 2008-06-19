# -*- coding: utf-8 -*-

from sqlalchemy import Table, Column, ForeignKey  #@UnresolvedImport
from sqlalchemy import Integer, String, DateTime, Text, Binary #@UnresolvedImport
from sqlalchemy import UniqueConstraint, PrimaryKeyConstraint #@UnresolvedImport
                       
from seishub.db.dbmanager import meta as metadata
                       
DEFAULT_PREFIX = 'default_'
RESOURCE_TABLE = 'data'
RESOURCE_TYPE_TABLE = 'resource_types'
INDEX_TABLE = 'index'
INDEX_DEF_TABLE = 'index_def'
QUERY_ALIASES_TABLE = 'query_aliases'
METADATA_TABLE = 'meta'
RESOURCE_META_TABLE = 'resource_meta'
XSD_TABLE = 'xsd'
XSLT_TABLE = 'xslt'

# xmldbms tables:
resource_tab = Table(DEFAULT_PREFIX + RESOURCE_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('data', Binary),
    )

#resource_types_tab = Table(DEFAULT_PREFIX + RESOURCE_TYPE_TABLE, metadata,
#    Column('name', Text),
#    Column('type', Text),
#    Column('uri', Text, ForeignKey(DEFAULT_PREFIX + URI_TABLE +'.uri'),
#           primary_key = True),
#    )

# XXX: normalize package_id and resource_type columns
resource_meta_tab = Table(DEFAULT_PREFIX + RESOURCE_META_TABLE, metadata,
    Column('res_id', Integer, ForeignKey(DEFAULT_PREFIX + RESOURCE_TABLE +
                                         '.id')),
    Column('package_id', Text),
    Column('resourcetype_id', Text),
    Column('revision', Integer),
    PrimaryKeyConstraint('res_id')
    )

metadata_tab = Table(DEFAULT_PREFIX + METADATA_TABLE, metadata,
                Column('res_id', Integer, 
                       ForeignKey(DEFAULT_PREFIX + RESOURCE_TABLE + '.id')),
                Column('user', Text),
                Column('timestamp', DateTime)
                )

# xmlindexcatalog tables:
index_def_tab = Table(DEFAULT_PREFIX + INDEX_DEF_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
#    Column('package_id', Text),
#    Column('resourcetype_id', Text),
    Column('value_path', Text),
    Column('key_path', Text),
    Column('data_type', String(20)),
    UniqueConstraint('value_path','key_path')
)

index_tab = Table(DEFAULT_PREFIX + INDEX_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('index_id', Integer, ForeignKey(DEFAULT_PREFIX + INDEX_DEF_TABLE +
                                           '.id')),
    Column('key', Text),
    Column('value', Integer),
)

query_aliases_tab = Table(DEFAULT_PREFIX + QUERY_ALIASES_TABLE, metadata,
    Column('name', Text, primary_key = True),
    Column('expr', Text)
) 

## resourcetypes tables
#xsd_tab = Table(DEFAULT_PREFIX + XSD_TABLE, metadata,
#    Column('uri', Text, primary_key = True),
#    Column('package_id', Text)
#)
#
#xslt_tab = Table(DEFAULT_PREFIX + XSLT_TABLE, metadata,
#    Column('uri', Text, primary_key = True),
#    Column('package_id', Text),
#    Column('format', Text)
#)