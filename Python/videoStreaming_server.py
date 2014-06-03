from twisted.internet import protocol

class MplayerProtocol(protocol.ProcessProtocol):

    def __init__(self, vidProt):
        self.vidProtocol = vidProt

    def writeData(self, data):
        print "writing to mplayer...."
        self.transport.write(data)

    def inConnectionLost(self):
        # Close socket
        self.vidProtocol.transport.loseConnection()


class VideoReceivingProtocol(protocol.Protocol):
    mpArgs = None
    mpProtocol = None

    def connectionMade(self):
        self.openMplayer()

    def openMplayer(self):
        from twisted.internet import reactor
        reactor.spawnProcess(self.mpProtocol, '/usr/bin/mplayer', args=self.mpArgs)

    def dataReceived(self, data):
        print "Received %d bytes of data!" % len(data)
        self.mpProtocol.writeData(data)


class VideoReceivingFactory(protocol.ServerFactory):
    protocol = VideoReceivingProtocol

    def buildProtocol(self, addr):
        p = protocol.ServerFactory.buildProtocol(self, addr)
        p.mpArgs = '-fps 31 -cache 1024 -'.split()
        p.mpProtocol = MplayerProtocol(p)
        return p


def main():
    from twisted.internet import reactor
    factory = VideoReceivingFactory()
    reactor.listenTCP(5001, factory)
    reactor.run()

if __name__ == '__main__':
    main()