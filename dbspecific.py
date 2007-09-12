from seishub.dbconfig import DEFAULT_PREFIX,RESOURCE_TABLE,URI_TABLE

DB_DRIVER = "pyPgSQL.PgSQL"
#DB_DRIVER="pgdb"
DB_ARGS = {
    'database':'seishub',
    'user':'seishub',
    'password':'seishub'
    }

CREATES=["CREATE TABLE %s_%s (id serial8 primary key, xml_data text)" % (DEFAULT_PREFIX,RESOURCE_TABLE),
         "CREATE TABLE %s_%s (uri text primary key, res_id int8 references %s_%s(id))" % (DEFAULT_PREFIX,URI_TABLE,DEFAULT_PREFIX,RESOURCE_TABLE),
         ]

QUERY_STR_MAP={'res_tab':DEFAULT_PREFIX+'_'+RESOURCE_TABLE,
               'uri_tab':DEFAULT_PREFIX+'_'+URI_TABLE,
               }

ADD_RESOURCE_QUERY="""INSERT INTO %s_%s (id,xml_data) values (%s,%s)"""
DELETE_RESOURCE_QUERY="""DELETE FROM %(res_tab)s WHERE (id = '%(res_id)s')"""
REGISTER_URI_QUERY="""INSERT INTO %s_%s (res_id,uri) values (%s,%s)"""
REMOVE_URI_QUERY="""DELETE FROM %(uri_tab)s WHERE (uri='%(uri)s')"""
GET_NEXT_ID_QUERY="""SELECT nextval('%s_%s_id_seq')"""
GET_ID_BY_URI_QUERY="""SELECT res_id FROM %(uri_tab)s WHERE (uri='%(uri)s')"""
GET_RESOURCE_BY_URI_QUERY="""SELECT xml_data FROM %(res_tab)s,%(uri_tab)s
                          WHERE(%(res_tab)s.id=%(uri_tab)s.res_id
                          AND %(uri_tab)s.uri='%(uri)s')
                          """

