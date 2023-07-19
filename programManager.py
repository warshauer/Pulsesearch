import sys
from PyQt5 import QtWidgets
from PyQt5 import uic
#import warsh_calc as wc
import pulseSearch as ps

'''
To add an instrument application, just import the QMainWindow class, create the instance in runApp(), pass that instance into the managerWindow list.
In the QMainWindow class, give the attribute 'me' (ex. self.me = 'pulsesearch'), this will be drawn from by the manager window.
'''
def runApp():
    app = QtWidgets.QApplication(sys.argv)

    #lakeshoreControl = lsc.lakeshoreWindow()
    pulseSearch = ps.pulsesearchWindow(version = 'v1.2')
    pulseSearch.show()
    # add other applications here, then drop into the next class as an arg

    #manWindow = managerWindow(pulseSearch)
    #manWindow.show()

    sys.exit(app.exec_())

class managerWindow(QtWidgets.QMainWindow):
    def __init__(self, *apps):
        QtWidgets.QMainWindow.__init__(self)
        self.ui = uic.loadUi('manager.ui',self)
        self.resize(200, 100)
        self.me = 'manager'

        self.apps = list(apps)
        i=0
        for app in apps:
            try:
                self.LW_apps.addItem(app.me)
            except:
                self.LW_apps.addItem(str(i))
                i+=1
        self.PB_show.clicked.connect(self.showApp)
        self.PB_hide.clicked.connect(self.hideApp)

    def showApp(self):
        i = self.LW_apps.currentRow()
        if type(i) == int:
            self.apps[i].show()

    def hideApp(self):
        i = self.LW_apps.currentRow()
        if type(i) == int:
            self.apps[i].hide()

runApp()
