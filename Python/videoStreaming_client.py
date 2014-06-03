from twisted.internet import protocol
import picamera

class VideoStreamingProtocol(protocol.Protocol):

    camera = picamera.PiCamera()

    def connectionMade(self):
        self.startRecording()

    def connectionLost(self):
        self.stopRecording()

    def startRecording(self):
        self.camera.start_recording(self.transport, format='h264', quantization=23)

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