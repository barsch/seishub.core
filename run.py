#!/usr/bin/env python
# -*- coding: utf-8 -*-

from twisted.application import service
from twisted.internet import reactor

from seishub.env import Environment
from seishub.services.admin import AdminServiceFactory
from seishub.defaults import ADMIN_PORT, REST_PORT, SSH_PORT
from seishub.services.rest import RESTServiceFactory
from seishub.services.ssh import SSHServiceFactory


def main():
    # setup our Environment
    env=Environment()
    
    # Twisted
    application = service.Application("SeisHub")
    env.app = application
    
    ## Admin
    port = env.config.getint('admin', 'port') or ADMIN_PORT
    reactor.listenTCP(port, AdminServiceFactory(env))
    
    ## REST
    port = env.config.getint('rest', 'port') or REST_PORT
    reactor.listenTCP(port, RESTServiceFactory(env))
    
    ## SSH
    port = env.config.getint('ssh', 'port') or SSH_PORT
    reactor.listenTCP(port, SSHServiceFactory(env))

    reactor.run()


if __name__ == '__main__':
    main()