# Controls for the raspberry pi camera
# Based on the rapsi* bash API
import subprocess as sp
import sys, re, time, os, socket, pprint
import datetime as dt

class Camera(object):

    defaultTLParams = {
            'interval': 10*1000,
            'duration': 7*24*60*60*1000,
            'cageName': socket.gethostname(),
            'width': 854,
            'height': 480,
            'timestamp': generateTimestamp(),
            'jpegQuality': 50
    }

    defaultVideoParams = {
            'cageName': socket.gethostname(),
            'duration': 60000,
            'stream': False,
            'streamTo': '10.117.33.13',
            'streamPort': 5001,
            'width': 1280,
            'height': 740,
            'fps': 30,
            'bitrate': 3000000,
            'timestamp': generateTimestamp(),
            'outputPath': None 
    }

    def __init__(self, logger=Logger()):
        self.activeTimelapse = None
        self.activeVideo = None
        # Set logger object
        self.logger = logger


    def startVideo(self, params):
        # Update Parameters
        vidParams = mergeDicts(self.defaultVideoParams, params)
        # Check for existing timelapse
        if self.activeTimelapse is not None:
            self.queueTimelapse(self.activeTimelapse, 5 + vidParams[duration]/1000)
            self.stopTimelapse()
        # Check for existing video
        if self.activeVideo is not None:
            print "Video Already in Progress!"
            pprint.pprint(self.activeVideo)
            return
        # Send command
        sendVideoCommand(vidParams)
        # Write to log
        self.logger.writeToLog('startVid')
        # Store start time
        vidParams['startTime'] = dt.datetime.now()
        # Store vid parameters
        self.activeVideo = Video(vidParams)

    def startTimelapse(self, params):
        # Update Parameters
        tlParams = mergeDicts(self.defaultTLParams, params)
        # Check for existing timelapse
        if self.activeTimelapse is not None:
            self.stopTimelapse()
        # Check for existing video
        if self.activeVideo is not None:
            self.queueTimelapse(tlParams, 5 + self.activeVideo.secondsRemaining())
        # Send command
        sentTimelapseCommand(tlParams)
        # Write to log
        self.logger.writeToLog(formatLogString('startTL','intervalLen',tlParams['interval'],'timestamp',tlParams['timestamp']))
        # Store start time
        tlParams['startTime'] = dt.datetime.now()
        # Store TL parameters
        self.activeTimelapse = Timelapse(tlParams)

    def stopVideo(self):
        if self.activeVideo is not None:
            self.activeVideo = None
        # Kill video processes
        sp.Popen('killall raspivid', shell=True)
        # Log
        self.logger.writeToLog("stopTL")

    def queueTimelapse(self, params, delay):
        # Schedule Timelapse
        from twisted.internet import reactor
        reactor.callLater(delay, self.startTimelapse, params)

    def stopTimelapse(self):
        if self.activeTimelapse is not None:
            self.activeTimelapse = None
        # Kill timelapse processes
        sp.Popen("killall raspistill", shell=True)
        # Log
        self.logger.writeToLog('stopVid')


class CameraState(dict):

    def secondsRemaining(self):
        d = dt.timedelta(milliseconds=self['duration'])
        e = self['startTime'] + d
        r = e - dt.datetime.now()
        return r.total_seconds()

class Timelapse(CameraState):
    pass


class Video(CameraState):
    pass


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
            if not self.logFile.closed
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


def sendTimelapseCommand(p):
    commandString = "raspistill -q {jpegQuality} -w {width} -h {height} " \
                    "-t {duration} -tl {interval} "\
                    "-o ~/timelapse/{cageName}_{dateTime}_%05d.jpg"
    commandString = commandString.format(**p)


def sendVideoCommand(p):
    # Generate Command String
    # Append on outputs based on params
    commandString = "raspivid -t {vTime} -fps 30 -cfx 128:128 " \
        "-b {bitrate} -w {width} -h {height}"
    if p['stream']:
        commandString += " -o - |"
        if p['outputPath'] is not None:
            commandString += " tee {outputPath} |"
        commandString += " nc {vIP} {vPort}"
    elif p['outputPath'] is not None:
        commandString += " -o {outputPath}.h264"

    if p['outputPath'] is not None:
        commandString += "; (MP4Box -add {outputPath}.h264 {outputPath}.mp4 -fps 30 &&" \
                    "rm {outputPath}.h264)"

    commandString = commandString.format(**videoParameters)


def formatLogString(*words):
    logStr = ""
    for word in words:
        logStr += "{} ".format(word)
    return logStr

def generateDateString():
    return dt.datetime.now().isoformat(' ')[:19]
    

def generateTimestamp():
    now = dt.datetime.now()
    return "{:04}{:02}{:02}_{:02}{:02}".format(
        now.year, now.month, now.day, now.hour, now.minute)

def mergeDicts(d1, d2):
    d = d1.copy()
    for key, value in d2:
        d[key] = value