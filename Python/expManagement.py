import os, datetime, subprocess, json
from pprint import pprint

rootPath = os.path.expanduser("~/Desktop/testExperiments")

# Interface functions
def createExperiment(expId):
    dirName = "Experiment_{}".format(expId)
    expPath = os.path.join(rootPath, dirName) 
    # Check Path for existing experiments
    if os.path.isdir(expPath):
        raise ExperimentExists(expPath)
    else:
        # Attempt to create a new experiment directory
        if ensureDirectory(expPath):
            # If the directory can be created, instantiate a new experiment
            # and return it
            attrs = {
            'path': expPath,
            'id': expId
            }
            experiment = Experiment(attrs)
            return experiment
        else:
            raise DirCreationFailed(expPath)


def loadExperiment(filePath=None):
    # Load the experiment's attributes dict from the JSON file
    jsonFile = open(filePath, 'r')
    expAttrs = json.load(jsonFile)
    jsonFile.close()

    # Instantiate and return the experiment 
    return Experiment(expAttrs)


class Experiment:
    """ The base directory for each experiment.
    handles ID generation and responsible for checking for the existence of mice 
    """

    def __init__(self, attrs):
        # This is the dict that will be saved as JSON.
        # Ideally the entire Experiment object (including subobjects)
        # Could be reconstructed from this info
        self.attributes = {
            'path': None,
            'id': None,
            'dateCreated': subprocess.check_output("date", shell=True),
            # References to each mouse's dict, timelapses and video dicts are here
            'mice': {},
            # Lists for IdGenerators
            'tlIdList': [],
            'vidIdList': [],
            'logIdList': []
        }

        self.mice = {}

        # Update attributes
        for key, val in attrs.iteritems():
            self.attributes[key] = val

        # Unpack mice, if passed mouse dicts, occurs when an old experiment is loaded
        self.unpackMice()

        # Pointer to JSON save file
        self.jsonPath = self.generateJsonPath()

        # Create generators for Ids
        self.getNextMouseId = IdGenerator(self.attributes['mice'])
        self.timelapseIdGenerator = IdGenerator(self.attributes['tlIdList'])
        self.videoIdGenerator = IdGenerator(self.attributes['vidIdList'])
        self.logIdGenerator = IdGenerator(self.attributes['logIdList'])

# JSON functions
    def generateJsonPath(self):
        jsonName = "{}.json".format(self.attributes['id'])
        return os.path.join(self.attributes['path'], jsonName)

    def exportToJSON(self):
        saveFile = open(self.jsonPath, 'w')
        saveFile.write(json.dumps(self.attributes,  sort_keys=True, indent=4, separators=(',', ': ')))
        saveFile.close()

# Mouse functions
    def createMouse(self, mouseId):
        # Create a new mouse directory
        try:
            mousePath = self.createMouseDirectory(mouseId)
        except DirCreationFailed, e:
            print "Failed to create mouse Directory!"
            print e
            return None

        # Package initializing attributes
        attrs = {
            'id': mouseId,
            'path': mousePath
        }

        # Create paths for timelapses, videos and logs
        for dirName, pathKey in [('timelapes', 'tlPath'), ('videos','vidPath'), ('logs','logPath')]:
            path = os.path.join(mousePath, dirName)
            ensureDirectory(path)
            attrs[pathKey] = path


        # Instantiate a mouse and reference its attributes dict
        mouse = Mouse(self, attrs)
        self.mice[mouseId] = mouse
        self.attributes['mice'][mouseId] = mouse.attributes

        return mouse

    def ensureMouse(self, mouseId):
        if mouseId not in self.attributes['mice']:
            createMouse(mouseId)
        else:
            ensureDirectory(self.attributes['mice'][mouseId]['path'])


    def createMouseDirectory(self, mouseId):
        # Make sure the base directory is there
        ensureDirectory(self.attributes['path'])

        # Create mouse directory
        dirName = "mouse_{}".format(mouseId)
        mousePath = os.path.join(self.attributes['path'], dirName)
        if ensureDirectory(mousePath):
            return mousePath
        else:
            raise DirCreationFailed(mousePath)

    def unpackMice(self):
        for key, mouseDict in self.attributes['mice'].iteritems():
            ensureDirectory(mouseDict['path'])
            self.mice[key] = Mouse(self, mouseDict)




