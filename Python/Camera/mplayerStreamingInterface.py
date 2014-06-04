from twisted.internet import protocol, fdesc, error
from twisted.protocols import basic
import os

class MplayerProtocol(protocol.ProcessProtocol):

    def __init__(self, vidProt, mpArgs):
        self.receivingProtocol = vidProt
        self.mpArgs = mpArgs

    def openMplayer(self):
        from twisted.internet import reactor
        reactor.spawnProcess(self, '/usr/bin/mplayer', args=self.mpArgs, env=os.environ)

    def writeToMplayer(self, data):
        #print "writing to mplayer...."
        self.transport.write(data)

    def closeMplayer(self):
        try:
            self.transport.signalProcess('KILL')
        except error.ProcessExitedAlready:
            pass

    def connectionMade(self):
        # Signal to the client once mplayer has successfully opened
        self.receivingProtocol.enterStreamingMode()

    def processEnded(self, reason):
        self.receivingProtocol.disconnect()

    def errReceived(self, data):
        print '[stderr] mplayer:'
        print data

    def outReceived(self, data):
        print '[stdout] mplayer:'
        print data


class VideoReceivingProtocol(basic.LineReceiver):
    """ Handles data transfer to and from the VideoStreamingProtocol.
    Signals to the VideoStreamingProtocol when the MplayerProtocol 
    successfully connects to an mplayer process.  Sends incoming data
    to the MplayerProtocol to be displayed, and to an output file, if 
    one is specified. """

    mpProtocol = None
    outputFile = None

    def connectionMade(self):
        self.mpProtocol.openMplayer()

    # Called by self.mpProtocol when connected to the Mplayer protocol
    def enterStreamingMode(self):
        # Convert to raw data mode
        self.setRawMode()
        # Send ready signal to the streamer
        self.signalMplayerReady()

    def signalMplayerReady(self):
        self.sendLine('ready')

    # Called upon receiving data after signalMplayerReady is called.
    # At this point, all incoming data should be video
    def rawDataReceived(self, data):
        self.mpProtocol.writeToMplayer(data)
        self.writeToFile(data)

    def connectionLost(self, reason):
        print 'Connection to VideoStreamer Lost!'
        self.mpProtocol.closeMplayer()
        self.closeOutputFile()

    def openOutputFile(self, path):
        if path is not None:
            try:
                # Open the file descriptor
                self.outputFile = open(path)
                # Make it nonblocking
                fdesc.setNonBlocking(self.outputFile)
            except:
                print "Warning! Incoming video stream will not save to local file!"
                self.outputFile = None

    def writeToFile(self, data):
        if self.outputFile is not None:
            # Write to nonblocking output file descriptor
            fdesc.writeToFD(self.outputFile, data)

    def closeOutputFile(self):
        if self.outputFile is not None:
            self.outputFile.close()

    def disconnect(self):
        self.transport.loseConnection()
        

class VideoReceivingFactory(protocol.ServerFactory):
    """ Builds VideoReceivingProtocols after connecting
     to a VideoStreamingFactory on a cage (or nannyCam) client.

        A dict specifying parameters can be passed to the
        VideoReceivingFactory on instantiation.

        Currently, the only parameter that can be specified is
            'localOutputPath', which specifies a destination
            for h264 video to be saved
    """

    protocol = VideoReceivingProtocol

    def __init__(self, params={'localOutputPath': None}):
        self.mplayerParams = params

    def buildProtocol(self, addr):
        p = protocol.ServerFactory.buildProtocol(self, addr)
        p.openOutputFile(self.mplayerParams['localOutputPath'])
        mpArgs = ['mplayer', '-fps', '31', '-cache', '1024', '-']
        p.mpProtocol = MplayerProtocol(p, mpArgs)
        return p


def main():
    from twisted.internet import reactor
    factory = VideoReceivingFactory()
    reactor.listenTCP(5001, factory)
    reactor.run()

if __name__ == '__main__':
    main()