# -*- coding: utf-8 -*-
"""
Test suite for DB utilities.
"""

from seishub.db import DEFAULT_PREFIX, util
from seishub.db.manager import meta
from seishub.test import SeisHubEnvironmentTestCase
from sqlalchemy import sql, Table, Column, Integer, String, ForeignKey, and_, \
    or_
import unittest


test_meta = meta

users = Table(DEFAULT_PREFIX+'users', test_meta,
    Column('id', Integer, primary_key=True),
    Column('name', String),
    Column('fullname', String),
)

addresses = Table(DEFAULT_PREFIX+'addresses', test_meta,
    Column('id', Integer, primary_key=True),
    Column('user_id', None, ForeignKey(DEFAULT_PREFIX+'users.id')),
    Column('email_address', String, nullable=False)
)

SQL_QUERY_1 = """SELECT default_users.fullname || ', ' || default_addresses.email_address AS title 
FROM default_users, default_addresses 
WHERE default_users.id = default_addresses.user_id AND default_users.name BETWEEN 'm' AND 'z' AND (default_addresses.email_address LIKE '%@aol.com' OR default_addresses.email_address LIKE '%@msn.com')"""

SQL_QUERY_2 = """SELECT default_users.id, default_users.name, default_users.fullname, default_addresses.id, default_addresses.user_id, default_addresses.email_address 
FROM default_users LEFT OUTER JOIN default_addresses ON default_users.id = default_addresses.user_id 
WHERE default_users.name LIKE 'jack' || '%' OR default_addresses.email_address LIKE 'jack' || '@%'"""


class DBUtilTest(SeisHubEnvironmentTestCase):
    """
    Test suite for DB utilities.
    """
    def setUp(self):
        self.db = self.env.db.engine
        test_meta.create_all(self.db, checkfirst = True)
        # insert a few test values
        self.db.execute(users.insert(), [ 
            {'id': 1, 'name':'jack', 'fullname':'Jack Jones'},
            {'id': 2, 'name':'wendy', 'fullname':'Wendy Williams'},
            {'id': 3, 'name':'fred', 'fullname':'Fred Flintstone'},
            {'id': 4, 'name':'mary', 'fullname':'Mary Contrary'},
        ])
        self.db.execute(addresses.insert(), [ 
            {'user_id': 1, 'email_address' : 'jack@yahoo.com'},
            {'user_id': 1, 'email_address' : 'jack@msn.com'},
            {'user_id': 2, 'email_address' : 'www@www.org'},
            {'user_id': 2, 'email_address' : 'wendy@aol.com'},
        ])
    
    def tearDown(self):
        addresses.drop()
        users.drop()
    
    def test_compileStaticSQLStatement(self):
        """
        Tests compiling of a static statement.
        """
        sql_auto = sql.select(
            [(users.c.fullname + ", " + 
              addresses.c.email_address).label('title')],
            and_(
                users.c.id==addresses.c.user_id,
                users.c.name.between('m', 'z'),
                or_(
                    addresses.c.email_address.like('%@aol.com'),
                    addresses.c.email_address.like('%@msn.com')
                )
            )
        )
        # check result
        result = self.db.execute(sql_auto)
        result = result.fetchall()
        self.assertEquals(result, [(u'Wendy Williams, wendy@aol.com',)])
        # compiled statement
        sql_compiled = util.compileStatement(sql_auto)
        self.assertEquals(sql_compiled, SQL_QUERY_1)
        # check result
        result = self.db.execute(sql.text(sql_compiled))
        result = result.fetchall()
        self.assertEquals(result, [(u'Wendy Williams, wendy@aol.com',)])
    
    def test_compileStatementFromText(self):
        sql_auto = sql.select(
            [sql.text(DEFAULT_PREFIX+"users.fullname || ', ' || " + 
                      DEFAULT_PREFIX+"addresses.email_address AS title")],
            and_(DEFAULT_PREFIX + "users.id = " + DEFAULT_PREFIX + 
                 "addresses.user_id", 
                 DEFAULT_PREFIX + "users.name BETWEEN 'm' AND 'z'",
                 "(" + DEFAULT_PREFIX + "addresses.email_address LIKE :x OR " +
                 DEFAULT_PREFIX+"addresses.email_address LIKE :y)"
            ),
            from_obj=[DEFAULT_PREFIX+'users', DEFAULT_PREFIX+'addresses']
        )
        # check result
        result = self.db.execute(sql_auto, x='%@aol.com', y='%@msn.com')
        result = result.fetchall()
        self.assertEquals(result, [('Wendy Williams, wendy@aol.com',)])
        # compiled statement
        sql_compiled = util.compileStatement(sql_auto, bind = self.db,
                                             x="'%@aol.com'", y="'%@msn.com'")
        self.assertEquals(sql_compiled, SQL_QUERY_1)
        # check result
        result = self.db.execute(sql.text(sql_compiled))
        result = result.fetchall()
        self.assertEquals(result, [('Wendy Williams, wendy@aol.com',)])
    
    def test_compileStatementWithBindParameter(self):
        sql_auto = sql.select([users, addresses],
            users.c.name.like(
                sql.bindparam('name', type_=String) + sql.text("'%'")) |
            addresses.c.email_address.like(
                sql.bindparam('name', type_=String) + sql.text("'@%'")),
            from_obj=[users.outerjoin(addresses)]
        )
        # check result
        result = self.db.execute(sql_auto, name='jack')
        result = result.fetchall()
        self.assertEquals(result, [
            (1, u'jack', u'Jack Jones', 1, 1, u'jack@yahoo.com'), 
            (1, u'jack', u'Jack Jones', 2, 1, u'jack@msn.com')]
        )
        # compiled statement
        sql_compiled = util.compileStatement(sql_auto, name="'jack'")
        self.assertEquals(sql_compiled, SQL_QUERY_2)
        # check result
        result = self.db.execute(sql.text(sql_compiled))
        result = result.fetchall()
        self.assertEquals(result, [
            (1, u'jack', u'Jack Jones', 1, 1, u'jack@yahoo.com'), 
            (1, u'jack', u'Jack Jones', 2, 1, u'jack@msn.com')]
        )


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DBUtilTest, 'test'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
