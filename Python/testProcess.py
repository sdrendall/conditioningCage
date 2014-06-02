# Testing script to characterize reactor.spawnProcess

from twisted.internet import reactor, protocol
import os

class RaspiVidStreamProtocol(protocol.ProcessProtocol):

    def outRecived(data):
        print 'outReceived: ', data