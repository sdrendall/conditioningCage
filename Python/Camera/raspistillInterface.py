from twisted.internet import protocol, fdesc, error, defer, threads
import datetime as dt
import os, socket

def generateTimestamp():
    now = dt.datetime.now()
    return "{:04}{:02}{:02}_{:02}{:02}".format(
        now.year, now.month, now.day, now.hour, now.minute)

def mergeDicts(d1, d2):
    d = d1.copy()
    for key, value in d2.iteritems():
        d[key] = value
    return d    

defaults = {
    'interval': 10*1000,
    'duration': 5*24*60*60*1000,
    'cageName': socket.gethostname(),
    'width': 854,
    'height': 480,
    'dateTime': generateTimestamp(),
    'jpegQuality': 50
}

end_of_image = eoi = '\xff\xd9'
start_of_image = soi = '\xff\xd8\xff\xe1'

class RaspiStillTimelapseProtocol(protocol.ProcessProtocol):
    _currImageNumber = 0
    _imageBuffer = ''

    def __init__(self, tlParams={}):
        tlParams = mergeDicts(defaults, tlParams)
        # Set the arguments to call raspistill with
        self.setTlArgs(tlParams)
        self.tlParams = tlParams
        # Empty list for deffereds fired on raspistill reaping
        self.fireWhenProcessEnds = []

    def outReceived(self, data):
        # Write incoming data to the next file in the timelapse seri
        #self.writeToNextImageFile(data)
        print 'Received %d bytes!' % len(data)
        self._detectSOI(data)

    def errReceived(self, data):
        print '[err] raspistill:'
        print data

    def processEnded(self, status):
        self.fireFireWhenProcessEndsDeferreds()

    def setTlArgs(self, params):
        tlArgString = 'raspistill --timelapse {interval} -t {duration} -w {width} -h {height} -q {jpegQuality} -o -'.format(**params)
        self.tlArgs = tlArgString.split()

    def fireFireWhenProcessEndsDeferreds(self):
        # Fire all deferreds in fireWhenProcessEnds
        while self.fireWhenProcessEnds:
            d = self.fireWhenProcessEnds.pop()
            try:
                d.callback(None)
            # This will eventually be called when
            #  the parent factory's currentProcessDeferred 
            #  is cancelled
            except defer.AlreadyCalledError:
                pass

    def deferUntilProcessEnds(self):
        d = defer.Deferred()
        self.fireWhenProcessEnds.append(d)
        return d

    def startTimelapse(self):
        from twisted.internet import reactor
        reactor.spawnProcess(self, '/usr/bin/raspistill', args=self.tlArgs, env=os.environ)
        return self.deferUntilProcessEnds()

    # Call with maybeDeferred
    def stopTimelapse(self):
        try:
            self.transport.signalProcess('KILL')
        except error.ProcessExitedAlready:
            return
        return self.deferUntilProcessEnds()

    def writeToNextImageFile(self, data):
        f = self._openNextImageFile()
        d = self._writeToImageFile(f, data)
        d.addCallback(self._closeImageFile, f)
        # Errback to write err to log?

    def _openNextImageFile(self):
        f = open(self._generateNextImageFileName(), 'w')
        fdesc.setNonBlocking(f.fileno())
        return f

    def _writeToImageFile(self, f, data):
        fd = f.fileno()
        return threads.deferToThread(fdesc.writeToFD, fd, data)

    def _closeImageFile(self, bytes, f):
        # Called with the results of fdesc.writeToFD
        print "Wrote {} bytes to {}!".format(bytes, f.name)
        f.close()

    def _generateNextImageFileName(self):
        filename = "~/timelapse/{cageName}_{dateTime}_%05d.jpg" % self._getNextImageNumber()
        filename = filename.format(**self.tlParams)
        return os.path.expanduser(filename)

    def _getNextImageNumber(self):
        self._currImageNumber += 1
        return self._currImageNumber

    def _detectEOI(self, data):
        # Find EOI
        ind = data.find(eoi)
        if ind >= 0:
            # add to buffer
            self._imageBuffer += data[:ind + len(eoi)]
            print 'Found EOF!'
            print '%d bytes received since last EOI' % len(self._imageBuffer)
            print 'writing to file...'
            self.writeToNextImageFile(self._imageBuffer)
            # reset buffer
            self._imageBuffer = data[ind + len(eoi):]
        else:
            self._imageBuffer += data

    def _detectSOI(self, data):
        ind = data.find(soi)
        if ind >= 0:
            # add to buffer
            self._imageBuffer += data[:ind]
            print 'Found SOI!'
            bytesInBuffer = len(self._imageBuffer)
            print '%d bytes received since last SOI' % bytesInBuffer
            if bytesInBuffer > 0:
                print 'writing to file...'
                self.writeToNextImageFile(self._imageBuffer)
            # reset buffer
            self._imageBuffer = data[ind:]
        else:
            self._imageBuffer += data




def main():
    from twisted.internet import reactor
    p = {'interval': 1000}
    tlProc = RaspiStillTimelapseProtocol(p)
    reactor.callWhenRunning(tlProc.startTimelapse)
    reactor.callWhenRunning(reactor.callLater, 5, tlProc.stopTimelapse)
    reactor.callWhenRunning(reactor.callLater, 8, tlProc.startTimelapse)
    reactor.callWhenRunning(reactor.callLater, 12, tlProc.stopTimelapse)
    reactor.run()

if __name__ == '__main__':
    main()
