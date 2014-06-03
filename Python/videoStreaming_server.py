from twisted.internet import protocol
import os

class MplayerProtocol(protocol.ProcessProtocol):

    def __init__(self, vidProt):
        self.vidProtocol = vidProt

    def writeData(self, data):
        #print "writing to mplayer...."
        self.transport.write(data)
        self.vidProtocol.outFile.write(data)

    def errReceived(self, data):
        print 'err Received!'
        print data

    def outReceived(self, data):
        print 'out Received!'
        print data

    def processExited(self, status):
        print 'Process Exited!'
        status.printTraceback()        


class VideoReceivingProtocol(protocol.Protocol):
    mpArgs = None
    mpProtocol = None
    outFile = open('/home/sam/test.h264', 'w')

    def connectionMade(self):
        self.openMplayer()

    def openMplayer(self):
        from twisted.internet import reactor
        reactor.spawnProcess(self.mpProtocol, '/usr/bin/mplayer', args=self.mpArgs, env=os.environ)

    def dataReceived(self, data):
        #print "Received %d bytes of data!" % len(data)
        self.mpProtocol.writeData(data)

    def connectionLost(self, reason):
        print 'Connection Lost!'


class VideoReceivingFactory(protocol.ServerFactory):
    protocol = VideoReceivingProtocol

    def buildProtocol(self, addr):
        p = protocol.ServerFactory.buildProtocol(self, addr)
        p.mpArgs = ['-fps 31', '-cache', '1024', '-']
        #p.mpArgs = ['--demux h264', '-']
        p.mpProtocol = MplayerProtocol(p)
        return p


def main():
    from twisted.internet import reactor
    factory = VideoReceivingFactory()
    reactor.listenTCP(5001, factory)
    reactor.run()

if __name__ == '__main__':
    main()