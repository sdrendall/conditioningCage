#! /usr/bin/python

# Master script for nanny cams

"""
Control script for nanny cams.
Modeled after the CageController.py script
Connects to a master server, enables a passive timelapse and live video streaming
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
# try different potential commands to retrieve the IP address
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


# ------ Camera Class ---- To handle camera actions -------------------
class rasPiCam(object):
    
    # Initialize defaults for timelapse and video calls
    # TODO: Allow for timelapse to run for an unbounded length of time
    # EDITED DEFAULTS FOR DRY RUN!!
    def __init__(self):
        self.timelapseParams = {
        'interval': 10*60*1000,
        'duration': 7*24*60*60*1000,
        'cageName': socket.gethostname(),
        'width': 854,
        'height': 480}
        self.videoParams = {
        'duration': 60000,
        'targetIP': IP_ADDR_VIDEO,
        'targetPort': IP_PORT_VIDEO}
        self.state = "inactive"
        
    def startVideo(self):
        if self.state == "timelapse":
            # Stop current timelapse
            self.stopTimelapse()
            ## ALLOW FOR KILL COMMAND TO RESOLVE -- FIX THIS SOON
            time.sleep(3)
            # Queue next timelapse 
            from twisted.internet import reactor
            reactor.callLater(self.videoParams['duration'] + 10000, self.startTimelapse)
        # Start Video
        commandString = "raspivid -vf -t {duration} -fps 30 -cfx 128:128 " \
                    "-b 3000000 -w 1280 -h 740 -o - | nc {targetIP} {targetPort}"
        commandString = commandString.format(**self.videoParams)
        sp.Popen(commandString, shell=True)
        # Change state
        self.state = "video"
        # Log Video stream start -- Inaccurate!!
        logEvent("startVid")
    
    # Fcn to start a timelapse -- delay arg is in milliseconds
    def startTimelapse(self):
        # Get date and time, for naming purposes
        dt = datetime.datetime.now()
        self.timelapseParams['dateTime'] = \
            "{:04}{:02}{:02}_{:02}{:02}".\
            format(dt.year, dt.month, dt.day, dt.hour, dt.minute)
        # Construct raspistill call from input parameters
        commandString = "raspistill -vf -q 50 -w {width} -h {height} " \
            "-t {duration} -tl {interval} "\
            "-o ~/timelapse/{cageName}_{dateTime}_%05d.jpg;"
        commandString = commandString.format(**self.timelapseParams)
        # Open timelapse subprocess
        sp.Popen(commandString, shell=True)
        # Change state
        self.state = "timelapse"
        # Log start time
        # TODO: Fix logging w/ delay
        logEvent("startTL intervalLen {}".format(self.timelapseParams['interval']))
    def stopTimelapse(self):
        # end timelapse
        sp.Popen("killall raspistill", shell=True)
        # Change state
        self.state = "inactive"
        # Log time
        logEvent("stopTL")

# Initialize Camera
piCam = rasPiCam()

# ---- Main Client Class to Handle Communication w/ server ----
# Not sure what this does yet
global_server = None

# Initialize dictionary to store parameters
current_parameters = {}

class nannyCamControlClient(basic.LineReceiver):
    
    cageName = socket.gethostname()
    currentVideoFileName = ""
    
    # Send line function -- self explanatory    
    def sendLine(self, line):
        "send line to stdout before transmitting, for debugging"
        print "Client: ", line
        basic.LineReceiver.sendLine(self, line)
    
    # Runs when a connection is made w/ the server
    def connectionMade(self):
        self.sendLine("CageName: {}".format(self.cageName))
        global global_server
        global_server = self

    # Runs when the client recieves a line from the server
    def lineReceived(self, line):
        # Print line to stdout -- for debugging
        print "Server:", line
        
        # Split line at :, used to delim a parameter's name and value
        paramArray = line.split(":",1)

        # Set Parameters -- denoted by :
        # In this case, we only care about the Date
        if len(paramArray) > 1:
            # Store name and value
            pName = paramArray[0]
            pVal = paramArray[1]

            # Store parameter locally:
            current_parameters[pName] = pVal
            
            # Set Date if recieved
            if pName == "Date":
                commandString = "sudo date -u {}".format(pVal)
                sp.Popen(commandString,shell=True)
                print "Setting date:"
                print commandString
                
        # Only valid syntax for a line are two : delimited values or a single character
        # Single characters correspond to commands w/o values
        elif len(line.strip()) == 1:
            command = line.strip()
            
            if command == "V":
            # stream video
                piCam.startVideo()
            
            elif command == "T":
            # start timelapse
                piCam.startTimelapse()
            
            elif command == "E":
            # end timelapse
                piCam.stopTimelapse()
            
        def connectionLost(self, reason):
            print "connection lost"


# ----------- Handle Log Files ------------------
logFile = None
def openNewLogFile():
    # init logFile
    global logFile
    # close current log, if open
    if logFile:
        logFile.close()
    # init log path, mkdir if !exist
    dir = os.path.expanduser("~/logs/")
    if not os.path.exists(dir):
        os.mkdir(dir)
    # build filename
    baseName = nannyCamControlClient.cageName
    dt = datetime.datetime.now()
    dateString = "{:04}{:02}{:02}_{:02}{:02}".\
        format(dt.year, dt.month, dt.day, dt.hour, dt.minute)
    # open logFile
    logFile = open(os.path.join(dir, "{}_{}.log".format(baseName, dateString)), "w")

# Function to log events
def logEvent(line):
	global logFile
	# write to logFile if it's there, otherwise open one first
	if logFile:	
		dateString = datetime.datetime.now().isoformat(' ')[:19]
		logFile.write("{} {}\n".format(dateString, line))
		logFile.flush()
	else:
		openNewLogFile()
		logEvent(line)
		
# --- CageConnectionFactory Class --- Handles Connection w/ server
class nannyCamConnectionFactory(protocol.ClientFactory):
    protocol = nannyCamControlClient
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



# ---------------------- Main Fcn --------------------------
# this connects the protocol to a server runing on port 1025
def main():

    # get cage name from command line
    if len(sys.argv)>1:
        cageName = sys.argv[1]
        # clean up cage name
        rx = re.compile('\W+')
        cageName = rx.sub(' ', sys.argv[1]).strip()
        if cageName:
            nannyCamControlClient.cageName = cageName

    # setup connection to server
    f = nannyCamConnectionFactory()
    reactor.connectTCP(IP_ADDR, IP_PORT, f)

    openNewLogFile()
    piCam.startTimelapse()

    reactor.run()

# this only runs if the module was *not* imported
if __name__ == '__main__':
    main()
    
