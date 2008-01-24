# -*- coding: utf-8 -*-

import os

from twisted.application import service, internet
from twisted.internet import protocol, reactor, defer, task
from twisted.protocols import basic
from twisted.web import resource, server, static, script
from twisted.python import log

from seishub.services.admin import admin
from seishub.services.rest import rest
from seishub.env import Environment


env=Environment()

# twisted logging
LOG_DIR = env.config.get('logging','log_dir')
DEBUG_LOG_FILE = env.config.get('logging','debug_log_file')
log.startLogging(open(os.path.join(LOG_DIR, DEBUG_LOG_FILE), 'w'))

### Twisted
SERVICE_ADMIN_PORT = env.config.getint('admin','port')
SERVICE_REST_PORT = env.config.getint('rest','port')

application = service.Application("SeisHub", uid=1, gid=1)
env.app=application

# Admin
adminService = internet.TCPServer(SERVICE_ADMIN_PORT, 
                                  admin.AdminHTTPFactory(env))
adminService.setName("Admin Service")
adminService.setServiceParent(application)

# REST
webRoot = rest.RESTService(env)
webService = internet.TCPServer(SERVICE_REST_PORT, server.Site(webRoot))
webService.setName("REST Service")
webService.setServiceParent(application)

# heartbeat

# update

# telnet

 