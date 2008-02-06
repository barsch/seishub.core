# -*- coding: utf-8 -*-

from twisted.application import service
from twisted.internet import reactor

from seishub.env import Environment
from seishub.services.admin.service import AdminHTTPFactory
from seishub.defaults import DEFAULT_ADMIN_PORT, DEFAULT_REST_PORT, \
                             DEFAULT_TELNET_PORT
from seishub.services.rest.service import RESTHTTPFactory
from seishub.services.telnet.service import TelnetServerFactory


# setup our Environment
env=Environment()

# Twisted
application = service.Application("SeisHub")
env.app=application
#
## Admin
port = env.config.getint('admin', 'port') or DEFAULT_ADMIN_PORT
reactor.listenTCP(port, AdminHTTPFactory(env))
#
## REST
port = env.config.getint('rest', 'port') or DEFAULT_REST_PORT
reactor.listenTCP(port, RESTHTTPFactory(env))
#
## Telnet
port = env.config.getint('telnet', 'port') or DEFAULT_TELNET_PORT
reactor.listenTCP(port, TelnetServerFactory(env))

reactor.run()