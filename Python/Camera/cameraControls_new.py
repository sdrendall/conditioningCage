# Controls for the raspberry pi camera
import subprocess as sp
import raspividInterface as rpvI
import sys, re, time, os, socket, pprint, picamera
import datetime as dt
from twisted.internet.task import LoopingCall
from twisted.internet import defer


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
        self.activeVideo = None
        # Set logger object
        if logger is not None:
            self.logger = logger
        else:
            self.logger = Logger()

    def startVideo(self, params={}):
        vidParams = self.overwriteVideoDefaults(params)
        # Stop active videos
        if self.activeVideo is not None:
            # Try to start the video again once the active video has stopped
            self.activeVideo.firedOnRaspividReaping.addBoth(self.startVideo, vidParams)
            self.stopVideo()
            return
        # Videos supercede timelapses
        fireToResumeTL = suspendActiveTimelapse() # None if no active timelapse
        # Log the video command
        self.logger.writeToLog(formatLogString('startVid', 'timestamp', vidParams['dateTime']))
        # Handle video creation
        self._initiateVideo(vidParams, susTl=fireToResumeTL)

    def stopVideo(self):
        if self.activeVideo is not None:
            self._terminateActiveVideo()
        self.logger.writeToLog('stopVid')

    def suspendActiveTimelapse(self):
        if self.activeTimelapse is not None:
            tl, self.activeTimelapse = self.activeTimelapse, None
            tl.stop()
            d = defer.Deferred()
            d.addCallback(tl.start)
            return d
        else:
            return None

    def startTimelapse(self, params={}):
        tlParams = self.overwriteTimelapseDefaults(params)
        # If a video is playing, start timelapse when the video ends
        if self.activeVideo is not None:
            self.activeVideo.firedOnRaspividReaping.addBoth(self.startTimelapse, tlParams)
            return
        # If a timelapse is active, stop it
        if self.activeTimelapse is not None:
            self._terminateActiveTimelapse()
        # Log the timelapse start
        self.logger.writeToLog(formatLogString('startTL','intervalLen',timelapse['interval'],'timestamp',timelapse['dateTime']))
        self._initiateTimelapse(tlParams)

    def stopTimelapse(self):
        self._terminateActiveTimelapse
        self.logger.writeToLog('stopTL')

    def overwriteVideoDefaults(self, params):
        return mergeDicts(self.defaultVideoParams, params)

    def overwriteTimelapseDefaults(self, params):
        return mergeDicts(self.defaultTLParamsm, params)

    def _initiateTimelapse(self, params):
        tl = Timelapse(params)
        tl.start()
        self.activeTimelapse = tl

    def _terminateActiveTimelapse(self):
        if self.activeTimelapse is not None:
            tl, self.activeTimelapse = self.activeTimelapse, None
            tl.stop()


    def _initiateVideo(self, params, susTl=None):
        if params['stream']:
            v = Stream(params)
        else:
            v = Video(params)
        v.start()
        v.firedOnRaspividReaping.addCallback(self._derefActiveVideo)
        if susTl is not None:
            v.firedOnRaspividReaping.chainDeferred(susTl)
        self.activeVideo = v

    def _terminateActiveVideo(self):
        self.activeVideo.stop()
        self.activeVideo.firedOnRaspividReaping.addBoth(self._derefActiveVideo)

    def _derefActiveVideo(self):
        if self.activeVideo is not None:
            self.activeVideo = None


class CameraState(dict):

    def secondsRemaining(self):
        d = dt.timedelta(milliseconds=self['duration'])
        e = self['startTime'] + d
        r = e - dt.datetime.now()
        return r.total_seconds()

class Video(CameraState):
    firedOnRaspividReaping = None
    rpvProtocol = None

    def start(self):
        self.rpvProtocol = rpvI.RaspiVidProtocol(vidParams=self)
        d = self.rpvProtocol.startRecording()
        self.firedOnRaspividReaping = d

    def stop(self):
        self.rpvProtocol.stopRecording()


class Stream(Video):
    # Same factory for each Stream
    streamingFactory = rpvI.VideoStreamingFactory()

    def start(self):
        d = self.streamingFactory.initiateStreaming(self.copy()) #eww.. the streamingFactory references this arg.  Shouldn't pass self.
        self.firedOnRaspividReaping = d

    def stop(self):
        self.streamingFactory.stopStreaming()

class Timelapse(CameraState):

    camera = None
    
    def start(self):
        # Instantiate a new camera
        self._initializeCamera()
        # Start a Looping call of raspistills
        self['loopingCall'] = LoopingCall(self._captureImage)
        self['loopingCall'].start(self['interval']/1000)

    def stop(self):
        self._stopLoopingCall()
        self.camera.close()

    def _stopLoopingCall(self):
        if 'loopingCall' in self:
            if self['loopingCall'].running:
                self['loopingCall'].stop()

    def _initializeCamera(self):
        self.camera = picamera.PiCamera()
        self.camera.color_effects= (128, 128) # Grayscale
        self.camera.exif_tags['ImageUniqueID'] = "{}_{}".format(socket.gethostname(), self['dateTime'])

    def _captureImage(self):
        filename = "~/timelapse/{cageName}_{dateTime}_%05d.jpg" % self._getNextImageNumber()
        filename = filename.format(**self)
        filename = os.path.expanduser(filename)
        self.camera.capture(filename, resize=(self['width'],self['height']), quality=self['jpegQuality'])

    def _getNextImageNumber(self):
        if not 'picNo' in self:
            self['picNo'] = 0
        self['picNo'] += 1
        return self['picNo']