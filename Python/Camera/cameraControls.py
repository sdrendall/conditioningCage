# Controls for the raspberry pi camera
import subprocess as sp
import raspividInterface as rpvI
import sys, re, time, os, socket, pprint, picamera
import datetime as dt
from twisted.internet.task import LoopingCall


# Helper functions
def formatLogString(*words):
    logStr = "{} " * len(words)
    logStr = logStr.format(*words)
    return logStr[:(len(logStr) - 1)]

def generateDateString():
    return dt.datetime.now().isoformat(' ')[:19]

def generateTimestamp():
    now = dt.datetime.now()
    return "{:04}{:02}{:02}_{:02}{:02}".format(
        now.year, now.month, now.day, now.hour, now.minute)

def mergeDicts(d1, d2):
    d = d1.copy()
    for key, value in d2.iteritems():
        d[key] = value
    return d

# Logging class - in lieu of a LoggingService
class Logger(object):
    # An object to handle logging
    # Used to write to log files
      
    def __init__(self):
        self.logFile = None
        self.logDir = None
        self.ensureLogPath()
        self.openNewLogFile()

    def ensureLogPath(self):
        self.logDir = os.path.expanduser("~/logs/")
        if not os.path.exists(self.logDir):
            os.mkdir(self.logDir)

    def openNewLogFile(self):
        if self.logFile:
            if not self.logFile.closed:
                logFile.close()
        filename = "cameraLog_" + generateTimestamp() + '.log'
        self.logFile = open(os.path.join(self.logDir, filename), "w")

    def closeLogFile(self):
        self.logFile.close()
        
    # Function to log events
    def writeToLog(self, line):
        if not self.logFile:
            self.openLogFile()
        self.logFile.write('{} {}\n'.format(generateDateString(), line))
        self.logFile.flush()


# The main event
class Camera(object):
    streamingFactory = raspividInterface.VideoStreamingFactory()

    defaultTLParams = {
            'interval': 10*1000,
            'duration': 5*24*60*60*1000,
            'cageName': socket.gethostname(),
            'width': 854,
            'height': 480,
            'dateTime': generateTimestamp(),
            'jpegQuality': 50
    }

    defaultVideoParams = {
            'cageName': socket.gethostname(),
            'duration': 0,
            'stream': False,
            'streamTo': '10.117.33.13',
            'streamPort': 5001,
            'width': 1280,
            'height': 740,
            'fps': 30,
            'bitrate': 3000000,
            'dateTime': generateTimestamp(),
            'outputPath': None
    }

    def __init__(self, logger=None):
        self.activeTimelapse = None
        self.deferredTimelapse = None
        self.activeVideo = None
        # Set logger object
        if logger is not None:
            self.logger = logger
        else:
            self.logger = Logger()


    def startVideo(self, params):
        from twisted.internet import reactor
        # Update Parameters
        vidParams = mergeDicts(self.defaultVideoParams, params)
        # Check for existing timelapse
        if self.activeTimelapse is not None:
            self.suspendTimelapse(self.activeTimelapse, 5 + vidParams['duration']/1000)
        # Check for existing video
        if self.activeVideo is not None:
            print "Video Already in Progress!"
            pprint.pprint(self.activeVideo)
            print "Killing Active Video!"
            self.stopVideo()
            # Wait a second to allow camera resources to become available
            reactor.callLater(1, self.startVideo, params)
            return
        # Send command
        sendVideoCommand(vidParams)
        # Write to log
        self.logger.writeToLog(formatLogString('startVid', 'timestamp', vidParams['dateTime']))
        # Store start time
        vidParams['startTime'] = dt.datetime.now()
        # Stop the video at the end of its duration
        vidParams['deferredStop'] = reactor.callLater(vidParams['duration']/1000, self.stopVideo)
        # Store vid parameters
        self.activeVideo = Video(vidParams)

    def startTimelapse(self, params):
        # Update Parameters
        tlParams = mergeDicts(self.defaultTLParams, params)
        # Check for and stop existing timelapses
        if self.activeTimelapse is not None:
            self.stopTimelapse()
        # Throw out a queued timelapse if another one is to be started
        if self.deferredTimelapse is not None:
            self.deferredTimelapse.cancelDeferredStart()
            self.deferredTimelapse = None
        # Create the timelapse
        timelapse = Timelapse(tlParams)
        # Check for existing video
        if self.activeVideo is not None:
            # if a video is running, start the timelapse when it finishes
            vidTimeRemaining = self.activeVideo.secondsRemaining()
            if vidTimeRemaining > 0:
                self.suspendTimelapse(timelapse, vidTimeRemaining + 1)
                return
            else:
                self.stopVideo()
        # Start timelapse
        timelapse.start()
        # Write to log
        self.logger.writeToLog(formatLogString('startTL','intervalLen',timelapse['interval'],'timestamp',timelapse['dateTime']))
        # Store start time
        timelapse['startTime'] = dt.datetime.now()
        # Update activeTimelapse
        self.activeTimelapse = timelapse

    def stopVideo(self):
        if self.activeVideo is not None:
            try:
                self.activeVideo['deferredStop'].cancel()
            except AssertionError, e:
                print e
            self.activeVideo = None
        # Kill video processes
        sp.Popen('killall raspivid', shell=True)
        # Log
        self.logger.writeToLog("stopVid")

        # Restart deferred timelapses
        if self.deferredTimelapse is not None:
            self.restartSuspendedTimelapse()

    def suspendTimelapse(self, timelapse, delay):
        # Stop the active timelapse
        if self.activeTimelapse is not None:
            self.stopTimelapse()
        # Overwrite current deferredTimelapse
        if self.deferredTimelapse is not None:
            self.deferredTimelapse.cancelDeferredStart()
        # Kill queued starts and stops
        timelapse.cancelDeferredStart()
        timelapse.cancelDeferredStop()
        # Schedule Timelapse
        self.deferredTimelapse = timelapse
        self.deferredTimelapse.queue(delay)

    def restartSuspendedTimelapse(self):
        # Return if there isn't a deferred timelapse
        if self.deferredTimelapse is None:
            return
        # Stop ongoing timelapse
        if self.activeTimelapse is not None:
            self.stopTimelapse()
        # Queue the timelapse (give the camera hardware time to free up)
        self.deferredTimelapse.queue(1) ### TODO: Return a deferred
        # rerefrence deferredTimelapse as activeTimelapse
        self.activeTimelapse, self.deferredTimelapse = self.deferredTimelapse, None

    def stopTimelapse(self):
        if self.activeTimelapse is not None:
            self.activeTimelapse.stop()
            self.activeTimelapse = None
        # Log
        self.logger.writeToLog('stopTL')


