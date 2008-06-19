from sqlalchemy import Table, Column, UniqueConstraint  #@UnresolvedImport 
from sqlalchemy import Integer, Text #@UnresolvedImport 
                       
from seishub.db.dbmanager import meta as metadata

DEFAULT_PREFIX = 'default_'
SCHEMA_TABLE = 'schemas'
STYLESHEET_TABLE = 'stylesheets'
ALIAS_TABLE = 'aliases'

schema_tab = Table(DEFAULT_PREFIX + SCHEMA_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('uid', Text, nullable = False),
    Column('package_id', Text, nullable = False),
    Column('resourcetype_id', Text),
    Column('type', Text),
    UniqueConstraint('package_id', 'resourcetype_id', 'type')
)

stylesheet_tab = Table(DEFAULT_PREFIX + STYLESHEET_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('uid', Text, nullable = False),
    Column('package_id', Text, nullable = False),
    Column('resourcetype_id', Text),
    Column('type', Text),
    UniqueConstraint('package_id', 'resourcetype_id', 'type')
)

alias_tab = Table(DEFAULT_PREFIX + ALIAS_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('package_id', Text, nullable = False),
    Column('resourcetype_id', Text),
    Column('name', Text, nullable = False),
    Column('expr', Text, nullable = False),
    UniqueConstraint('package_id', 'resourcetype_id', 'name')
)