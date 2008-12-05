# -*- coding: utf-8 -*-

from twisted.application import service

from seishub.env import Environment
from seishub.services.admin import AdminService
from seishub.services.web import WebService
from seishub.services.ssh import SSHService
from seishub.services.sftp import SFTPService
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

# Web
web_service = WebService(env)

# SSH
ssh_service = SSHService(env)

# SFTP
sftp_service = SFTPService(env)

# heartbeat
heartbeat_service = HeartbeatService(env)

# update

