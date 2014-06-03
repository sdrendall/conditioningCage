from twisted.internet import protocol
import picamera

def echo(line):
    print line

class VideoStreamingProtocol(protocol.Protocol):

    camera = picamera.PiCamera()

    def connectionMade(self):
        from twisted.internet import reactor
        print "Connection Made!"
        print "Recording in 3 seconds....."
        reactor.callLater(3, self.startRecording)
        for i in range(1,3):
            reactor.callLater(i, echo, 3-i)

    def connectionLost(self, reason):
        self.stopRecording()

    def startRecording(self):
        self.camera.start_recording(self.transport, format='h264', bitrate=3000000)

    def stopRecording(self):
        self.camera.stop_recording()

class VideoStreamingFactory(protocol.ClientFactory):
    protocol = VideoStreamingProtocol

def main():
    from twisted.internet import reactor
    factory = VideoStreamingFactory()
    reactor.connectTCP('10.200.0.39', 5001, factory)
    reactor.run()

if __name__ == '__main__':
    main()