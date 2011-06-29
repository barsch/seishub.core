# -*- coding: utf-8 -*-
"""
Catalog and database related administration panels.
"""

from seishub.core.core import Component, implements
from seishub.core.db import DEFAULT_PREFIX
from seishub.core.exceptions import SeisHubError, InvalidParameterError
from seishub.core.packages.interfaces import IAdminPanel
from seishub.core.registry.defaults import resourcetypes_tab, packages_tab
from seishub.core.xmldb.defaults import index_def_tab, document_tab, \
    resource_tab, document_meta_tab
from seishub.core.xmldb.index import type_classes
from sqlalchemy import sql, not_, func, and_
import os
import pprint
import time


LIMITS = {'10': 10, '100': 100, '1000': 1000, '10000': 10000,
          'unlimited': None}


class DatabaseQueryPanel(Component):
    """
    Query the database via HTTP form.
    """
    implements(IAdminPanel)

    template = 'templates' + os.sep + 'catalog_db_query.tmpl'
    panel_ids = ('catalog', 'Catalog', 'db-query', 'Query Database')
    has_roles = ['CATALOG_ADMIN']

    def render(self, request):
        db = self.env.db.engine
        tables = sorted([t for t in db.table_names() if DEFAULT_PREFIX in t])
        data = {
            'query': 'SELECT 1;',
            'result': '',
            'cols': '',
            'rows': 0,
            'clock': "%0.6f" % 0,
            'tables': tables,
            'views': sorted(self.env.db.getViews()),
            'prefix': DEFAULT_PREFIX,
        }
        args = request.args
        if request.method == 'POST':
            query = None
            if 'query' in args and 'send' in args:
                query = data['query'] = request.args['query'][0]
            elif 'table' in args:
                table = DEFAULT_PREFIX + request.args['table'][0]
                query = 'SELECT * \nFROM ' + table + '\nLIMIT 20;'
            elif 'view' in args:
                view = request.args['view'][0]
                query = 'SELECT * \nFROM "' + view + \
                        '" \nORDER BY document_id DESC\nLIMIT 20;'
            if query:
                data['query'] = query
                try:
                    t1 = time.time()
                    result = db.execute(query)
                    t2 = time.time()
                    data['clock'] = "%0.6f" % (t2 - t1)
                    try:
                        data['cols'] = result.keys
                    except AttributeError:
                        data['cols'] = []
                    data['result'] = result.fetchall()
                    data['rows'] = len(data['result'])
                except Exception, e:
                    self.env.log.error('Database query error', e)
                    data['error'] = ('Database query error', e)
        return data


class ResourcesPanel(Component):
    """
    List all resources.
    """
    implements(IAdminPanel)

    template = 'templates' + os.sep + 'catalog_resources.tmpl'
    panel_ids = ('catalog', 'Catalog', 'resources', 'Resources')
    has_roles = ['CATALOG_ADMIN']

    def render(self, request):
        packages = self.env.registry.getPackageIds()
        resourcetypes = self.env.registry.getAllPackagesAndResourceTypes()
        # remove SeisHub packages and resource types
        packages.remove('seishub')
        resourcetypes.pop('seishub')

        data = {
            'file': '',
            'package_id': '',
            'resourcetype_id': '',
            'resturl': self.env.getRestUrl(),
            'packages': packages,
            'resourcetypes': resourcetypes,
            'resources': [],
            'rows': 0,
            'clock': "%0.6f" % 0,
            'limits': sorted(LIMITS.keys()),
            'limit': '10'
        }
        if request.method == 'POST':
            args = request.args
            data['package_id'] = args.get('package_id', [''])[0]
            data['resourcetype_id'] = args.get('resourcetype_id', [''])[0]
            if 'file' in args:
                data['file'] = args.get('file', [''])[0]
                data = self._addResource(data)
            elif 'delete' in args and 'resource[]' in args:
                data['resource[]'] = args['resource[]']
                data = self._deleteResources(data)
            elif 'delete-all' in args:
                data = self._deleteAllResources(data)
            elif 'filter' in args:
                data['limit'] = args.get('limit', LIMITS.keys())[0]
                data = self._getResources(data)
        return data

    def _getResources(self, data):
        limit = LIMITS.get(data['limit'], 10)
        t1 = time.time()
        result = self.catalog.getAllResourceNames(data['package_id'],
                                                  data['resourcetype_id'],
                                                  limit)
        t2 = time.time()
        data['resources'] = result
        data['clock'] = "%0.6f" % (t2 - t1)
        data['rows'] = len(result)
        return data

    def _addResource(self, data):
        try:
            self.catalog.addResource(package_id=data['package_id'],
                                     resourcetype_id=data['resourcetype_id'],
                                     xml_data=data['file'])
        except InvalidParameterError, e:
            data['error'] = ("Please choose a non-empty XML document", e)
        except SeisHubError, e:
            data['error'] = ("Error adding resource", e)
        data['file'] = ''
        data['info'] = "Resource has been added."
        return data

    def _deleteResources(self, data):
        for id in data.get('resource[]', [None]):
            try:
                self.catalog.deleteResource(resource_id=int(id))
            except Exception, e:
                self.log.info("Error deleting resource", e)
                data['error'] = ("Error deleting resource", e)
                return data
        data['info'] = "Resources have been removed."
        return data

    def _deleteAllResources(self, data):
        try:
            self.catalog.deleteAllResources(
                package_id=data['package_id'],
                resourcetype_id=data['resourcetype_id'])
        except SeisHubError, e:
            data['error'] = ("Error deleting all resources", e)
        data['info'] = "Resources have been deleted."
        return data


