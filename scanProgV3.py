import numpy as np
import os
import sys
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.ticker as ticker
import numpy as np
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot
import appClasses as dd
#import qt5_controller as qc
from warsh_comms import smsClient
#from flowControllerClasses import Flowmeter
from instrumentControl import esp301_GPIB, sr830
import time

class DLscanWindow(QtWidgets.QWidget):
    def __init__(self, parent, whoami = 'DLscan'):
        QtWidgets.QWidget.__init__(self)
        self.ui = uic.loadUi('scansV3.ui',self)
        self.resize(1600, 950)
        self.me = whoami
        self.parent = parent

        self.extraDelay = 0.05

        self.started = False

        self.threadpool = QtCore.QThreadPool()	
        self.threadpool.setMaxThreadCount(1)

        self.settings = QtCore.QSettings(self.me, 'v1.1')

        

        
        self._timeConstantList = [.00001, .00003, .0001, .0003, .001, .003, .01, .03, .1, .3, 1, 3, 10, 30, 100, 300, 1000, 3000, 10000, 30000]
        self._sensitivityList = [2, 5, 10, 20, 50, 100, 200, 500, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1]
        
        self.sms_variables ={'sms_toggle':False, 'sms_interval':5}

        
        line_dict = {1:{'live':{'color':'tab:orange', 'alpha':.75}}, 
                     2:{'live':{'color':'tab:red', 'alpha':.64, 'linestyle':'dashed'}}}
        plot_dict = {1:{'ylabel':'lock-in 1', 'ylimits':[-1,1]}, 2:{'ylabel':'lock-in 2', 'ylimits':[-1,1]}}

        self.plot = dd.plotCanvasDL(self, line_dict = line_dict, xlabel = 'time (ps)', plot_dict = plot_dict, autolim = False, xlimits = [-1, 1], last_point = True)
        #self.logger = dd.logfileManager(self, downsample = 4)
        self.ui.GL_plot.addWidget(self.plot,0,0,1,1)

        self.cutie = cuteWorker(self, self.plot)
        self.thread = QtCore.QThread(parent = self)
        self.cutie.moveToThread(self.thread)

        self._move = False
        self.moveOn = False
        self._cmi = 0
        self._cmpn = 1
        self._toggles = {'1_op':True, '2_op':False}
        self.count_dracula = 0
        self.pn = 1
        self.link = 0

        self.motionAllowed = True
        self.addNext = False
        self.stageJustMoved = False
        self.timeStageEnd = time.monotonic()
        self.loot = time.monotonic()

        

        if True:
            self.stageValues = {}
            self.stageValues[1] = {'home':0.00, 'pos':0}
            self.stageValues[2] = {'home':0.00, 'pos':0}
            self.stageValues[3] = {'home':0.00, 'pos':0}

            self.sWidgets = {'THzsetposition':self.SB_THzPos, 'gatesetposition':self.SB_gatePos, 'THzposition':self.LE_THzCurrent, 'gateposition':self.LE_gateCurrent, 'prescan':self.SB_prescan,'delays':self.TE_delays, 'start':self.PB_start, 'comments':self.TE_comments, 'extension':self.LE_extension, 'startnum':self.SB_startnum, 'filename':self.LE_filename, 'path':self.LE_path, 'browse':self.PB_browse, 'stop':self.PB_stop, 'stepsize':self.SB_stepSize, 'numsteps':self.SB_numSteps, 'THzkey':self.LE_THzKey, 'gatekey':self.LE_gateKey, 'rotkey':self.LE_rotKey, 'scanperround':self.SB_scanPerRound, 'numrounds':self.SB_numRounds, 'round':self.LE_round, 'delay':self.LE_delay, 'scan':self.LE_scan, 'set2current':self.PB_set2current, 'scanmode':self.CB_scanMode}


            # why didn't this work in a for loop :(
            self.sWidgets['start'].clicked.connect(self._start)
            self.sWidgets['stop'].clicked.connect(self.stop)
            self.sWidgets['browse'].clicked.connect(self._browse)
            self.sWidgets['set2current'].clicked.connect( self._set2current )
            


            self.SB_xlim0.valueChanged.connect( lambda : self.xlimit_change( self.plot, 0, self.SB_xlim0.value() ) )
            self.SB_xlim1.valueChanged.connect( lambda : self.xlimit_change( self.plot, 1, self.SB_xlim1.value() ) )
            self.wiggy = {}
            self.wiggy[1] = {'ylim0':self.SB_ylim00, 'ylim1':self.SB_ylim01}
            self.wiggy[2] = {'ylim0':self.SB_ylim10, 'ylim1':self.SB_ylim11}
            self.SB_ylim00.valueChanged.connect( lambda : self.ylimit_change( self.plot, 0, self.SB_ylim00.value(), axis = 1 ) )
            self.SB_ylim01.valueChanged.connect( lambda : self.ylimit_change( self.plot, 1, self.SB_ylim01.value(), axis = 1 ) )
            self.SB_ylim10.valueChanged.connect( lambda : self.ylimit_change( self.plot, 0, self.SB_ylim10.value(), axis = 2 ) )
            self.SB_ylim11.valueChanged.connect( lambda : self.ylimit_change( self.plot, 1, self.SB_ylim11.value(), axis = 2) )

        self._sample_interval = 50
        self._timer = QtCore.QTimer()
        self._timer.setInterval(self._sample_interval) #msec
        self._timer.timeout.connect(self.runtime_functionV2)
        

        self.tt = time.monotonic()

        self._recallSettings()
        

        quit = QtWidgets.QAction("Quit", self)
        quit.triggered.connect(self.close)

    def onWindowOpen(self):
        self.lockins = self.parent.lockins
        self.stageBoss = self.parent.stageBoss
        self.timeConstants = [self._timeConstantList[self.lockins[1].get_time_constant()], self._timeConstantList[self.lockins[2].get_time_constant()]]
        self.x = []
        self.y = {}
        self.y[1] = {'live':[]}
        self.y[2] = {'live':[]}
        for key in self.lockins:
            self.y[key]['live'].append(self._get_measurement(self.lockins[key]))
        self.x.append(0)
        self._timer.start()


    def _sensitivityChange(self, index, value):
        self.wiggy[index]['ylim0'].setValue(-self._sensitivityList[value])
        self.wiggy[index]['ylim1'].setValue(self._sensitivityList[value])
        self.ylimit_change( self.plot, 0, -self._sensitivityList[value], axis = index )
        self.ylimit_change( self.plot, 1, self._sensitivityList[value], axis = index )
        # change y limits

    def _setStepsize(self, stage_key, step_size):
        self.stageBoss.setStepsize(stage_key, step_size)

    def _moveStep(self, stage_key):
        self.stageBoss.moveStageStep(stage_key)
        self.stageJustMoved = True

    def _moveAbsolute(self, stage_key, pos):
        self.stageBoss.moveStageAbsolute(stage_key, pos)
        self.stageJustMoved = True

    def _update_stage_position(self, *stage_keys):
        for stage_key in stage_keys:
            self.stageBoss.updateStagePosition(stage_key)
            if stage_key == 'ESP1':
                self.sWidgets['THzposition'].setText(format(self.stageBoss.getStagePosition(stage_key), '.4f'))
            elif stage_key == 'ESP2':
                self.sWidgets['gateposition'].setText(format(self.stageBoss.getStagePosition(stage_key), '.4f'))
            elif stage_key == 'CONEX':
                self.LE_rotCurrent.setText(format(self.stageBoss.getStagePosition(stage_key), '.4f'))
            else:
                pass

    def _browse(self):
        fname = QtWidgets.QFileDialog.getSaveFileName(self, ' Select Log File ', r'C:\Data\THz')
        print(fname[0])
        print(fname[0].split('/')[-1])
        self.sWidgets['filename'].setText(fname[0].split('/')[-1])
        self.sWidgets['path'].setText(fname[0][:len(fname[0])-len(fname[0].split('/')[-1])].strip('/'))

    def appendData(self):
        y1 = self._get_measurement(self.lockins[1])
        self.y[1]['live'].append(y1)
        y2 = self._get_measurement(self.lockins[2])
        self.y[2]['live'].append(y2)
        self._update_stage_position('ESP1', 'ESP2')
        x = self.pn*(self.stageBoss.getStagePosition('ESP1') - self.THzStart)/.15
        self.x.append(x)
        self.hippo.feedData(x, y1, y2)
        #print(time.monotonic() - self.loot)
        #self.loot = time.monotonic()

    def _get_measurement(self, lockin):
        return lockin.get_output()

    def _set2current(self):
        self.sWidgets['THzsetposition'].setValue(self.stageBoss.getStagePosition('ESP1'))
        self.sWidgets['gatesetposition'].setValue(self.stageBoss.getStagePosition('ESP2'))

    def _widgetEnable(self, bool):
        for k in ['THzsetposition', 'gatesetposition', 'prescan', 'delays', 'start', 'comments', 'extension', 'startnum', 'scanperround', 'numrounds', 'set2current', 'stepsize', 'filename', 'path', 'browse', 'numsteps', 'scanmode']:
            self.sWidgets[k].setEnabled(bool)
    
    def _start(self):
        # get sensitivity, time constant, etc
        # y axis based on sensitivity
        # wait times based on time constant
        try:
            self._sensitivityChange(1, self.lockins[1].get_sensitivity())
            self.timeConstants[0] = self._timeConstantList[self.lockins[1].get_time_constant()]
            self._sensitivityChange(2, self.lockins[2].get_sensitivity())
            self.timeConstants[1] = self._timeConstantList[self.lockins[2].get_time_constant()]
            self.parent.scanStart()
            self.delays, self.numScans = self._parseDelays()
            self.rotPositions = self._parseRotationPositions()
            comments = self._buildComments()
            self.hippo = HungryHungryHippo(self, self.delays, self.numScans, self.sWidgets['numrounds'].value(), self.sWidgets['numsteps'].value(), self.sWidgets['path'].text(), self.sWidgets['filename'].text(), self.sWidgets['extension'].text(), self.sWidgets['startnum'].value(), comments)
            self.scanList = self.buildScans(self.sWidgets['THzsetposition'].value(), str(self.sWidgets['THzkey'].text()), self.sWidgets['gatesetposition'].value(), str(self.sWidgets['gatekey'].text()), self.delays, self.numScans, self.sWidgets['stepsize'].value(), self.sWidgets['numsteps'].value(), self.sWidgets['prescan'].value(), self.sWidgets['numrounds'].value(), str(self.sWidgets['rotkey'].text()), self.rotPositions, typo = str(self.CB_scanType.currentText()))
            print('scanList created')
            self.xlimit_change(self.plot, 0, 0)
            self.xlimit_change(self.plot, 1, self.sWidgets['numsteps'].value()*self.sWidgets['stepsize'].value()/.15/1000)
            self.x = []
            self.y[1]['live'] = []
            self.y[2]['live'] = []
            self._widgetEnable(False)
            scanDict = self.scanList.pop(0)
            self.initializeScan(*scanDict['args'], numSteps = scanDict['numSteps'], RDS = scanDict['RDS'])
            print('after pull')
            self.started = False
            while self.started != True:
                self.executeQueue()
            #self._timer.start()
            self.tabs1.setCurrentIndex(1)
            print('start')
        except Exception as e:
            print(e)
            try:
                self.stop()
            except Exception as e:
                print(e)
                self.started = False
                self._widgetEnable(True)
                self.parent.scanEnd()

    def beginScan(self):
        self.x = []
        self.y[1]['live'] = []
        self.y[2]['live'] = []
        self.started = True

    def stopScan(self):
        self.started = False
        self.hippo.closeFile()
        if len(self.scanList) < 1:
            self.stop()
        else:
            scanDict = self.scanList.pop(0)
            self.initializeScan(*scanDict['args'], numSteps = scanDict['numSteps'], RDS = scanDict['RDS'])
            while self.started != True:
                self.executeQueue()

    def _buildComments(self):
        delays = self.sWidgets['delays'].toPlainText()
        comments = self.sWidgets['comments'].toPlainText()
        stuff = 'rounds: ' + str(self.sWidgets['numrounds'].value()) + '    ' + 'steps: ' + str(self.sWidgets['numsteps'].value()) + '    ' + 'stepsize: ' + format(self.sWidgets['stepsize'].value(), '.4f')
        positions = 'THzSet: ' + format(self.sWidgets['THzsetposition'].value(), '.4f') + '    ' + 'gateSet: '+format(self.sWidgets['gatesetposition'].value(), '.4f') + '    ' + 'prescan: '+format(self.sWidgets['prescan'].value(), '.4f') + '      scanmode: ' + self.sWidgets['scanmode'].currentText()
        theboy = self.sWidgets['filename'].text() + '\n' + delays + '\n' + comments + '\n' + stuff + '\n' + positions
        return theboy

    def _parseDelays(self):
        text = self.sWidgets['delays'].toPlainText()
        tl = text.split(', ')
        delays = []
        numScans = []
        for item in tl:
            delays.append(float(item.split('_')[0]))
            numScans.append(int(item.split('_')[1]))
        print(delays, numScans)
        return delays, numScans
    
    def _parseRotationPositions(self):
        text = self.LE_rotPos.text()
        tl = text.split(', ')
        rotationPositions = []
        for item in tl:
            rotationPositions.append(float(item))
        print(rotationPositions)
        return rotationPositions
    
    def stop(self):
        print('stop')
        self._widgetEnable(True)
        self._storeSettings()
        self.started = False
        self.hippo.closeFile()
        self.parent.scanEnd()

    def updatePlot(self):
        #self.plot.updateCanvas(np.array(self.x), self.y)
        try:
            self.cutie.run(np.array(self.x), self.y)
        except Exception as e:
            print(e)

    def updatePlot2(self):
        self.plot.update_plot(np.array(self.x), self.y)

    # ---- MAIN RUNTIME ----
    def runtime_functionV2(self):
        if self.started:
            self.executeQueue()
        else:
            self._update_stage_position('ESP1', 'ESP2')

    def executeQueue(self):
        if len(self.commandQueue) < 1:
            print('executeQueue() received empty set of functions')
            time.sleep(20)
        else:
            funky = self.commandQueue.pop(0)
            funky()

    def _addFunctionToQueue(self, func, *args, **kwargs):
        self.commandQueue.append(self._lambMill(func, *args, **kwargs))

    def _safetyCheckpoint(self, *stage_keys):
        if True in [self.stageBoss.moving(stage_key) for stage_key in stage_keys]:
            self.commandQueue.insert(0, self._lambMill(self._safetyCheckpoint, *stage_keys))
        else:
            if self.stageJustMoved == True:
                self.timeStageEnd = time.monotonic()
                self.stageJustMoved = False
                self.commandQueue.insert(0, self._lambMill(self._safetyCheckpoint, *stage_keys))
            elif time.monotonic() - self.timeStageEnd < (self.parent.TCcof*max(self.timeConstants) + self.parent.TCadd):
                self.commandQueue.insert(0, self._lambMill(self._safetyCheckpoint, *stage_keys))
            else:
                pass

    def _lambMill(self, func, *args, **kwargs):
        return lambda:func(*args, **kwargs)

    def _update_scan_numbers(self, r, d, s):
        self.sWidgets['round'].setText(str(r))
        self.sWidgets['delay'].setText(format(self.delays[d], '.2f'))
        self.sWidgets['scan'].setText(str(s))
            

    def buildScans(self, THzStart, THzKey, gateStart, gateKey, delays, numScans, stepsize, numSteps, prescan, numRounds, rotKey, rotPositions, typo = 'THz'):
        scanList = []
        if typo == 'THz':
            for i in range(numRounds):
                for rotPos in rotPositions:
                    for j in range(len(delays)):
                        for k in range(numScans[j]):
                            THzKerby = {'stage_key':THzKey, 'start':THzStart - prescan - delays[j]*0.15, 'moving':True, 'stepsize':stepsize, 'subdir':False}
                            gateKerby = {'stage_key':gateKey, 'start':gateStart - delays[j]*0.15, 'moving':False, 'stepsize':0, 'subdir':False}
                            rotKerby = {'stage_key':rotKey, 'start':rotPos, 'moving':False, 'stepsize':0, 'subdir':True}
                            print(i,j,k)
                            scanList.append( {'args':[THzKerby.copy(), gateKerby.copy(), rotKerby.copy()], 'numSteps':numSteps, 'RDS':[i,j,k]} )
        elif typo == 'po':
            for i in range(numRounds):
                for rotPos in rotPositions:
                    for j in range(len(delays)):
                        for k in range(numScans[j]):
                            THzKerby = {'stage_key':THzKey, 'start':THzStart - delays[j]*0.15, 'moving':True, 'stepsize':stepsize, 'subdir':False}
                            gateKerby = {'stage_key':gateKey, 'start':gateStart - delays[j]*0.15, 'moving':True, 'stepsize':stepsize, 'subdir':False}
                            rotKerby = {'stage_key':rotKey, 'start':rotPos, 'moving':False, 'stepsize':0, 'subdir':True}
                            print(i,j,k)
                            scanList.append( {'args':[THzKerby.copy(), gateKerby.copy(), rotKerby.copy()], 'numSteps':numSteps, 'RDS':[i,j,k]} )
        return scanList

    def initializeScan(self, *args, numSteps = 3, RDS = None):
        # arg = {'index':stageIndex, 'start':startPosition, 'moving':True/False, 'stepsize':stepSize, 'controller':theControllerName}
        print('initialize ['+','.join([str(x) for x in RDS])+']')
        self.commandQueue = []
        movingKeys = []
        subdir = ''
        self.stageBoss.clearAllChildren()
        for arg in args:
            print(arg)
            stage_key = arg['stage_key']
            start = arg['start']
            self.commandQueue.append(self._lambMill(self._moveStageAbsolute, stage_key = stage_key, start = start))
            self.commandQueue.append(self._lambMill(self._safetyCheckpoint, stage_key))
            self.commandQueue.append(self._lambMill(self._update_stage_position, stage_key))
            if arg['moving']:
                movingKeys.append(stage_key)
                self._setStepsize(stage_key, arg['stepsize']) # instead of this we just have to set step size
                if stage_key == 'ESP1':
                    self.THzStart = start
            if arg['subdir']:
                subdir = '\\{0:.1f}'.format(start)
        self.commandQueue.append(self._lambMill(self._update_scan_numbers, r = RDS[0], d = RDS[1], s = RDS[2]))
        self.commandQueue.append(self._lambMill(self.hippo.startFile, subdir = subdir, r = RDS[0], d = RDS[1], s = RDS[2]))
        self.commandQueue.append(self.beginScan)
        self.commandQueue.append(self.appendData)
        self.commandQueue.append(self.updatePlot)
        for j in range(1,numSteps):
            for i in range(len(movingKeys)):
                self.commandQueue.append(self._lambMill(self._moveStep, stage_key = movingKeys[i]))
            self.commandQueue.append(self._lambMill(self._safetyCheckpoint, *movingKeys))
            self.commandQueue.append(self.appendData)
            self.commandQueue.append(self.updatePlot)
        self.commandQueue.append(self.stopScan)



    def _moveStageAbsolute(self, stage_key, start):
        self.stageBoss.moveStageAbsolute(stage_key, start)

    def xlimit_change(self, plot_canvas, index, value):
        plot_canvas.set_xlimit(index, value)

    def ylimit_change(self, plot_canvas, index, value, **kwargs):
        plot_canvas.set_ylimit(index, value, **kwargs)

    def closeEvent(self, event):
        self._widgetEnable(True)
        self._storeSettings()
        reply = QtWidgets.QMessageBox.question(self, 'Quit?',
                                     'Are you sure you want to quit?',
                                     QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            self._timer.stop()
            if not type(event) == bool:
                event.accept()
            else:
                sys.exit()
        else:
            if not type(event) == bool:
                event.ignore()

    def send_sms_update(self, t, temps):
        stringer = ''
        for key in temps:
            stringer = stringer + str(key) + ': ' + format(temps[key], '.2f') + ' K\n'
        self.sms.send(stringer, self.LE_phonenumber.text())

    def ttest(self, label = ''):
        t = time.monotonic()
        print(t - self.tt, label)

    def _recallSettings(self):
        try:
            # numbers
            self.sWidgets['THzsetposition'].setValue(float(self.settings.value('THzsetposition')))
            self.sWidgets['gatesetposition'].setValue(float(self.settings.value('gatesetposition')))
            self.sWidgets['prescan'].setValue(float(self.settings.value('prescan')))
            self.sWidgets['startnum'].setValue(self.settings.value('startnum'))
            self.sWidgets['stepsize'].setValue(float(self.settings.value('stepsize')))
            self.sWidgets['numsteps'].setValue(self.settings.value('numsteps'))
            self.sWidgets['scanperround'].setValue(self.settings.value('scanperround'))
            self.sWidgets['numrounds'].setValue(self.settings.value('numrounds'))
            # text
            self.sWidgets['delays'].setPlainText(self.settings.value('delays'))
            self.sWidgets['comments'].setPlainText(self.settings.value('comments'))
            self.sWidgets['extension'].setText(self.settings.value('extension'))
            self.sWidgets['path'].setText(self.settings.value('path'))
            self.sWidgets['filename'].setText(self.settings.value('filename'))
            self.sWidgets['scanmode'].setCurrentIndex(int(self.settings.value('scanmode')))
        except Exception as e:
            print(e)

    def _storeSettings(self):
        try:
            # numbers
            self.settings.setValue('THzsetposition', self.sWidgets['THzsetposition'].value())
            self.settings.setValue('gatesetposition', self.sWidgets['gatesetposition'].value())
            self.settings.setValue('prescan', self.sWidgets['prescan'].value())
            self.settings.setValue('startnum', self.sWidgets['startnum'].value())
            self.settings.setValue('stepsize', self.sWidgets['stepsize'].value())
            self.settings.setValue('numsteps', self.sWidgets['numsteps'].value())
            self.settings.setValue('scanperround', self.sWidgets['scanperround'].value())
            self.settings.setValue('numrounds', self.sWidgets['numrounds'].value())
            # text
            self.settings.setValue('delays', self.sWidgets['delays'].toPlainText())
            self.settings.setValue('comments', self.sWidgets['comments'].toPlainText())
            self.settings.setValue('extension', self.sWidgets['extension'].text())
            self.settings.setValue('path', self.sWidgets['path'].text())
            self.settings.setValue('filename', self.sWidgets['filename'].text())
            self.settings.setValue('scanmode', self.sWidgets['scanmode'].currentIndex())
        except Exception as e:
            print(e)

    def _threadWork(self, function, *onFinishFunctions):
        self.thread = QtCore.QThread(parent = self)
        self.worker = Worker(self, function)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        # Step 6: Start the thread
        self.thread.start()
        for finishFunction in onFinishFunctions:
            self.thread.finished.connect(finishFunction)

class HungryHungryHippo():
    def __init__(self, parent, delays, scanperround, numrounds, numsteps, path, filename, extension, startnum, comments):
        self.parent = parent
        self.delays = delays
        self.scanPerRound = scanperround
        self.numRounds = numrounds
        self.numSteps = numsteps
        self.path = path
        self.filename = filename
        self.extension = extension
        self.startnum = startnum
        self.di = 0
        self.si = 0
        self.ri = 0
        commentFile = self.openFile(comment = True)
        commentFile.write(comments)
        commentFile.close()

    def startFile(self, subdir = '', r = None, d = None, s = None):
        self.wto = self.openFile(comment = False, subdir = subdir, r = r, d = d, s = s)
        self.x = []
        self.y0 = []
        self.y1 = []

    def feedData(self, x, y0, y1):
        self.x.append(x)
        self.y0.append(y0)
        self.y1.append(y1)
        self.wto.write(format(x, '.4f') + ' ' + format(y0, '.4f') + ' ' + format(y1, '.4f') + '\n')

    def openFile(self, comment = False, subdir = '', r = None, d = None, s = None):
        if comment:
            fn = self.path + '//' + self.filename+'_comments'
        else:
            if os.path.exists(self.path + subdir):
                fn = self.path + subdir + '//' + self.filename+'_('+str(self.delays[d])+'_'+str(d)+'_'+str(r)+'_'+str(s)+')_'
            else:
                os.makedirs(self.path + subdir)
                fn = self.path + subdir + '//' + self.filename+'_('+str(self.delays[d])+'_'+str(d)+'_'+str(r)+'_'+str(s)+')_'
        i=0
        while os.path.exists(fn+self.extension):
            fn = fn + '_fs'+str(i)
            i+=1
        return open(fn + self.extension, 'w')
    
    def closeFile(self):
        self.wto.close()

class HungryMeasuring():
    def __init__(self, parent, delays, scanperround, numrounds, numsteps, path, filename, extension, startnum, comments):
        self.parent = parent
        self.delays = delays
        self.scanPerRound = scanperround
        self.numRounds = numrounds
        self.numSteps = numsteps
        self.path = path
        self.filename = filename
        self.extension = extension
        self.startnum = startnum
        self.di = 0
        self.si = 0
        self.ri = 0
        self.commentFile = self.openFile(comment = True)
        self.commentFile.write(comments)
        self.commentFile.close()
        self.newScan()

    def newScan(self):
        self.delay = self.delays[self.di]
        self.numScans = self.scanPerRound[self.di]
        self.wto = self.openFile()
        self.x = []
        self.y0 = []
        self.y1 = []

    def feedData(self, x, y0, y1):
        self.x.append(x)
        self.y0.append(y0)
        self.y1.append(y1)
        self.wto.write(format(x, '.4f') + ' ' + format(y0, '.4f') + ' ' + format(y1, '.4f') + '\n')
        if len(self.x) == self.numSteps:
            self.toSend.append(max(self.y0))
            self.wto.close()
            self.si += 1
            if self.si >= self.numScans:
                try:
                    #self.sms.send(' scans done: ' + format(sum(self.toSend)/len(self.toSend), '.4f'), self.number)
                    self.toSendAvgs.append(sum(self.toSend)/len(self.toSend))
                    self.toSend = []
                except:
                    pass
                self.di += 1
                self.si = 0
                if self.di >= len(self.delays):
                    try:
                        strtr = ''
                        for avg in self.toSendAvgs:
                            strtr = strtr + ' ' + format(avg, '.3f')
                        self.sms.send(' round done: ' + strtr, self.number)
                        self.toSendAvgs = []
                    except:
                        pass
                    self.di = 0
                    self.ri += 1
                    if self.ri >= self.numRounds:
                        self.parent.stop()
            self.newScan()
            return True, self.delays[self.di], self.di, self.si, self.ri
        else:
            return False, self.delays[self.di], self.di, self.si, self.ri

    def openFile(self, comment = False):
        if comment:
            fn = self.path + '//' + self.filename+'_comments'
        else:
            fn = self.path + '//' + self.filename+'_('+str(self.delays[self.di])+'_'+str(self.di)+'_'+str(self.ri)+'_'+str(self.si)+')_'
        i=0
        while os.path.exists(fn+self.extension):
            fn = fn + '_fs'+str(i)
            i+=1
        return open(fn + self.extension, 'w')
    
    def closeFile(self):
        self.wto.close()

class Worker(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    def __init__(self, parent, function):
        super(Worker, self).__init__()
        self.parent = parent
        self.function = function
        
    def run(self):
        self.function()
        self.finished.emit()

class cuteWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    def __init__(self, parent, plot):
        super(cuteWorker, self).__init__()
        self.parent = parent
        self.plot = plot
        
    def run(self, x, y):
        self.plot.updateCanvas(x, y)
        self.plot._drawPlot()