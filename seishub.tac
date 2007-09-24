# -*- coding: utf-8 -*-

import os

from twisted.application import service, internet
from twisted.internet import protocol, reactor, defer, task
from twisted.protocols import basic
from twisted.web import resource, server, static, script
from twisted.python import log
#from twisted.enterprise import adbapi 

from seishub.services.admin import admin
from seishub.services.rest import rest
from seishub.config import Configuration
from seishub.log import LogService

# import config file
confs = Configuration()

LOG_DIR = confs.get('logging','log_dir')
LOG_ROTATE = confs.getbool('logging','log_rotate')
ACCESS_LOG_FILE = confs.get('logging','access_log_file')
ERROR_LOG_FILE = confs.get('logging','error_log_file')
DEBUG_LOG_FILE = confs.get('logging','debug_log_file')

SERVICE_ADMIN_PORT = confs.getint('admin','port')
SERVICE_REST_PORT = confs.getint('rest','port')

log.startLogging(open(os.path.join(LOG_DIR, DEBUG_LOG_FILE), 'w'))


#DB_DRIVER = "MySQLdb"
#DB_ARGS = {
#    'db':          'seishub',
#    'host':        'localhost',
#    'user':        'seishub',
#    'passwd'   :   'seishub',
#}


### DB
#db = adbapi.ConnectionPool(DB_DRIVER, **DB_ARGS)



### Twisted
application = service.Application("seishub")

# rest
webRoot = resource.Resource(  )
webRoot.putChild('', rest.RESTService())
webService = internet.TCPServer(SERVICE_REST_PORT, server.Site(webRoot))
webService.setName("REST Service")
webService.setServiceParent(application)

# admin
adminRoot = resource.Resource()
adminRoot.putChild('', admin.AdminService(application))
adminService = internet.TCPServer(SERVICE_ADMIN_PORT, server.Site(adminRoot))
adminService.setName("Admin Service")
adminService.setServiceParent(application)


# Log Services
accesslogService = LogService(ACCESS_LOG_FILE, LOG_DIR, "access", LOG_ROTATE)
accesslogService.setName("Access Log")
accesslogService.setServiceParent(application)

errorlogService = LogService(ERROR_LOG_FILE, LOG_DIR, "error", LOG_ROTATE)
errorlogService.setName("Error Log")
errorlogService.setServiceParent(application)

# heartbeat

# update

# telnet

 