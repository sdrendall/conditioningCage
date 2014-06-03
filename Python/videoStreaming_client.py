from twisted.internet import protocol
import os 
#import picamera

def echo(line):
    print line

class RaspiVidProtocol(protocol.ProcessProtocol):

    def __init__(self, streamProto):
        self.streamingProtocol = streamProto

    def outReceived(self, data):
        print 'Received %d bytes' % len(data)
        print 'Writing to socket...'
        self.streamingProtocol.sendData(data)

    def errReceived(self, data):
        print 'err Received!'
        print data

    def processExited(self, status):
        print 'Process Exited!'
        status.printTraceback()        


class VideoStreamingProtocol(protocol.Protocol):
    rpiVidArgs = ('raspiVid'
        '-t', '60000',
        '-fps', '30',
        '-cfx', '128:128',
        '-b', '3000000',
        '-w', '1280',
        '-h', '740',
        '-o', '-')
    rpiVidProtocol = None

    def connectionMade(self):
        from twisted.internet import reactor
        print "Connection Made!"
        print "Recording in 3 seconds....."
        reactor.callLater(3, self.startRecording)
        for i in range(1,3):
            reactor.callLater(i, echo, 3-i)

    def sendData(self, data):
        self.transport.write(data)

    def connectionLost(self, reason):
        self.stopRecording()

    def startRecording(self):
        from twisted.internet import reactor
        reactor.spawnProcess(self.rpiVidProtocol, '/usr/bin/raspivid', args=self.rpiVidArgs, env=os.environ)
        #self.camera.start_recording(self.transport, format='h264', bitrate=3000000)

    def stopRecording(self):
        self.rpiVidProtocol.transport.signalProcess('KILL')

class VideoStreamingFactory(protocol.ClientFactory):
    protocol = VideoStreamingProtocol

    def buildProtocol(self, addr):
        p = protocol.ClientFactory.buildProtocol(self, addr)
        p.rpiVidProtocol = RaspiVidProtocol(p)
        return p

def main():
    from twisted.internet import reactor
    factory = VideoStreamingFactory()
    reactor.connectTCP('10.200.0.39', 5001, factory)
    reactor.run()

if __name__ == '__main__':
    main()