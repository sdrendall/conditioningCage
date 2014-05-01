# HCFC Cage Controller program

# This is the source and configuration file (someday they will be separate) for the RasPi Cage Client daemon.
# IT SHOULD NOT BE CALLED DIRECTLY FROM THE PYTHON INTERPRETER, THAT WILL NOT WORK
# Instead, the daemon can be started like so:
#   twistd CageController.py

import sys, re, time, datetime, os
import glob
import socket
import subprocess as sp
import cameraControls

from twisted.internet import protocol
from twisted.protocols import basic
from twisted.internet.serialport import SerialPort
from twisted.application import service

# IP Addresses to search for server and to stream video to respectively
IP_ADDR = "10.117.33.13" # ccServer is 10.117.33.13
IP_PORT = 1025
IP_ADDR_VIDEO = "10.117.33.13" # ccServer is 10.117.33.13
IP_PORT_VIDEO = 5001

# Determine IP address of controller
# (for deubgging, connect to Ofer's machine if on Warren Alpert subnet)
MY_IP = ""
try:
    print("trying ipconfig...")
    sys.stdout.flush()
    MY_IP = sp.check_output("/usr/sbin/ipconfig getifaddr en0", shell=True).strip()
    print("success")
    sys.stdout.flush()
except:
    try:
        print("trying ifconfig...")
        sys.stdout.flush()
        MY_IP = sp.check_output("/sbin/ifconfig eth0", shell=True)
        while not re.search(r"addr:([\.\d]*)", MY_IP):
            print("waiting for IP addr")
            sys.stdout.flush()
            time.sleep(5)
        MY_IP = re.search(r"addr:([\.\d]*)", MY_IP).group(1)
        print("success")
        sys.stdout.flush()
    except:
        pass
print("My IP: " + MY_IP)
sys.stdout.flush()
if re.match(r"10.119.",MY_IP):
    print("decided to connect to Ofer's machine!")
    sys.stdout.flush()
    IP_ADDR = "10.119.88.15" # Ofer's machine is 10.119.88.15
    IP_ADDR_VIDEO = "10.119.88.15" # Ofer's machine is 10.119.88.15


TEENSY_BAUD = 9600

global_teensy = None
global_server = None

current_parameters = {}


