#! /usr/bin/python

# HCFC Cage Controller program

"""
The controller for a home conditioning cage.
It is meant to run on a RasPi and to connect to a Teensy on the USB port.
"""

import sys, re, time, datetime, os
import glob
import socket
import subprocess as sp

from twisted.internet import reactor, protocol
from twisted.protocols import basic
from twisted.internet.serialport import SerialPort

# IP Addresses to search for server and to stream video to respectively
IP_ADDR = "ccws.med.harvard.edu" # HCC Laptop is 192.168.1.4
IP_PORT = 1025
IP_ADDR_VIDEO = "ccws.med.harvard.edu" # HCC Laptop is 192.168.1.4
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
if re.match(r"10.11.176",MY_IP):
    print("decided to connect to Ofer's machine!")
    sys.stdout.flush()
    IP_ADDR = "10.11.176.190" # Ofer's machine is 10.11.176.190
    IP_ADDR_VIDEO = "10.11.176.190" # Ofer's machine is 10.11.176.190


TEENSY_BAUD = 9600
if sys.platform == "linux2":
    TEENSY_DEV = glob.glob("/dev/serial/by-path/*usb*")[0]
# for debugging on a mac:
elif sys.platform == "darwin":
    devices = glob.glob('/dev/tty.usb*')
    TEENSY_DEV = devices[0]

global_teensy = None
global_server = None

current_parameters = {}


class ConditioningControlClient(basic.LineReceiver):

    cageName = socket.gethostname()
    currentVideoFileName = ""

    def sendLine(self, line):
        "send line to stdout before transmitting, for debugging"
        print "Client: ", line
        basic.LineReceiver.sendLine(self, line)

    def connectionMade(self):
        self.sendLine("CageName: {}".format(self.cageName))
        self.teensy = self.factory.teensy
        global global_server
        global_server = self

    def lineReceived(self, line):
        global global_teensy
        print "Server:", line
        paramArray = line.split(":",1)

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
                commandString = "sudo date -u {}".format(pVal)
                sp.Popen(commandString,shell=True)
                print "Setting date:"
                print commandString

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
                dir = os.path.expanduser("~/fc_videos/")
                if not os.path.exists(dir):
                    os.mkdir(dir)
                videoParams = {}
                videoParams['duration'] = fcDuration
                videoParams['cageName'] = socket.gethostname()
                # possible width/heights: 1920x1080; 1280x720; 854x480
                videoParams['width'] = 854
                videoParams['height'] = 480
                videoParams['bitrate'] = 1000000
                dt = datetime.datetime.now()
                videoParams['dateTime'] = "{:04}{:02}{:02}_{:02}{:02}".format(
                    dt.year, dt.month, dt.day, dt.hour, dt.minute)
                videoBaseName = "~/fc_videos/{cageName}_FC_{dateTime}".format(**videoParams)
                videoParams['fileBase'] = videoBaseName
                self.currentVideoFileName = videoBaseName
                commandString = "raspivid -w {width} -h {height} " \
                    "-n -b {bitrate} -fps 30 -cfx 128:128 " \
                    "-t {duration} -o {fileBase}.h264; " \
                    "(MP4Box -add {fileBase}.h264 {fileBase}.mp4 -fps 30 && " \
                    "rm {fileBase}.h264)"
                commandString = commandString.format(**videoParams)
                print(commandString)
                sp.Popen(commandString, shell=True)
                # Log Start Time
                logEvent("startFC")

            elif command=="X":
                # end Fear Conditioning
                passCommandToTeensy = True
                sp.Popen("killall raspivid", shell=True)
                # fileBaseName = self.currentVideoFileName
                # commandString = "MP4Box -add {}.h264 {}.mp4; " \
                #     "rm {}.h264".format(fileBaseName, fileBaseName, fileBaseName)
                # sp.Popen(commandString, shell=True)
                
                # Log Stop Time
                logEvent("stopFC")

            elif command=="V":
                # run non-FC video streaming
                global current_parameters
                videoParameters = {}
                videoParameters["vTime"] = 60000 # TODO make this a user parameter
                videoParameters["vIP"] = IP_ADDR_VIDEO
                videoParameters["vPort"] = IP_PORT_VIDEO
                commandString = "raspivid -t {vTime} -fps 30 -cfx 128:128 " \
                    "-b 3000000 -w 1280 -h 740 -o - | nc {vIP} {vPort}"
                commandString = commandString.format(**videoParameters)
                sp.Popen(commandString, shell=True)
                # Log Video stream start -- Inaccurate!!
                logEvent("startVid")

            elif command=="T":
                # run timelapse
                dir = os.path.expanduser("~/timelapse/")
                if not os.path.exists(dir):
                    os.mkdir(dir)
                timelapseParams = {}
                timelapseParams['interval'] = 45*1000
                timelapseParams['duration'] = 4*24*60*60*1000
                timelapseParams['cageName'] = socket.gethostname()
                # possible width/heights: 1280x720; 854x480
                timelapseParams['width'] = 854
                timelapseParams['height'] = 480
                dt = datetime.datetime.now()
                timelapseParams['dateTime'] = \
                    "{:04}{:02}{:02}_{:02}{:02}".format(
                        dt.year, dt.month, dt.day, dt.hour, dt.minute)
                commandString = "raspistill -q 50 -w {width} -h {height} " \
                    "-t {duration} -tl {interval} "\
                    "-o ~/timelapse/{cageName}_{dateTime}_%05d.jpg"
                commandString = commandString.format(**timelapseParams)
                print(commandString)
                sp.Popen(commandString, shell=True)
                # Log start time
                logEvent("startTL " + "intervalLen " + str(timelapseParams['interval']))
            

            elif command=="E":
                # end timelapse
                sp.Popen("killall raspistill", shell=True)
                # Log time
                logEvent("stopTL")

            if global_teensy and passCommandToTeensy:
                global_teensy.sendLine(command)
                print "sending command to teensy: <{}>".format(command)
            else:
                print "no global_teensy"


    def connectionLost(self, reason):
        print "connection lost"


