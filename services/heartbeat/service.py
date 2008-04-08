# -*- coding: utf-8 -*-

import time
import socket

from twisted.application import internet
from twisted.internet import protocol

from seishub.config import IntOption
from seishub.defaults import HEARTBEAT_UDP_PORT, \
                             HEARTBEAT_CHECK_PERIOD, \
                             HEARTBEAT_CHECK_TIMEOUT


class HeartbeatReceiver(protocol.DatagramProtocol):
    """Receive UDP heartbeat packets and log them in a dictionary."""
    
    def __init__(self, env):
        self.env = env
    
    def datagramReceived(self, data, (ip, port)):
        self.env.nodes[ip] = [time.time(), data]


class HeartbeatDetector(internet.TimerService):
    """Detect clients not sending heartbeats and removes them from list."""
    
    def __init__(self, env):
        self.env = env
        internet.TimerService.__init__(self, HEARTBEAT_CHECK_PERIOD, self.detect)
    
    def detect(self):
        """Detects clients w/ heartbeat older than HEARTBEAT_CHECK_TIMEOUT."""
        limit = time.time() - HEARTBEAT_CHECK_TIMEOUT
        #silent = [ip for (ip, ipTime) in self.env.nodes.items() if ipTime < limit]
        print 'Active clients: %s' % self.env.nodes.items()


class HeartbeatTransmitter(internet.TimerService):
    """Sends heartbeat to list of active nodes."""

    def __init__(self, env):
        self.env = env
        internet.TimerService.__init__(self, HEARTBEAT_CHECK_PERIOD, self.transmit)
    
    def transmit(self):
        hbsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        hbsocket.sendto('SeisHub', ('127.0.0.1', 43278))
        print 'Transmission'


class HeartbeatService(internet.UDPServer):
    """A asynchronous events-based heartbeat server for SeisHub."""
    IntOption('heartbeat', 'port', HEARTBEAT_UDP_PORT, 
              'Heartbeat port number.')
    
    def __init__(self, env):
        env.nodes = {}
        
        detector_service = HeartbeatDetector(env)
        detector_service.setName("Heartbeat Detector")
        detector_service.setServiceParent(env.app)
        
        transmitter_service = HeartbeatTransmitter(env)
        transmitter_service.setName("Heartbeat Transmitter")
        transmitter_service.setServiceParent(env.app)
        
        receiver_service = HeartbeatReceiver(env)
        
        port = env.config.getint('heartbeat', 'port')
        internet.UDPServer.__init__(self, port, receiver_service)
        self.setName("Heartbeat Receiver")
        self.setServiceParent(env.app)
