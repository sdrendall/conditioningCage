# coding=UTF-8

"Basic wx interface for Home Cage Fear Conditioning controler."


import wx
import os
import json
import subprocess as sp

# local settings for layout
SECTION_BORDER_WIDTH = 20
BUTTON_BORDER = 5

# set up parameters
class Parameter(object):
    def __init__(self, guiString, variableName, value, min=0, max=1e6):
        self.guiString = guiString
        self.variableName = variableName
        self.value = value
        self.min = min
        self.max = max


fcParams = [];

fcParams.append(Parameter('Temperature Check Interval (sec)', 'tempPeriod', 2))
fcParams.append(Parameter('Tone Duration (sec)', 'toneDuration', 2))
fcParams.append(Parameter('Shock Duration (sec)', 'shockDuration', 1))
fcParams.append(Parameter('Target Temperature (°C)', 'targetTemp', 30))
fcParams.append(Parameter('Water delivery valve open time (ms)', 'dispensationInterval', 100))
fcParams.append(Parameter('Fear Tone Frequency (Hz)', 'fcToneFrequency', 6000))

## not currently in use
# fcParams['maxNosepokesPerTone'] = 30
# fcParams['tmp2_active'] = 0

fcDelays = [];
fcDelays.append(Parameter('FC Delay 1', 'fcDelay1', 300))
fcDelays.append(Parameter('FC Delay 2', 'fcDelay2', 45))
fcDelays.append(Parameter('FC Delay 3', 'fcDelay3', 30))
fcDelays.append(Parameter('FC Delay 4', 'fcDelay4', 30))
fcDelays.append(Parameter('FC Delay 5', 'fcDelay5', 30))
fcDelays.append(Parameter('FC Delay 6', 'fcDelay6', 0))
fcDelays.append(Parameter('FC Delay 7', 'fcDelay7', 0))
fcDelays.append(Parameter('FC Delay 8', 'fcDelay8', 0))
fcDelays.append(Parameter('FC Delay 9', 'fcDelay9', 0))
fcDelays.append(Parameter('FC Delay 10', 'fcDelay10', 0))



