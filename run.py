#!/usr/bin/env python
# -*- coding: utf-8 -*-

from twisted.application import service
from twisted.internet import reactor 

from seishub.env import Environment
from seishub.services.admin import AdminServiceFactory
from seishub.defaults import ADMIN_PORT, REST_PORT, SSH_PORT, SFTP_PORT
from seishub.services.rest import RESTServiceFactory
from seishub.services.ssh import SSHServiceFactory
from seishub.services.sftp import SFTPServiceFactory


def main():
    # setup our Environment
    env=Environment()
    
    # Twisted
    application = service.Application("SeisHub")
    env.app = application
    
    ## Admin
    port = env.config.getint('admin', 'port') or ADMIN_PORT
    reactor.listenTCP(port, AdminServiceFactory(env)) #@UndefinedVariable
    
    ## REST
    port = env.config.getint('rest', 'port') or REST_PORT
    reactor.listenTCP(port, RESTServiceFactory(env)) #@UndefinedVariable
    
    ## SSH
    port = env.config.getint('ssh', 'port') or SSH_PORT
    reactor.listenTCP(port, SSHServiceFactory(env)) #@UndefinedVariable
    
    ## SSH
    port = env.config.getint('sftp', 'port') or SFTP_PORT
    reactor.listenTCP(port, SFTPServiceFactory(env)) #@UndefinedVariable
    
    reactor.run() #@UndefinedVariable


if __name__ == '__main__':
    main()