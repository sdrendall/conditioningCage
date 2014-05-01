from twisted.internet import stdio
from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import ServerFactory

import os, sys, datetime
import subprocess as sp


class IoCommandProtocol(LineReceiver):
    from os import linesep as delimiter

    client = None

    def connectionMade(self):
        self.transport.write('>>> ')

    def lineReceived(self, line):
        # Ignore blank lines
        if not line: return
        self.parseLine(line)
        self.transport.write('>>> ')

    def printToDisplay(self, line):
        self.transport.write('\n')
        self.sendLine(line)
        self.transport.write('>>> ')

    def parseLine(self, line):
        # Split it up
        allArgs = line.split()
        command = allArgs[0].lower()
        args = allArgs[1:]
        # Send it off
        self.sendCommandToCage(command, args)

    def addClient(self, client):
        self.client = client

    def removeClient(self):
        self.client = None


    def sendCommandToCage(self, command, args):

        if self.client is not None:
            try:
                method = getattr(self.client, "do_" + command)
            except AttributeError, e:
                self.printToDisplay("[Error]: Command not recognized")
            else:
                try:
                    method(*args)
                except Exception, e:
                    self.printToDisplay("[Error]: " + str(e))
        else:
            self.printToDisplay('No Clients Connected!')


class CageServer(LineReceiver):

    io = None

    def __init__(self):
        self.addr = None

    def connectionMade(self):
        self.addr = self.transport.getPeer()
        self.io.printToDisplay('Connected To {}'.format(self.addr))

    def connectionLost(self, reason):
        self.io.printToDisplay('Connection To {} lost!'.format(self.addr))
        self.io.removeClient()

    def lineReceived(self, line):
        self.io.printToDisplay(line)


    # Cage Commands

    def do_startvid(self, *args):
        sp.Popen("nc -l 5001 | mplayer -fps 31 -cache 1024 -", shell=True)
        self.sendLine('V')

    def do_stopvid(self, *args):
        self.sendLine('X')

    def do_starttimelapse(self, *args):
        self.sendLine('T')

    def do_endtimelapse(self, *args):
        self.sendLine('E')

    def do_startfc(self, *args):
        self.sendLine('F')

    def do_stopfc(self, *args):
        self.sendLine('X')

class CageServerFactory(ServerFactory):

    protocol = CageServer

    def __init__(self, ioProtocol):
        self.io = ioProtocol

    def buildProtocol(self, addr):
        protocol = ServerFactory.buildProtocol(self, addr)
        protocol.io = self.io
        self.io.addClient(protocol)
        return protocol

def main():
    from twisted.internet import reactor
    factory = CageServerFactory(IoCommandProtocol())
    reactor.listenTCP(1025, factory)
    stdio.StandardIO(factory.io)
    reactor.run()

if __name__ == '__main__':
    main()