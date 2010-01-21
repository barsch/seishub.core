# -*- coding: utf-8 -*-

from seishub.env import EnvironmentBase
from seishub.services.seedmonitor import SEEDFileMonitorService
from twisted.application import service


# create application
application = service.Application("SEEDMonitor")

# setup our Environment
env = EnvironmentBase(id='seedmon', application = application)

# set default values
env.config.set('seedfilemonitor', 'autostart', True)
env.config.set('seedfilemonitor', 'scanner_period', 0)
env.config.set('seedfilemonitor', 'crawler_period', 0)
env.config.save()

# SEED File Monitor
seedmonitor_service = SEEDFileMonitorService(env)
