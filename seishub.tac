# -*- coding: utf-8 -*-

import os

from twisted.application import service, internet
from twisted.internet import protocol, reactor, defer, task
from twisted.protocols import basic
from twisted.web import resource, server, static, script
from twisted.python import log

from seishub.env import Environment
from seishub.services.admin.service import AdminService
from seishub.services.rest.service import RESTService
from seishub.services.telnet.service import TelnetService


env=Environment()

# Logging
LOG_DIR = env.config.get('logging','log_dir')
DEBUG_LOG_FILE = env.config.get('logging','debug_log_file')
log.startLogging(open(os.path.join(LOG_DIR, DEBUG_LOG_FILE), 'w'))

# Twisted
application = service.Application("SeisHub", uid=1, gid=1)
env.app=application

# Admin
ADMIN_PORT = env.config.getint('admin','port') or 40441
admin_service = internet.TCPServer(ADMIN_PORT, AdminService(env))
admin_service.setName("WebAdmin")
admin_service.setServiceParent(application)

# REST
REST_PORT = env.config.getint('rest','port') or 8080
rest_service = internet.TCPServer(REST_PORT, server.Site(RESTService(env)))
rest_service.setName("REST")
rest_service.setServiceParent(application)

# heartbeat

# update

# Telnet
TELNET_PORT = env.config.getint('telnet','port') or 5001
telnet_service = internet.TCPServer(TELNET_PORT, TelnetService(env))
telnet_service.setName("Telnet")
telnet_service.setServiceParent(application)
