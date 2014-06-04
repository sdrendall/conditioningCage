""" This is the video recording module for the raspberry pi clients.  It can be
    used in two ways.  The RaspiVidProtocol provides an interface for the 
    raspivid command that can be used to record video locally.

    Video streaming is accomplished using the VideoStreamingFactory, by calling the
    initiateStreaming commands.

    Video parameters can be set by assigning them to VideoStreamingFactory.vidParams

    The RaspiVidProtocol parameters must be set on initialization """

from twisted.internet import protocol, fdesc, error, defer
from twisted.protocols import basic
import os, subprocess

defaults = {
            'duration': 0,
            'streamTo': '10.117.33.13',
            'streamPort': 5001,
            'width': 1280,
            'height': 740,
            'fps': 30,
            'bitrate': 3000000,
            'outputPath': None
    }

def echo(line):
    print line

def mergeDicts(d1, d2):
    d = d1.copy()
    for key, value in d2.iteritems():
        d[key] = value
    return d

class RaspiVidProtocol(protocol.ProcessProtocol):

    outputFile = None
    fireWhenOutputFileIsClosed = None

    def __init__(self, vidParams={}, streamProto=None):
	vidParams = mergeDicts(defaults, vidParams)
        # Reference the streaming protocol
        self.streamingProtocol = streamProto
        # Set the arguments to call raspivid with
        self.setVidArgs(vidParams)
        # Open an output file
        self.openOutputFile(vidParams)
        # Create an empty list to contain deferreds to be fired
        #  when raspivid is reaped
        self.fireWhenProcessEnds = []

    # Called with data from raspivid's stdout
    def outReceived(self, data):
        self.streamData(data)
        self.writeToFile(data)

    def errReceived(self, data):
        print '[err] raspivid:'
        print data

    def processEnded(self, status):
        self.fireFireWhenProcessEndsDeferreds()

    def fireFireWhenProcessEndsDeferreds():
        # Fire all deferreds in fireWhenProcessEnds
        while self.fireWhenProcessEnds:
            d = fireWhenProcessEnds.pop()
            try:
                d.callback()
            # This will eventually be called when
            #  the parent factory's currentProcessDeferred 
            #  is cancelled
            except defer.AlreadyCalledError:
                pass

    def deferUntilProcessEnds():
        d = defer.Deferred()
        self.fireWhenProcessEnds.append(d)
        return d

    def startRecording(self):
        from twisted.internet import reactor
        reactor.spawnProcess(self, '/usr/bin/raspivid', args=self.vidArgs, env=os.environ)
        return self.deferUntilProcessEnds()

    # Call with maybeDeferred
    def stopRecording(self):
        try:
            self.transport.signalProcess('KILL')
        except error.ProcessExitedAlready:
            return
        return self.deferUntilProcessEnds()

    def setVidArgs(self, params):
        # Create a list of args from params
        vidArgString = 'raspivid -fps {fps} -cfx 128:128 -b {bitrate} -w {width} -h {height} -t {duration} -o -'
        vidArgString = vidArgString.format(**params)
        self.vidArgs = vidArgString.split()

    def streamData(self, data):
        if self.streamingProtocol is not None:
            self.streamingProtocol.sendData(data)
        else:
            self.stopRecording()

    def openOutputFile(self, params):
        if params['outputPath'] is not None:
            self.outputFile = open(params['outputPath'])
            fdesc.setNonBlocking(self.outputFile)
            self.queueConvertToMp4(params)

    def writeToFile(self, data):
        if self.outputFile is not None:
            fdesc.writeToFC(self.outputFile, data)

    def closeOutputFile(self):
        if self.outputFile is not None:
            self.outputFile.close()
            self.outputFile = None
        self.fireFireWhenOutputFileIsClosed()

    def fireFireWhenOutputFileIsClosed(self):
        if self.fireWhenOutputFileIsClosed is not None:
            try:
                d, self.fireWhenOutputFileIsClosed = self.fireWhenOutputFileIsClosed, None
                d.callback()
            except defer.AlreadyCalledError:
                pass

    def queueConvertToMp4(self, params):
        d = defer.Deferred()
        d.addCallback(convertToMp4, params['outputPath'])
        self.fireWhenOutputFileIsClosed = d

    def convertToMp4(self, path):
        # Insecure, outputPath should be sanitized
        comStr = "MP4Box -add %s.h264 %s.mp4 -fps 30 &&" \
                    "rm %s.h264" % path, path, path
        subprocess.Popen(comStr, shell=True)


class VideoStreamingProtocol(basic.LineReceiver):
    rpiVidProtocol = None
    rpiVidParams = None

    def lineReceived(self, line):
        self.parseLine(line)

    def parseLine(self, line):
        # 'ready' indicates that the server has opened mplayer
        #  and that it is ready to receive a stream
        if line == 'ready':
            d = self.startStreaming()
            # disconnect if raspivid is closed, for whatever reason
            d.addBoth(self.disconnect)

    def sendData(self, data):
        self.transport.write(data)

    def connectionLost(self, reason):
        self.rpiVidProtocol.stopRecording()

    def startStreaming(self):
        # Open a raspivid process to begin streaming
        d = self.rpiVidProtocol.startRecording()
        # Return a deferred that is fired when the raspivid process is closed
        return d

    def stopStreaming(self):
        # Kill the raspivid process then close the connection
        d = maybeDeferred(self.rpiVidProtocol.stopRecording)
        d.addCallback(self.disconnect)
        return d

    def disconnect(self):
        self.transport.loseConnection()

class VideoStreamingFactory(protocol.ClientFactory):
    protocol = VideoStreamingProtocol
    vidParams = defaults
    _newProcessDeferred = None
    _connectors = {}
    _streamId = 0

    def initiateStreaming(self, params={}):
        self.vidParams = mergeDicts(self.vidParams, params)
        # Kill all pending connections
        self.disconnectConnectors()
        # Connect to the server to begin streaming
        self.connectToServer()
        return self.createNewProcessDeferred()

    def stopStreaming(self):
        # Alias, for more intuitive use
        self.disconnectConnectors()

    def createNewProcessDeferred(self):
        d = defer.Deferred()
        self._newProcessDeferred = d
        return d

    def disconnectConnectors(self):
        # disconnect does nothing to disconnected connections
        #  this also serves to clear the _connectors dict
        for key in self._connectors:
            c = self._connectors.pop(key)
            c.disconnect()

    def connectToServer(self):
        from twisted.internet import reactor
        c = reactor.connectTCP(self.vidParams['streamTo'], self.vidParams['streamPort'], self)
        _connectors[self._streamId] = c
        self._streamId += 1
        return c

    def buildProtocol(self, addr):
        p = protocol.ClientFactory.buildProtocol(self, addr)
        rvp = self.buildRpvProtocol(p)
        p.rpiVidProtocol = rvp
        return p

    def buildRpvProtocol(self, vsp):
        p = RaspiVidProtocol(self.vidParams, vsp)
        # Dereference the _newProcessDeferred.  This should be the deferred created by the 
        #  most recent call to initiateStream
        d, self._newProcessDeferred = self._newProcessDeferred, None
        # Create a deferred that will be fired when raspivid is closed and
        #  chain the _newProcessDeferred to it.  This allows
        #  the streaming flow control to have the last word.
        fireWhenProcessEnds = p.deferUntilProcessEnds()
        fireWhenProcessEnds.chainDeferred(d)
        return p

def main():
    from twisted.internet import reactor
    factory = VideoStreamingFactory()
    reactor.connectTCP('10.200.0.39', 5001, factory)
    reactor.run()

if __name__ == '__main__':
    main()