class CameraState(dict):

    def secondsRemaining(self):
        d = dt.timedelta(milliseconds=self['duration'])
        e = self['startTime'] + d
        r = e - dt.datetime.now()
        return r.total_seconds()

class Timelapse(CameraState):

    camera = None
    
    def start(self):
        # Instantiate a new camera
        self.initializeCamera()
        # Remove queued starts or stops
        self.cancelDeferredStart()
        # Start a Looping call of raspistills
        self['loopingCall'] = LoopingCall(self.captureImage)
        self['loopingCall'].start(self['interval']/1000)
        # Schedule an ending
        from twisted.internet import reactor
        self['deferredStop'] = reactor.callLater(self['duration'], self.stop)

    def stop(self):
        # Cancel the deferredStop if it's running
        self.cancelDeferredStop()
        # Stop the Timelapse
        self.stopLoopingCall()
        # Cancel deferredStart -- until Camera.restartSuspendedTimelapse returns a deferred
        self.cancelDeferredStart()
        # Close the camera
        self.camera.close()

    def suspend(self):
        pass

    def queue(self, delay):
        # queues a timelapse to be started after delay
        # stop timelapse, and cancel all callLaters
        self.stop()
        from twisted.internet import reactor
        self['deferredStart'] = reactor.callLater(delay, self.start)

    def stopLoopingCall(self):
        if 'loopingCall' in self:
            if self['loopingCall'].running:
                self['loopingCall'].stop()

    def cancelDeferredStop(self):
        if 'deferredStop' in self:
            if self['deferredStop'].active():
                self['deferredStop'].cancel()
            del self['deferredStop']

    def cancelDeferredStart(self):
        if 'deferredStart' in self:
            if self['deferredStart'].active():
                self['deferredStart'].cancel()
            del self['deferredStart']

    def initializeCamera(self):
        self.camera = picamera.PiCamera()
        self.camera.color_effects= (128, 128) # Grayscale
        self.camera.exif_tags['ImageUniqueID'] = "{}_{}".format(socket.gethostname(), self['dateTime'])

    def captureImage(self):
        filename = "~/timelapse/{cageName}_{dateTime}_%05d.jpg" % self.getNextImageNumber()
        filename = filename.format(**self)
        filename = os.path.expanduser(filename)
        self.camera.capture(filename, resize=(self['width'],self['height']), quality=self['jpegQuality'])

    def getNextImageNumber(self):
        if not 'picNo' in self:
            self['picNo'] = 0
        self['picNo'] += 1
        return self['picNo']

class Video(CameraState):
    pass

def sendVideoCommand(p):
    # Generate Command String
    # Append on outputs based on params
    commandString = "raspivid -t {duration} -fps 30 -cfx 128:128 " \
        "-b {bitrate} -w {width} -h {height}"
    if p['stream']:
        commandString += " -o - |"
        if p['outputPath'] is not None:
            commandString += " tee {outputPath} |"
        commandString += " nc {streamTo} {streamPort}"
    elif p['outputPath'] is not None:
        commandString += " -o {outputPath}.h264"

    if p['outputPath'] is not None:
        commandString += "; (MP4Box -add {outputPath}.h264 {outputPath}.mp4 -fps 30 &&" \
                    "rm {outputPath}.h264)"

    commandString = commandString.format(**p)
    print commandString
    # Send off the start command
    sp.Popen(commandString, shell=True)

def raspikill():
    sp.Popen('killall raspivid', shell=True)