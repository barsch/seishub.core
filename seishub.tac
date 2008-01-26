# -*- coding: utf-8 -*-

import os

from twisted.application import service
from twisted.python import log

from seishub.env import Environment
from seishub.services.admin.service import getAdminService
from seishub.services.rest.service import getRESTService
from seishub.services.telnet.service import getTelnetService


env=Environment()

# Logging
LOG_DIR = env.config.get('logging','log_dir')
DEBUG_LOG_FILE = env.config.get('logging','debug_log_file')
log.startLogging(open(os.path.join(LOG_DIR, DEBUG_LOG_FILE), 'w'))

# Twisted
# XXX: maybe use gid and uid for posix environments
#application = service.Application("SeisHub", uid=XXX, gid=XXX)
application = service.Application("SeisHub")
env.app=application

# Admin
admin_service = getAdminService(env)
admin_service.setServiceParent(application)

# REST
rest_service = getRESTService(env)
rest_service.setServiceParent(application)

# Telnet
telnet_service = getTelnetService(env)
telnet_service.setServiceParent(application)

# heartbeat

# update

