#! /usr/bin/python

# Master script for nanny cams

"""
Control script for nanny cams.
Modeled after the CageController.py script
"""

import sys, re, time, datetime, os
import glob
import socket
import subprocess as sp

from twisted.internet import reactor, protocol
from twisted.protocols import basic

from Camera import cameraControls

ccServer = "10.117.33.13"
betty = '10.200.0.42'

# IP Addresses to search for server and to stream video to respectively
IP_ADDR = ccServer # ccServer is 10.117.33.13
IP_PORT = 1025
IP_ADDR_VIDEO = IP_ADDR # ccServer is 10.117.33.13
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

defaultTimelapseParams = {
    'interval': .1*60*1000,
    'duration': 7*24*60*60*1000,
    'cageName': socket.gethostname(),
    'width': 854,
    'height': 480}
defaultVideoParams = {
    'duration': 0,
    'stream': True,
    'streamTo': IP_ADDR_VIDEO,
    'streamPort': IP_PORT_VIDEO}

# Initialize Camera
camera = cameraControls.Camera()

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
                camera.startVideo(defaultVideoParams)
            
            elif command == "T":
            # start timelapse
                camera.startTimelapse(defaultTimelapseParams)
            
            elif command == "E":
            # end timelapse
                camera.stopTimelapse()
            
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
    camera.startTimelapse(defaultTimelapseParams)

    reactor.run()

# this only runs if the module was *not* imported
if __name__ == '__main__':
    main()
    