class ConditioningControlClient(basic.LineReceiver):

    cageName = socket.gethostname()
    logger = None
    camera = None

    def sendLine(self, line):
        "send line to stdout before transmitting, for debugging"
        print "Client: ", line
        basic.LineReceiver.sendLine(self, line)

    def connectionMade(self):
        self.sendLine("CageName: {}".format(self.cageName))
        self.teensy = self.factory.teensy
        global global_server
        global_server = self
        global IP_ADDR_VIDEO
        IP_ADDR_VIDEO = self.transport.getPeer()
        print IP_ADDR_VIDEO

    def lineReceived(self, line):
        global global_teensy
        print "Server:", line
        paramArray = line.split(":", 1)

        # Set Parameters
        if len(paramArray) > 1:
            pName = paramArray[0]
            pVal = paramArray[1]

            # save paramters locally:
            current_parameters[pName] = pVal

            # do something on RasPi with cerain parameters
            sendToTeensy = True;
            if pName == "Date":
                sendToTeensy = False
                if sys.platform == "linux2":
                    commandString = "sudo date -u {}".format(pVal)
                    sp.Popen(commandString,shell=True)
                    print "Setting date"
                    # print commandString
                else:
                    print "Not setting date (not running on a RasPi)"

            # send parameter off to Teensy:
            if sendToTeensy and global_teensy:
                global_teensy.sendLine("{}: {}".format(pName, pVal))
                print "sending param to teensy: <{}: {}>".format(pName, pVal)
            else:
                print "no global_teensy"

        # Run Command on Raspi
        elif len(line.strip())==1:
            command = line.strip()
            passCommandToTeensy = False

            if command=="F":
                # run Fear Conditioning
                passCommandToTeensy = True
                print(current_parameters["BlockDuration"])
                try:
                    delayTimes = map(int,current_parameters["BlockDuration"].split(","))
                    print(delayTimes)
                    # delayTimes = [current_parameters["fcDelay{}".format(x)] for x in range(1,11)]
                except:
                    delayTimes = [300000]
                    print("Couldn't compute delay times. Defaulting to 5 minutes.")

                fcDuration = sum(delayTimes) + 5*60*1000 # add extra five minutes after last shock
                savePath = os.path.expanduser("~/fc_videos/")
                if not os.path.exists(savePath):
                    os.mkdir(savePath)

                # Compile parameters
                videoParams = {
                    'duration': fcDuration,
                    'cageName': socket.gethostname(),
                    # possible width/heights: 1920x1080; 1280x720; 854x480
                    'width': 854,
                    'height': 480,
                    'bitrate': 1000000,
                    'dateTime': generateTimestamp(),
                }
                videoParams['outputPath'] =  savePath + "/{cageName}_FC_{dateTime}".format(**videoParams)

                # Start a video
                self.camera.startVideo(videoParams)
                

            elif command=="X":
                # end Fear Conditioning
                passCommandToTeensy = True
                self.camera.stopVideo()

                # Log Stop Time
                self.logger.writeToLog("stopFC")

            elif command=="V":
                # run non-FC video streaming
                global current_parameters
                videoParameters = {
                "streamTo": IP_ADDR_VIDEO,
                "streamPort": IP_PORT_VIDEO,
                'stream': True
                }
                self.camera.startVideo(videoParameters)

            elif command=="T":
                # run timelapse
                savePath = os.path.expanduser("~/timelapse/")
                if not os.path.exists(savePath):
                    os.mkdir(savePath)

                timelapseParams = {
                'cageName': socket.gethostname(),
                'dateTime': generateTimestamp()
                }
                self.camera.startTimelapse(timelapseParams)

            elif command=="E":
                self.camera.stopTimelapse()

            elif command=="S":
                passCommandToTeensy = True;
            elif command=="R":
                passCommandToTeensy = True;

            if passCommandToTeensy:
                if global_teensy:
                    global_teensy.sendLine(command)
                    print "sending command to teensy: <{}>".format(command)
                else:
                    print "no global_teensy"
            else:
                print "not passing command on to Teensy"


    def connectionLost(self, reason):
        print "connection lost"


class CageConnectionFactory(protocol.ClientFactory):

    protocol = ConditioningControlClient
    camera = None
    teensy = None

    def __init__(self, loggingService):
        # Reference the loggingService, this will be used by each client to write to the log
        self.loggingService = loggingService
        # Instantiate a camera object that will be used by CageClients to write to the camera
        self.camera = cameraControls.Camera(logger=self.loggingService)

    # link cage clients to their loggers when building
    def buildProtocol(self, addr):
        protocol = protocol.ClientFactory.buildProtocol(self, addr)
        protocol.logger = self.loggingService
        # Create a camera object to be used by the raspberry pi
        # Uses this module's writeToLog function to log 
        protocol.camera = self.camera
        return protocol

    def clientConnectionFailed(self, connector, reason):
        print "Connection failed!"
        self.reconnect()

    def clientConnectionLost(self, connector, reason):
        print "Connection lost!"
        self.reconnect()

    def reconnect(self):
        time.sleep(1)
        print "Reconnecting..."
        from twisted.internet import reactor
        reactor.connectTCP(IP_ADDR, IP_PORT, self)


class TeensyClient(basic.LineReceiver):

    logger = None

    def sendLine(self, line):
        print "To Teensy: ", line
        basic.LineReceiver.sendLine(self, line)

    def connectionMade(self):
        print "connected to Teensy!"
        self.factory.conditioningClientFactory.teensy = self
        global global_teensy
        global_teensy = self

    def lineReceived(self, line):
        print "From Teensy: " + line
        global global_server
        if global_server:
            global_server.sendLine(line)
        else:
            print "no global_server"
        if line.startswith("LOG "):
            data = line[4:] # strip "LOG "
            self.logger.writeToLog(data)

    def connectionLost(self, reason):
        print "connection to Teensy lost"
        global global_teensy
        global_teensy = None


