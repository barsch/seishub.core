# -*- coding: utf-8 -*-

from seishub.core.db import DEFAULT_PREFIX
from seishub.core.db.manager import meta as metadata
from sqlalchemy import Table, Column, ForeignKey, UniqueConstraint, Integer, \
    Text, Boolean


PACKAGES_TABLE = 'packages'
RESOURCETYPES_TABLE = 'resourcetypes'
SCHEMA_TABLE = 'schemas'
STYLESHEET_TABLE = 'stylesheets'
ALIAS_TABLE = 'aliases'


packages_tab = Table(DEFAULT_PREFIX + PACKAGES_TABLE, metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('name', Text),
    Column('version', Text),
    UniqueConstraint('name'),
    useexisting=True,
)

resourcetypes_tab = Table(DEFAULT_PREFIX + RESOURCETYPES_TABLE, metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('name', Text,),
    Column('package_id', Integer,
           ForeignKey(DEFAULT_PREFIX + PACKAGES_TABLE + '.id')),
    Column('version', Text),
    Column('version_control', Boolean),
    UniqueConstraint('name', 'package_id'),
    useexisting=True,
)

schema_tab = Table(DEFAULT_PREFIX + SCHEMA_TABLE, metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('document_id', Integer, nullable=False),
    Column('package_id', Integer,
           ForeignKey(DEFAULT_PREFIX + PACKAGES_TABLE + '.id'),
           nullable=False),
    Column('resourcetype_id', Integer,
           ForeignKey(DEFAULT_PREFIX + RESOURCETYPES_TABLE + '.id')),
    Column('type', Text),
    UniqueConstraint('package_id', 'resourcetype_id', 'type'),
    useexisting=True,
)

stylesheet_tab = Table(DEFAULT_PREFIX + STYLESHEET_TABLE, metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('document_id', Integer, nullable=False),
    Column('package_id', Integer,
           ForeignKey(DEFAULT_PREFIX + PACKAGES_TABLE + '.id'),
           nullable=False),
    Column('resourcetype_id', Integer,
           ForeignKey(DEFAULT_PREFIX + RESOURCETYPES_TABLE + '.id')),
    Column('type', Text),
    UniqueConstraint('package_id', 'resourcetype_id', 'type'),
    useexisting=True,
)

alias_tab = Table(DEFAULT_PREFIX + ALIAS_TABLE, metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('uri', Text, nullable=False),
    Column('expr', Text, nullable=False),
    UniqueConstraint('uri'),
    useexisting=True,
)