class CageConnectionFactory(protocol.ClientFactory):
    protocol = ConditioningControlClient
    teensy = None

    def clientConnectionFailed(self, connector, reason):
        print "Connection failed!"
        # reactor.stop()
        self.reconnect()

    def clientConnectionLost(self, connector, reason):
        print "Connection lost!"
        # reactor.stop()
        self.reconnect()

    def reconnect(self):
        time.sleep(1)
        print "Reconnecting..."
        reactor.connectTCP(IP_ADDR, IP_PORT, self)


class TeensyClient(basic.LineReceiver):

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
            logEvent(data)

    def connectionLost(self, reason):
        print "connection to Teensy lost"


class TeensyConnectionFactory(protocol.ClientFactory):
    protocol = TeensyClient

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
        # reactor.connectTCP(IP_ADDR, IP_PORT, self)



logFile = None
def openNewLogFile():
    global logFile
    if logFile:
        logFile.close()
    dir = os.path.expanduser("~/logs/")
    if not os.path.exists(dir):
        os.mkdir(dir)
    baseName = ConditioningControlClient.cageName
    # fileNum = 1;
    # while os.path.exists(os.path.join(dir, "{}_{}.log".format(baseName, fileNum))):
    #     fileNum += 1
    # logFile = open(os.path.join(dir, "{}_{}.log".format(baseName, fileNum)), "w")
    dt = datetime.datetime.now()
    dateString = "{:04}{:02}{:02}_{:02}{:02}".format(
                    dt.year, dt.month, dt.day, dt.hour, dt.minute)
    logFile = open(os.path.join(dir, "{}_{}.log".format(baseName, dateString)), "w")
    
 
# Function to log events
def logEvent(line):
	global logFile
	if logFile:	
		dateString = datetime.datetime.now().isoformat(' ')[:19]
		logFile.write("{} {}\n".format(dateString, line))
		logFile.flush()
	else:
		openNewLogFile()
		logEvent(line)


# this connects the protocol to a server runing on port 1025
def main():

    # get cage name from command line
    if len(sys.argv)>1:
        cageName = sys.argv[1]
        # clean up cage name
        rx = re.compile('\W+')
        cageName = rx.sub(' ', sys.argv[1]).strip()
        if cageName:
            ConditioningControlClient.cageName = cageName


    # setup connection to server
    f = CageConnectionFactory()
    reactor.connectTCP(IP_ADDR, IP_PORT, f)

    # setup connection to teensy
    f2 = TeensyConnectionFactory()
    f2.conditioningClientFactory = f;
    protocol = f2.buildProtocol(None)
    deviceName = TEENSY_DEV
    port = SerialPort(protocol, deviceName, reactor)

    f.teensyFactory = f2

    openNewLogFile()

    reactor.run()

# this only runs if the module was *not* imported
if __name__ == '__main__':
    main()