class TeensyConnectionFactory(protocol.ClientFactory):
    protocol = TeensyClient

    def __init__(self, loggingService):
        self.loggingService = loggingService

    # link teensy clients to the logger when building
    def buildProtocol(self, addr):
        protocol = protocol.ClientFactory.buildProtocol(self, addr)
        protocol.logger = self.loggingService
        return protocol

    def clientConnectionFailed(self, connector, reason):
        print "Teensy Connection failed!"
        self.reconnect()

    def clientConnectionLost(self, connector, reason):
        print "Teensy Connection lost!"
        self.reconnect()

    def reconnect(self):
        time.sleep(1)
        print "Reconnecting to Teensy..."
        # TODO: what to put here to reconnect????

class TeensyService(service.Service):
    # A Service to handle the connection to the teensy

    def __init__(factory, device):
        self.factory = factory
        self.device = device
        self.port = None

    # The service is started when the twisted daemon runs.
    # The service builds a TeensyClient using the TeensyConnectionFactory
    # The service then opens a serial port
    def startService(self):
        service.Service.startService(self)
        if self.device:
            from twisted.internet import reactor
            protocol = self.factory.buildProtocol(None)
            self.port = SerialPort(protocol, self.device, reactor)

    # Stopping the service dereferences the SerialPort
    def stopService(self):
        service.Service.stopService(self)
        self.port = None


class LoggingService(service.Service):
    # A Service to handle logging
    # Opens a log file when started
    # Used to write to log files

    def __init__(self):
        self.logFile = None
        self.logDir = None
        self.ensureLogPath()

    def startService(self):
        service.Service.startService(self)
        self.openNewLogFile

    def stopService(self):
        service.Service.stopService(self)
        self.logFile.close()

    def ensureLogPath(self):
        self.logDir = os.path.expanduser("~/logs/")
        if not os.path.exists(self.logDir):
            os.mkdir(self.logDir)

    def openNewLogFile(self):
        if self.logFile:
            if not self.logFile.closed
                logFile.close()
        baseName = ConditioningControlClient.cageName
        dt = datetime.datetime.now()
        timestamp = generateTimestamp()
        self.logFile = open(os.path.join(logDir, "{}_{}.log".format(baseName, timestamp )), "w")
        
    # Function to log events
    def writeToLog(self, line):
        if not self.logFile:
            self.openLogFile()
        self.logFile.write('{} {}\n'.format(generateDateString(), line))
        self.logFile.flush()


# Functions to generate human-readable dates
def generateDateString():
    return datetime.datetime.now().isoformat(' ')[:19]

def generateTimestamp():
    now = datetime.datetime.now()
    return "{:04}{:02}{:02}_{:02}{:02}".format(
        now.year, now.month, now.day, now.hour, now.minute)

# Gets the teensy's addr
def getTeensyDev():
teensy = None
if sys.platform == "linux2":
    devices = glob.glob("/dev/serial/by-path/*usb*")
    if devices:
        teensy = devices[0]
# for debugging on a mac:
elif sys.platform == "darwin":
    devices = glob.glob('/dev/tty.usb*')
    if devices:
        teensy = devices[0]
return teensy

# This should all be in a .tac file.  For now its just going to sit here.

# get cage name from command line
if len(sys.argv)>1:
    cageName = sys.argv[1]
    # clean up cage name
    rx = re.compile('\W+')
    cageName = rx.sub(' ', sys.argv[1]).strip()
    if cageName:
        ConditioningControlClient.cageName = cageName

# Create a master service to hold all functional services
masterService = service.MultiService()

# set up a logging service
loggingService = LoggingService()

# setup service to connect to server
cageFactory = CageConnectionFactory(loggingService)
cageService = internet.TCPClient(IP_ADDR, IP_PORT, cageFactory)

# setup teensy service
teensyFactory = TeensyConnectionFactory(loggingService)
teensyDevice = getTeensyDev()
teensyService = TeensyService(teensyFactory, teensyDevice)

# Add cage and teensy services to the master service
loggingService.setServiceParent(masterService)
cageService.setServiceParent(masterService)
teensyService.setServiceParent(masterService)

# Create an application. This is used by the twistd fcn
application = service.Application("Cage Client")

# Attach the master service to the application
masterService.setServiceParent(application)