class Mouse:
    """ This is the mouse class.  Instantiated for each mouse.
    Maintains timelapse, video and log paths for this mouse """

    def __init__(self, experiment, attrs):
        # Create a new attributes dict for each mouse
        self.attributes = {
            'timelapses': {},
            'videos': {},
            'logs': {}
            }
        # Reference the experiment 
        self.experiment = experiment
        # Add/update keys+values
        for key, val in attrs.iteritems():
            self.attributes[key] = val
        

    def createTimelapse(self):
        # Generate New Id, use date stamp
        tlId = generateDateId(self.experiment.timelapseIdGenerator)

        # Create Timelapse Path
        tlPath = self.createTimelapsePath(tlId)

        # Store timelapse attributes in a dict
        self.attributes['timelapses'][tlId] = {
        'path': tlPath,
        'id': tlId
        }

        # Return Timelapse attributes dict
        return self.attributes['timelapses'][tlId]


    def createTimelapsePath(self, tlId):
        dirName = "timelapse_{}".format(tlId)
        tlPath = os.path.join(self.attributes['tlPath'], dirName)
        if ensureDirectory(tlPath):
            return tlPath
        else:
            raise DirCreationFailed(tlPath)


    def createVideo(self):
        # Generate Id
        vidId = generateDateId(self.experiment.videoIdGenerator)
        # Store attributes in a dict
        self.attributes['videos'][vidId] = {
        'id': vidId,
        'path': self.attributes['vidPath']
        }
        # Return Dict
        return self.attributes['videos'][vidId]


    def createLog(self):
        # Same deal as Video creation
        logId = generateDateId(self.experiment.logIdGenerator)
        self.attributes['logs'][logId] = {
        'id': logId,
        'path': self.attributes['logPath'] 
        }

# Misc. Useful functions
def IdGenerator(idList=[]):
    """ Generator to generate ID numbers for timelapses,
    videos, mice... 
    """
    idNo = 0
    while True:
        idNo += 1
        if not idNo in idList:
            idList.append(idNo)
            yield idNo


def generateDateString():
    dt = datetime.datetime.now()
    dateString = "{:04}{:02}{:02}_{:02}{:02}".\
            format(dt.year, dt.month, dt.day, dt.hour, dt.minute)
    return dateString


def generateDateId(generator):
    return "{}_{}".format(generateDateString(), generator.next())


def ensureDirectory(path):
    """ Ensures that a directory exists at the given path.  If a directory 
    is not found, attempts to make one.  Returns a boolean stating whether or not
    a directory exists at the given path"""
    if path and os.path.isdir(path):
        return True
    else:
        try:
            os.mkdir(path)
            return True
        except OSError, e:
            print "Could not create directory %r" % path
            print e
            return False


## EXCEPTIONS!
class ExperimentExists(Exception):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        errString = "Experiment already exists at {}".format(path)
        return repr(errString)

class DirCreationFailed(Exception):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        errString = "Failed to create a directory at {}".format(path)
        return repr(errString)


# For Debugging
def main():
    # Create an experiment and test timelapse, video and log creation
    jsonPath = testNewExperiment()
    # Load an experiment and print out the results
    testLoadedExperiment(jsonPath)


def testNewExperiment():
    print "Testing a new experiment!\n"
    # Create an experiment
    experiment = createExperiment('testExp')
    # Create some Mice
    mice = {}
    for mId in range(1,5):
        mice[mId] = experiment.createMouse(mId)
    # Create some Timelapses
    tlRefs =[]
    for mouseNo in [1, 3, 3, 2, 4, 1]:
        tlRefs.append(mice[mouseNo].createTimelapse())
    # Create some Videos
    vidRefs = []
    for mouseNo in [2, 4, 4, 2, 3, 1]:
        vidRefs.append(mice[mouseNo].createVideo())
    # Create some logs
    logRefs = []
    for mouseNo in [2, 1, 1, 3, 4, 2]:
        logRefs.append(mice[mouseNo].createLog())

    # Print the results
    print "Timelapse References:"
    pprint(tlRefs)
    print '\n'

    print "Video References:"
    pprint(vidRefs)
    print'\n'

    print "Log References:"
    pprint(logRefs)
    print'\n'
    
    print "Experiment Attributes:"
    pprint(experiment.attributes)
    print'\n'

    # Export attributes to json
    experiment.exportToJSON()

    return experiment.jsonPath

def testLoadedExperiment(jsonPath):
    print "Testing a loaded Experiment!\n"
    experiment = loadExperiment(jsonPath)

    # Reference the mice
    mice = {}
    for mId, mouse in experiment.mice.iteritems():
        mice[int(mId)] = mouse 
    pprint(mice)
    # Create some Timelapses
    tlRefs =[]
    for mouseNo in [1, 3, 3, 4, 2]:
        tlRefs.append(mice[mouseNo].createTimelapse())
    # Create some Videos
    vidRefs = []
    for mouseNo in [2, 4, 3, 1]:
        vidRefs.append(mice[mouseNo].createVideo())
    # Create some logs
    logRefs = []
    for mouseNo in [2, 1, 1, 3, 4, 2]:
        logRefs.append(mice[mouseNo].createLog())


    # Print the results
    print "Timelapse References:"
    pprint(tlRefs)
    print '\n'

    print "Video References:"
    pprint(vidRefs)
    print'\n'

    print "Log References:"
    pprint(logRefs)
    print'\n'
    
    print "Experiment Attributes:"
    pprint(experiment.attributes)
    print'\n'


if __name__ == "__main__":
    main()