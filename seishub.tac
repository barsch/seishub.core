# -*- coding: utf-8 -*-

from twisted.application import service

from seishub.env import Environment
from seishub.services.admin.service import AdminService
from seishub.services.rest.service import RESTService
from seishub.services.ssh.service import SSHService


# setup our Environment
env=Environment()

# Twisted
# XXX: maybe use gid and uid for posix environments
#application = service.Application("SeisHub", uid=XXX, gid=XXX)
application = service.Application("SeisHub")
env.app=application

# Admin
admin_service = AdminService(env)
admin_service.setServiceParent(application)

# REST
rest_service = RESTService(env)
rest_service.setServiceParent(application)

# SSH
telnet_service = SSHService(env)
telnet_service.setServiceParent(application)

# heartbeat

# update

