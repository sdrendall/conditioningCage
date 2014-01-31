# HCFC server program

from twisted.internet import reactor, protocol
from twisted.protocols import basic
import subprocess as sp

IP_PORT = 1025

# Initialize current_parameters dict
current_parameters = {}

class PiCoordinationProtocol(basic.LineReceiver):
    nextID = 1

    def __init__(self, factory):
        self.factory = factory
        self.cageName = ""
        self.cageIP = None
        self.id = 0

    def connectionMade(self):
        print "added client"
        self.factory.clients.add(self)
        self.cageIP = self.transport.getPeer()

    def connectionLost(self, reason):
        print "removed client"
        print reason
        self.factory.clients.remove(self)
        self.factory.interface.removeCage(self.id)

    def lineReceived(self, line):
        print "line received : {}".format(line)
        #self.factory.sendLineToAll("<{}> {}".format(self.transport.getHost(), line))
        self.parseLine(line)

    def parseLine(self, line):
        if line.startswith("CageName: "):
            # this should be the first communication upon connecting to a cage
            self.cageName = line[len("CageName: "):]
            if self.id == 0:
                self.id = PiCoordinationProtocol.nextID
                PiCoordinationProtocol.nextID += 1
                # self.factory.interface.addCage(self.id, self.cageName)
                self.factory.interface.addCage(self.id, "{} ({})".format(self.cageName, self.cageIP.host))
            else:
                # should never get here
                pass
            # set time on cage
            uDate = sp.check_output('date "+%m%d%H%M%Y.%S"', shell=True)
            self.factory.setParameter("Date", uDate, cageId=self.id)

        elif line.startswith("[DEBUG] "):
            # send debug info straight to stdout
            print "{} {}".format(self.id, line)

        elif line.startswith("LOG "):
            print "{} {}".format(self.id, line)

        paramArray = line.split(":",1)

        # Set Parameters
        if len(paramArray) > 1:
            pName = paramArray[0]
            pVal = paramArray[1]

            # save paramters locally:
            current_parameters[pName] = pVal

class PiCoordinationFactory(protocol.Factory):
    def __init__(self, interface):
        self.clients = set()
        self.interface = interface

    def buildProtocol(self, addr):
        return PiCoordinationProtocol(self)

    def sendLineToAll(self, line):
        self.interface.displayText("Sending to all cages: "+line)
        for c in self.clients:
            c.sendLine(line)

    def sendLineToOne(self, id, line):
        for c in self.clients:
            if c.id == id:
                self.interface.displayText(
                    "Sending to '{}': {}".format(c.cageName, line))
                c.sendLine(line)

    def setParameter(self, pName, pVal, cageId=None):
        paramString = "{}: {}".format(pName, pVal)
        if cageId:
            self.sendLineToOne(cageId, paramString)
        else:
            self.sendLineToAll(paramString)

    def startFC(self, cageId=None):
        cmd = "F"
        if cageId:
            self.sendLineToOne(cageId, cmd)
        else:
            self.sendLineToAll(cmd)

    def stopFC(self, cageId=None):
        cmd = "X"
        if cageId:
            self.sendLineToOne(cageId, cmd)
        else:
            self.sendLineToAll(cmd)

    def runVideo(self, id):
        self.sendLineToOne(id, "V")

    def startTimelapse(self, cageId=None):
        cmd = "T"
        if cageId:
            self.sendLineToOne(cageId, cmd)
        else:
            self.sendLineToAll(cmd)

    def endTimelapse(self, cageId=None):
        cmd = "E"
        if cageId:
            self.sendLineToOne(cageId, cmd)
        else:
            self.sendLineToAll(cmd)


## For Testing/Debug purposes below:

class nullInterface():
    def addCage(self, cageIP):
        pass

    def removeCage(self, cageID):
        pass

def main():
    ni = nullInterface();
    reactor.listenTCP(IP_PORT, PiCoordinationFactory(ni))
    reactor.run()

# this only runs if the module was *not* imported
if __name__ == '__main__':
    main()
