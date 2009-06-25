# -*- coding: utf-8 -*-

from seishub.env import Environment
from seishub.services.seedmonitor import SEEDFileMonitorService
from seishub.services.sftp import SFTPService
from seishub.services.ssh import SSHService
from seishub.services.web import WebService
from twisted.application import service
#from seishub.services.heartbeat import HeartbeatService


# setup our Environment
env = Environment()

# create application
application = service.Application("SeisHub")
env.app = application

# HTTP/HTTPS
web_service = WebService(env)

# SSH
ssh_service = SSHService(env)

# SFTP
sftp_service = SFTPService(env)

# Heart Beat
#heartbeat_service = HeartbeatService(env)

# SEED File Monitor
seedmonitor_service = SEEDFileMonitorService(env)
