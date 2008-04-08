# -*- coding: utf-8 -*-

from twisted.application import service

from seishub.env import Environment
from seishub.services.admin import AdminService
from seishub.services.rest import RESTService
from seishub.services.ssh import SSHService
from seishub.services.heartbeat import HeartbeatService


# setup our Environment
env=Environment()

# Twisted
# XXX: maybe use gid and uid for posix environments
#application = service.Application("SeisHub", uid=XXX, gid=XXX)
application = service.Application("SeisHub")
env.app = application

# Admin
admin_service = AdminService(env)

# REST
rest_service = RESTService(env)

# SSH
ssh_service = SSHService(env)

# heartbeat
heartbeat_service = HeartbeatService(env)

# update