class HCFHControllerWindow(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.mainSizer = wx.BoxSizer(wx.VERTICAL)

        self.topSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.mainSizer.Add(self.topSizer, 0, wx.EXPAND)

        # Client list
        self.clientListBox = wx.StaticBox(self, -1, label="Cages")
        self.clientListSizer = wx.StaticBoxSizer(self.clientListBox,wx.VERTICAL)
        self.clientList = wx.ListBox(self, -1, name="Cage List")
        self.clientListSizer.Add(self.clientList, 1, wx.EXPAND)

        self.topSizer.Add(self.clientListSizer, 1, wx.EXPAND | wx.ALL, SECTION_BORDER_WIDTH)


        # Command Buttons
        self.commandListBox = wx.StaticBox(self, -1, label="Commands")
        self.commandListSizer = wx.StaticBoxSizer(self.commandListBox, wx.VERTICAL)

        self.commandUploadParams = wx.Button(self, -1, "Upload parameters to all cages")
        self.commandUploadParams.Bind(wx.EVT_BUTTON, self.uploadParamsAllCagesEvent)
        self.commandListSizer.Add(self.commandUploadParams, 0, wx.ALL, BUTTON_BORDER)

        self.commandUploadParams = wx.Button(self, -1, "Upload parameters to selected cage")
        self.commandUploadParams.Bind(wx.EVT_BUTTON, self.uploadParamsOneCageEvent)
        self.commandListSizer.Add(self.commandUploadParams, 0, wx.ALL, BUTTON_BORDER)

        self.commandSaveParams = wx.Button(self, -1, "Save parameters to file")
        self.commandSaveParams.Bind(wx.EVT_BUTTON, self.saveParams)
        self.commandListSizer.Add(self.commandSaveParams, 0, wx.ALL, BUTTON_BORDER)

        self.commandLoadParams = wx.Button(self, -1, "Load parameters from file")
        self.commandLoadParams.Bind(wx.EVT_BUTTON, self.loadParams)
        self.commandListSizer.Add(self.commandLoadParams, 0, wx.ALL, BUTTON_BORDER)

        self.commandSetDefaultParams = wx.Button(self, -1, "Save parameters as default")
        self.commandSetDefaultParams.Bind(wx.EVT_BUTTON, self.setDefaultParams)
        self.commandListSizer.Add(self.commandSetDefaultParams, 0, wx.ALL, BUTTON_BORDER)


        self.commandStartFC = wx.Button(self, -1, "Start Fear Conditioning in All Cages")
        self.commandStartFC.Bind(wx.EVT_BUTTON, self.runFCAllCages)
        self.commandStartFC.SetBackgroundColour(wx.GREEN)
        self.commandListSizer.Add(self.commandStartFC, 0, wx.ALL, BUTTON_BORDER)

        self.commandStartOneFC = wx.Button(self, -1, "Start Fear Conditioning in Selected Cage")
        self.commandStartOneFC.Bind(wx.EVT_BUTTON, self.runFCOneCage)
        self.commandStartOneFC.SetBackgroundColour(wx.GREEN)
        self.commandListSizer.Add(self.commandStartOneFC, 0, wx.ALL, BUTTON_BORDER)

        self.commandStopFC = wx.Button(self, -1, "Stop Fear Conditioning in All Cages")
        self.commandStopFC.Bind(wx.EVT_BUTTON, self.endFCAllCages)
        self.commandStopFC.SetBackgroundColour(wx.RED)
        self.commandListSizer.Add(self.commandStopFC, 0, wx.ALL, BUTTON_BORDER)

        self.commandStopOneFC = wx.Button(self, -1, "Stop Fear Conditioning in Selected Cage")
        self.commandStopOneFC.Bind(wx.EVT_BUTTON, self.endFCOneCage)
        self.commandStopOneFC.SetBackgroundColour(wx.RED)
        self.commandListSizer.Add(self.commandStopOneFC, 0, wx.ALL, BUTTON_BORDER)

        self.commandStartVideo = wx.Button(self, -1, "Get Video Stream from Selected Cage")
        self.commandStartVideo.Bind(wx.EVT_BUTTON, self.runVideo)
        self.commandListSizer.Add(self.commandStartVideo, 0, wx.ALL, BUTTON_BORDER)

        self.commandStartOneTimelapse = wx.Button(self, -1, "Run Timelapse in Selected Cage")
        self.commandStartOneTimelapse.Bind(wx.EVT_BUTTON, self.runOneTimelapse)
        self.commandStartOneTimelapse.SetBackgroundColour(wx.GREEN)
        self.commandListSizer.Add(self.commandStartOneTimelapse, 0, wx.ALL, BUTTON_BORDER)

        self.commandStartTimelapse = wx.Button(self, -1, "Run Timelapse in All Cages")
        self.commandStartTimelapse.Bind(wx.EVT_BUTTON, self.runTimelapse)
        self.commandStartTimelapse.SetBackgroundColour(wx.GREEN)
        self.commandListSizer.Add(self.commandStartTimelapse, 0, wx.ALL, BUTTON_BORDER)

        self.commandEndOneTimelapse = wx.Button(self, -1, "Stop Timelapse in Selected Cage")
        self.commandEndOneTimelapse.Bind(wx.EVT_BUTTON, self.endOneTimelapse)
        self.commandEndOneTimelapse.SetBackgroundColour(wx.RED)
        self.commandListSizer.Add(self.commandEndOneTimelapse, 0, wx.ALL, BUTTON_BORDER)

        self.commandEndTimelapse = wx.Button(self, -1, "Stop Timelapse in All Cages")
        self.commandEndTimelapse.Bind(wx.EVT_BUTTON, self.endTimelapse)
        self.commandEndTimelapse.SetBackgroundColour(wx.RED)
        self.commandListSizer.Add(self.commandEndTimelapse, 0, wx.ALL, BUTTON_BORDER)

        self.topSizer.Add(self.commandListSizer, 1, 0 | wx.TOP | wx.BOTTOM, SECTION_BORDER_WIDTH)

        # FC Parameters
        self.parametersListBox = wx.StaticBox(self, -1, label="FC Paramters")
        self.parametersListSizer = wx.StaticBoxSizer(self.parametersListBox, wx.VERTICAL)

        self.delaysBox = wx.StaticBox(self, -1, label="FC Delays (in seconds)")
        self.delaysSizer = wx.StaticBoxSizer(self.delaysBox, wx.VERTICAL)

        self.parameterCtrls = {}
        for p in fcParams:
            hbox = wx.BoxSizer(wx.HORIZONTAL)
            st = wx.StaticText(self, label=p.guiString)
            hbox.Add(st, proportion=1, flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=8)
            sc = wx.SpinCtrl(self,size=(80,-1))
            sc.SetRange(p.min, p.max)
            sc.SetValue(p.value)
            sc.SetSelection(0,0) # prevent value from being initially selected
            sc.variableName = p.variableName
            self.parameterCtrls[sc.variableName] = sc
            hbox.Add(sc, proportion=0)
            self.parametersListSizer.Add(hbox, flag=0|wx.LEFT|wx.RIGHT|wx.TOP|wx.ALIGN_RIGHT, border=10)

        for p in fcDelays:
            hbox = wx.BoxSizer(wx.HORIZONTAL)
            st = wx.StaticText(self, label=p.guiString)
            hbox.Add(st, flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=8)
            sc = wx.SpinCtrl(self)
            sc.SetRange(p.min, p.max)
            sc.SetValue(p.value)
            sc.SetSelection(0,0) # prevent value from being initially selected
            sc.variableName = p.variableName
            self.parameterCtrls[sc.variableName] = sc
            hbox.Add(sc, proportion=1)
            self.delaysSizer.Add(hbox, -1, flag=0|wx.LEFT|wx.RIGHT|wx.TOP|wx.ALIGN_RIGHT, border=10)

        self.parametersSizer = wx.BoxSizer(wx.VERTICAL)
        self.parametersSizer.Add(self.parametersListSizer,0,wx.EXPAND)
        self.parametersSizer.Add(self.delaysSizer,0,wx.EXPAND|wx.TOP,border=10)

        self.topSizer.Add(self.parametersSizer, 1, wx.EXPAND | wx.ALL, SECTION_BORDER_WIDTH)

        self.debugText = wx.TextCtrl(self, style=wx.TE_READONLY|wx.TE_MULTILINE)
        self.debugText.SetDefaultStyle(wx.TextAttr(wx.BLUE))
        self.debugText.SetSizeHints(0,75)

        self.mainSizer.Add(self.debugText, 1, wx.EXPAND | wx.ALL, SECTION_BORDER_WIDTH)

        # load up default parameters, if file exists
        self.loadDefaultParams()

        #Layout sizers
        self.SetSizer(self.mainSizer)
        self.SetAutoLayout(1)
        self.mainSizer.Fit(self)
        self.Show()

    def addCage(self, cageID, cageName):
        self.clientList.Append(cageName, cageID)

    def removeCage(self, cageID):
        for n in xrange(self.clientList.GetCount()):
            if cageID == self.clientList.GetClientData(n):
                self.clientList.Delete(n)

    def runFCAllCages(self, e):
        """Send FC paramaters to cages, then run FC."""
        self.uploadParams()
        self.server.startFC()

    def runFCOneCage(self, e):
        """Send FC paramaters to one cage, then run FC."""
        n = self.clientList.GetSelection()
        if n == wx.NOT_FOUND:
            self.displayText("Run FC: No cage selected.")
        else:
            id = self.clientList.GetClientData(n)
            self.uploadParams(id)
            self.server.startFC(id)

    def endFCAllCages(self, e):
        """Cancel FC."""
        self.server.stopFC()

    def endFCOneCage(self, e):
        """Cancel FC."""
        n = self.clientList.GetSelection()
        if n == wx.NOT_FOUND:
            self.displayText("Stop FC: No cage selected.")
        else:
            id = self.clientList.GetClientData(n)
            self.server.stopFC(id)

    def runTimelapse(self, e):
        self.server.startTimelapse()

    def runOneTimelapse(self, e):
        n = self.clientList.GetSelection()
        if n == wx.NOT_FOUND:
            self.displayText("Start Timelapse: No cage selected.")
        else:
            id = self.clientList.GetClientData(n)
            self.server.startTimelapse(id)

    def endTimelapse(self, e):
        self.server.endTimelapse()

    def endOneTimelapse(self, e):
        n = self.clientList.GetSelection()
        if n == wx.NOT_FOUND:
            self.displayText("End Timelapse: No cage selected.")
        else:
            id = self.clientList.GetClientData(n)
            self.server.endTimelapse(id)

    def uploadParamsAllCagesEvent(self, e):
        self.uploadParams()

    def uploadParamsOneCageEvent(self, e):
        n = self.clientList.GetSelection()
        if n == wx.NOT_FOUND:
            self.displayText("Upload Parameters: No cage selected.")
        else:
            id = self.clientList.GetClientData(n)
            self.uploadParams(id)

    def uploadParams(self, cageID=None):
        for pc in self.parameterCtrls.itervalues():
            pName = pc.variableName
            pVal = pc.GetValue()
            if pName in {'tempPeriod', 'toneDuration', 'shockDuration'}:
                pVal *=1000 # convert from sec to ms
            if not pName.startswith("fcDelay"):
                self.server.setParameter(pName, pVal, cageID)
        delaysArray = []
        for xx in xrange(1,11):
            delay = self.parameterCtrls["fcDelay"+str(xx)].GetValue()
            delay *= 1000 # convert from sec to ms
            if delay==0:
                break
            delaysArray.append(delay)
        self.server.setParameter("BlockDuration", str(delaysArray).strip("[]"), cageID)


    def saveParams(self, event=None, filePath=None):
        if filePath==None:
            style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
            dialog = wx.FileDialog(None, 'Save', wildcard="*.pref", style=style)
            if dialog.ShowModal() == wx.ID_OK:
                filePath = dialog.GetPath()
            else:
                filePath = None
            dialog.Destroy()

        if filePath!=None:
            fName, fExt = os.path.splitext(filePath)
            filePath = fName+".pref"

            try:
                saveFile = open(filePath,'w')
                paramsDict = {pc.variableName: pc.GetValue() for pc in self.parameterCtrls.itervalues()}
                saveFile.write(json.dumps(paramsDict, sort_keys=True, indent=4, separators=(',', ': ')))
                saveFile.close()
            except Exception, e:
                raise

    DEFAULTS_FILE_NAME = "HomeCageConditioningDefaults.pref"

    def setDefaultParams(self, e):
        self.saveParams(filePath=self.DEFAULTS_FILE_NAME)

    def loadDefaultParams(self):
        if os.path.exists(self.DEFAULTS_FILE_NAME):
            self.loadParams(filePath=self.DEFAULTS_FILE_NAME)

    def loadParams(self, event=None, filePath=None):
        if filePath==None:
            style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            dialog = wx.FileDialog(None, 'Open', wildcard="*", style=style)
            if dialog.ShowModal() == wx.ID_OK:
                filePath = dialog.GetPath()
            else:
                filePath = None
            dialog.Destroy()

        if filePath!=None:
            try:
                paramFile = open(filePath,'r')
                newParamsDict = json.load(paramFile)
                paramFile.close()
                for (pName, pVal) in newParamsDict.iteritems():
                    if self.parameterCtrls.has_key(pName):
                        self.parameterCtrls[pName].SetValue(pVal)
                        self.parameterCtrls[pName].SetSelection(0,0) # prevent value from being selected
            except Exception, e:
                raise


    def runVideo(self, e):
        n = self.clientList.GetSelection()
        if n == wx.NOT_FOUND:
            self.displayText("Get Video: No cage selected.")
        else:
            id = self.clientList.GetClientData(n)
            sp.Popen("nc -l 5001 | mplayer -fps 31 -cache 1024 -", shell=True)
            self.server.runVideo(id)

    def setServer(self, server):
        self.server = server

    def displayText(self, text):
        self.debugText.AppendText(text + "\n")

class NullServer():
    def runVideo(self,id):
        pass
    def startFC(self):
        pass

def main():
    ns = NullServer()
    app = wx.App(False)
    frame = wx.Frame(None,name="HCFC Controller")
    panel = HCFHControllerWindow(frame)
    panel.setServer(ns)
    frame.Show()
    frame.SetSize((1000,2000))
    app.MainLoop()

if __name__ == '__main__':
    main()
