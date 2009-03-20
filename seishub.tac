# -*- coding: utf-8 -*-

from twisted.application import service

from seishub.env import Environment
from seishub.services.web import WebService
from seishub.services.ssh import SSHService
from seishub.services.sftp import SFTPService
from seishub.services.heartbeat import HeartbeatService
from seishub.services.filemonitor import SEEDFileMonitorService
import sys


# check for python version
if not sys.hexversion >= 0x2060000:
    print "ERROR: SeisHub needs at least Python 2.6 or higher in order to run."
    exit()

# setup our Environment
env=Environment()

# Twisted
# XXX: maybe use gid and uid for posix environments
#application = service.Application("SeisHub", uid=XXX, gid=XXX)
application = service.Application("SeisHub")
env.app = application

# HTTP/HTTPS
web_service = WebService(env)

# SSH
ssh_service = SSHService(env)

# SFTP
sftp_service = SFTPService(env)

# Heart Beat
heartbeat_service = HeartbeatService(env)

# SEED File Monitor
filemonitor_service = SEEDFileMonitorService(env)

# update