class CatalogQueryPanel(Component):
    """
    Query the catalog via HTTP form.
    """
    implements(IAdminPanel)

    template = 'templates' + os.sep + 'catalog_query.tmpl'
    panel_ids = ('catalog', 'Catalog', 'query', 'Query Catalog')
    has_roles = ['CATALOG_ADMIN']

    def render(self, request):
        data = {
            'query': '/seishub/stylesheet order by media-type ASC ' + \
                     'limit 2 offset 5',
            'result': '',
            'rows': '',
            'clock': "%0.6f" % 0
        }
        args = request.args
        if request.method == 'POST':
            query = None
            if 'query' in args and 'send' in args:
                query = data['query'] = request.args['query'][0]
            if query:
                data['query'] = query
                try:
                    t1 = time.time()
                    result = self.catalog.query(query)
                    t2 = time.time()
                    data['clock'] = "%0.6f" % (t2 - t1)
                    data['rows'] = len(result) - 1
                    data['result'] = pprint.pformat(result, 4)
                except Exception, e:
                    self.env.log.info('Catalog query error', e)
                    data['error'] = ('Catalog query error', e)
        return data


class DatabaseStatusPanel(Component):
    """
    Shows some statistics of the database.
    """
    implements(IAdminPanel)

    template = 'templates' + os.sep + 'catalog_status.tmpl'
    panel_ids = ('catalog', 'Catalog', 'status', 'Status')
    has_roles = ['CATALOG_ADMIN']

    def render(self, request):
        if 'tables' in request.path:
            return self._renderTables()
        elif 'resources' in request.path:
            return self._renderResources()
        elif 'dbcheck' in request.path:
            return self._renderDBCheck()
        # default /manage/catalog/status
        return {}

    def _renderTables(self):
        # /manage/catalog/status/tables
        out = ''
        for table in sorted(self.env.db.engine.table_names()):
            if not table.startswith(DEFAULT_PREFIX):
                continue
            # get table disk space size
            size = self.env.db.getTableSize(table)
            # count objects
            try:
                query = "SELECT count(*) FROM %s;" % table
                entries = self.env.db.query(query).fetchall()[0][0]
            except:
                entries = 0
            # format output
            out += "%s|%s|%s\n" % (table, entries, size)
        return out

    def _renderResources(self):
        # /manage/catalog/status/resources
        out = ''
        resourcetypes = self.env.registry.db_getResourceTypes()
        for resourcetype in resourcetypes:
            # resources
            query = sql.select([func.count(resource_tab.c['id'])],
                               distinct=True)
            query = query.where(
                resource_tab.c['resourcetype_id'] == resourcetype._id
            )
            resources = self.env.db.query(query).fetchone()[0]
            # documents
            query = sql.select([func.count(document_tab.c['id'])],
                               distinct=True)
            query = query.where(
                and_(document_tab.c['resource_id'] == resource_tab.c['id'],
                     resource_tab.c['resourcetype_id'] == resourcetype._id)
            )
            documents = self.env.db.query(query).fetchone()[0]
            out += "%s|%s|%d|%d\n" % (resourcetype.package.package_id,
                                      resourcetype.resourcetype_id,
                                      resources, documents)
        return out

    def _renderDBCheck(self):
        # /manage/catalog/status/dbcheck
        out = ''
        # check index tables
        all_indexes = sql.select([index_def_tab.c['id']], distinct=True)
        for index in type_classes.values():
            clean = True
            tab = index.db_table
            out += 'Table %s' % tab
            # index_id
            query = sql.select([tab.c['index_id']],
                               not_(tab.c['index_id'].in_(all_indexes)),
                               distinct=True, limit=20)
            ids = self.env.db.query(query).fetchall()
            for id in ids:
                clean = False
                out += '\n  * Unknown index_id %d' % (id[0])
            if len(ids) == 20:
                out += '\n    (more)'
            # document_id
            oncl = tab.c['document_id'] == document_tab.c['id']
            query = sql.select([tab.c['document_id']],
                               document_tab.c['id'] == None,
                               [tab.outerjoin(document_tab, onclause=oncl)],
                               limit=20)
            ids = self.env.db.query(query).fetchall()
            for id in ids:
                clean = False
                out += '\n  * Unknown document_id %d' % (id[0])
            if clean:
                out += ' - CHECKED'
            if len(ids) == 20:
                out += '\n    (more)'
            out += '\n'
        # check document table
        out += 'Table %s' % document_tab.name
        oncl = document_tab.c['resource_id'] == resource_tab.c['id']
        query = sql.select([document_tab.c['resource_id']],
                           resource_tab.c['id'] == None,
                           [document_tab.outerjoin(resource_tab,
                                                   onclause=oncl)],
                           limit=20)
        ids = self.env.db.query(query).fetchall()
        for id in ids:
            out += '\n  * Unknown resource_id %d' % (id[0])
        else:
            out += ' - CHECKED'
        if len(ids) == 20:
            out += '\n    (more)'
        out += '\n'
        # check document_meta table
        out += 'Table %s' % document_meta_tab.name
        oncl = document_meta_tab.c['id'] == document_tab.c['id']
        query = sql.select([document_meta_tab.c['id']],
                           document_tab.c['id'] == None,
                           [document_meta_tab.outerjoin(document_tab,
                                                        onclause=oncl)],
                           limit=20)
        ids = self.env.db.query(query).fetchall()
        for id in ids:
            out += '\n  * Unknown document_id %d' % (id[0])
        else:
            out += ' - CHECKED'
        if len(ids) == 20:
            out += '\n    (more)'
        out += '\n'
        # check resource table
        out += 'Table %s' % resource_tab.name
        oncl = resource_tab.c['resourcetype_id'] == resourcetypes_tab.c['id']
        query = sql.select([resource_tab.c['resourcetype_id']],
                           resourcetypes_tab.c['id'] == None,
                           [resource_tab.outerjoin(resourcetypes_tab,
                                                   onclause=oncl)],
                           limit=20)
        ids = self.env.db.query(query).fetchall()
        for id in ids:
            out += '\n  * Unknown resourcetype_id %d' % (id[0])
        else:
            out += ' - CHECKED'
        if len(ids) == 20:
            out += '\n    (more)'
        out += '\n'
        # check resourcetypes table
        out += 'Table %s' % resourcetypes_tab.name
        oncl = resourcetypes_tab.c['package_id'] == packages_tab.c['id']
        query = sql.select([resourcetypes_tab.c['package_id']],
                           packages_tab.c['id'] == None,
                           [resourcetypes_tab.outerjoin(packages_tab,
                                                        onclause=oncl)],
                           limit=20)
        ids = self.env.db.query(query).fetchall()
        for id in ids:
            out += '\n  * Unknown package_id %d' % (id[0])
        else:
            out += ' - CHECKED'
        if len(ids) == 20:
            out += '\n    (more)'
        out += '\n'
        return out

