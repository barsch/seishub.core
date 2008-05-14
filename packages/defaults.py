from sqlalchemy import MetaData, Table, Column, Integer, String, \
                       UniqueConstraint, ForeignKey, Text, Binary, \
                       PrimaryKeyConstraint, DateTime
                       
from seishub.db.dbmanager import meta as metadata

DEFAULT_PREFIX = 'default_'
SCHEMA_TABLE = 'schemas'
STYLESHEET_TABLE = 'stylesheets'

schema_tab = Table(DEFAULT_PREFIX + SCHEMA_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('uri', Text),
    Column('package_id', Text),
    Column('resourcetype_id', Text),
    Column('type', Text)
)

stylesheet_tab = Table(DEFAULT_PREFIX + STYLESHEET_TABLE, metadata,
    Column('id', Integer, primary_key = True, autoincrement = True),
    Column('uri', Text),
    Column('package_id', Text),
    Column('resourcetype_id', Text),
    Column('type', Text)
)