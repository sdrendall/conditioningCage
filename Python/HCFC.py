#! /usr/bin/env python

# Echo server program


# get Twisted ready
from twisted.internet import wxreactor
wxreactor.install()
from twisted.internet import reactor
import HCFCServer

# inport wx/GUI
import wx
import wxHCFCInterface

# setup GUI
app = wx.App(False)
frame = wx.Frame(None,name="HCFC Controller")
panel = wxHCFCInterface.HCFHControllerWindow(frame)
frame.Show()
frame.SetSize((1000,900))
#app.MainLoop()

# create server
server = HCFCServer.PiCoordinationFactory(panel)
panel.setServer(server)

# coordinate wx & Twisted
reactor.registerWxApp(app)

#setup GUI/reactor
reactor.listenTCP(1025, server)
reactor.run()


