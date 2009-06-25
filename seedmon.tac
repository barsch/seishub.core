# -*- coding: utf-8 -*-

from seishub.env import EnvironmentBase
from seishub.services.seedmonitor import SEEDFileMonitorService
from twisted.application import service


# setup our Environment
env = EnvironmentBase(config_file='seedmon.ini')

# set autostart
env.config.set('seedfilemonitor', 'autostart', True)
env.config.save()

# create application
application = service.Application("SEEDMonitor")
env.app = application

# SEED File Monitor
seedmonitor_service = SEEDFileMonitorService(env)
