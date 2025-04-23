import os
import sys
import matplotlib
matplotlib.use('Qt5Agg')
import numpy as np
from PyQt5 import QtCore, QtWidgets
from PyQt5 import uic
import appClasses as dd
import time

class DLscanWindow(QtWidgets.QWidget):
    def __init__(self, parent, whoami = 'DLscan'):
        QtWidgets.QWidget.__init__(self)
        self.ui = uic.loadUi('scansV4p0.ui',self)
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

        
        line_dict = {1:{'X':{'color':'tab:orange', 'alpha':.75},'Y':{'color':'tab:orange', 'alpha':.75, 'linestyle':'dashed'}}, 
                     2:{'X':{'color':'tab:red', 'alpha':.64},'Y':{'color':'tab:red', 'alpha':.64, 'linestyle':'dashed'}}}
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

            self.sWidgets = {'THzsetposition':self.SB_THzPos, 'gatesetposition':self.SB_gatePos, 'THzsetpositionref':self.SB_THzRefPos, 'gatesetpositionref':self.SB_gateRefPos,
                             'set2currentrefscan':self.PB_set2currentRef, 
                             'THzposition':self.LE_THzCurrent, 'gateposition':self.LE_gateCurrent, 
                             'prescan':self.SB_prescan, 'delays':self.TE_delays, 
                             'start':self.PB_start, 'comments':self.TE_comments, 'extension':self.LE_extension, 'startnum':self.SB_startnum, 'filename':self.LE_filename, 'path':self.LE_path, 'browse':self.PB_browse, 'stop':self.PB_stop, 
                             'stepsize':self.SB_stepSize, 'numsteps':self.SB_numSteps, 
                             'THzkey':self.CB_THzKey, 'gatekey':self.CB_gateKey, 'rotkey':self.CB_rotKey, 'rotposition':self.LE_rotCurrent,
                             'numrounds':self.SB_numRounds, 
                             'round':self.LE_round, 'delay':self.LE_delay, 'scan':self.LE_scan,
                             'set2current':self.PB_set2current, 'scanmode':self.CB_scanMode,
                             'xkey':self.CB_xKey, 'xposition':self.LE_xPosCurrent, 'xsampposition':self.SB_xPosSample, 'xrefposition':self.SB_xPosReference, 
                             'ykey':self.CB_yKey, 'yposition':self.LE_yPosCurrent, 'ysampposition':self.SB_yPosSample, 'yrefposition':self.SB_yPosReference, 
                             'set2currentsamp':self.PB_set2currentSample, 'set2currentref':self.PB_set2currentReference,
                             'xlogunit':self.CB_xLogUnit, 'updatepositions':self.PB_updatePositions, 'heatercontrol':self.CB_heaterControl, 'heaterpath':self.LE_heaterSettings}


            # why didn't this work in a for loop :(
            self.sWidgets['start'].clicked.connect(self._start)
            self.sWidgets['stop'].clicked.connect(self.stop)
            self.sWidgets['browse'].clicked.connect(self._browse)
            self.sWidgets['set2current'].clicked.connect( self._set2current )
            self.sWidgets['set2currentrefscan'].clicked.connect( self._set2currentRefScan )
            self.sWidgets['set2currentsamp'].clicked.connect( self._set2currentSample )
            self.sWidgets['set2currentref'].clicked.connect( self._set2currentReference )
            self.sWidgets['updatepositions'].clicked.connect( self._updateAllPositions )
            


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
        self.connectedStages = self.stageBoss.keys()
        for widgetKey in ['THzkey', 'gatekey', 'rotkey', 'xkey', 'ykey']:
            self.sWidgets[widgetKey].clear()
            self.sWidgets[widgetKey].addItems(self.connectedStages)
            self.sWidgets[widgetKey].addItems(['null'])
        self._recallStageKeys()
        self.timeConstants = [0,0]
        for key in self.lockins:
            self.timeConstants[key-1] = self._timeConstantList[self.lockins[key].get_time_constant()]
        self.x = []
        self.y = {}
        self.y[1] = {'X':[], 'Y':[]}
        self.y[2] = {'X':[], 'Y':[]}
        for key in self.lockins:
            self.y[key]['X'].append(self._get_measurement(self.lockins[key], 'X'))
            self.y[key]['Y'].append(self._get_measurement(self.lockins[key], 'Y'))
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

    def _update_stage_position(self, *stage_keys):
        for stage_key in stage_keys:
            if stage_key != 'null':
                self.stageBoss.updateStagePosition(stage_key)
                if stage_key == self.sWidgets['THzkey'].currentText():
                    self.sWidgets['THzposition'].setText(format(self.stageBoss.getStagePosition(stage_key), '.4f'))
                elif stage_key == self.sWidgets['gatekey'].currentText():
                    self.sWidgets['gateposition'].setText(format(self.stageBoss.getStagePosition(stage_key), '.4f'))
                elif stage_key == self.sWidgets['xkey'].currentText():
                    self.sWidgets['xposition'].setText(format(self.stageBoss.getStagePosition(stage_key), '.4f'))
                elif stage_key == self.sWidgets['ykey'].currentText():
                    self.sWidgets['yposition'].setText(format(self.stageBoss.getStagePosition(stage_key), '.4f'))
                elif stage_key == self.sWidgets['rotkey'].currentText():
                    self.sWidgets['rotposition'].setText(format(self.stageBoss.getStagePosition(stage_key), '.4f'))
                else:
                    pass
            else:
                pass

    def _updateAllPositions(self):
        for stage_key in self.connectedStages:
            if stage_key != 'null':
                self.stageBoss.updateStagePosition(stage_key)
                if stage_key == self.sWidgets['THzkey'].currentText():
                    self.sWidgets['THzposition'].setText(format(self.stageBoss.getStagePosition(stage_key), '.4f'))
                elif stage_key == self.sWidgets['gatekey'].currentText():
                    self.sWidgets['gateposition'].setText(format(self.stageBoss.getStagePosition(stage_key), '.4f'))
                elif stage_key == self.sWidgets['xkey'].currentText():
                    self.sWidgets['xposition'].setText(format(self.stageBoss.getStagePosition(stage_key), '.4f'))
                elif stage_key == self.sWidgets['ykey'].currentText():
                    self.sWidgets['yposition'].setText(format(self.stageBoss.getStagePosition(stage_key), '.4f'))
                elif stage_key == self.sWidgets['rotkey'].currentText():
                    self.sWidgets['rotposition'].setText(format(self.stageBoss.getStagePosition(stage_key), '.4f'))
                else:
                    pass
            else:
                pass

    def _browse(self):
        fname = QtWidgets.QFileDialog.getSaveFileName(self, ' Select Log File ', r'C:\Data\THz')
        print(fname[0])
        print(fname[0].split('/')[-1])
        self.sWidgets['filename'].setText(fname[0].split('/')[-1])
        self.sWidgets['path'].setText(fname[0][:len(fname[0])-len(fname[0].split('/')[-1])].strip('/'))

    def appendData(self):
        readIn = []
        for key in self.lockins:
            yX = self._get_measurement(self.lockins[key], 'X')
            yY = self._get_measurement(self.lockins[key], 'Y')
            readIn.append(tuple([yX,yY]))
            self.y[key]['X'].append(yX)
            self.y[key]['Y'].append(yY)
        if len(readIn) > 1:
            y1X, y1Y = readIn[0]
            y2X, y2Y = readIn[1]
        else:
            y1X, y1Y = readIn[0]
            y2X, y2Y = tuple([0.0,0.0])
            self.y[2]['X'].append(y2X)
            self.y[2]['Y'].append(y2Y)
        self._update_stage_position(*self.movingKeys)
        if self.logUnit == 'ps':
            x = self.pn*(self.stageBoss.getStagePosition(self.xLeadKey) - self.startPos)/.15
        elif self.logUnit == 'deg':
            x = self.pn*(self.stageBoss.getStagePosition(self.xLeadKey) - self.startPos)
        self.x.append(x)
        if self.logActive:
            self.hippo.feedData(x, y1X, y1Y, y2X, y2Y)


    def _get_measurement(self, lockin, output):
        return lockin.get_specific_output(output)

    def _set2current(self):
        try:
            THzKey = str(self.sWidgets['THzkey'].currentText())
            self.sWidgets['THzsetposition'].setValue(self.stageBoss.getStagePosition(THzKey))
            gateKey = str(self.sWidgets['gatekey'].currentText())
            self.sWidgets['gatesetposition'].setValue(self.stageBoss.getStagePosition(gateKey))
        except Exception as e:
            print(e)

    def _set2currentRefScan(self):
        try:
            THzKey = str(self.sWidgets['THzkey'].currentText())
            self.sWidgets['THzsetpositionref'].setValue(self.stageBoss.getStagePosition(THzKey))
            gateKey = str(self.sWidgets['gatekey'].currentText())
            self.sWidgets['gatesetpositionref'].setValue(self.stageBoss.getStagePosition(gateKey))
        except Exception as e:
            print(e)

    def _set2currentSample(self):
        try:
            xkey = str(self.sWidgets['xkey'].currentText())
            if xkey != 'null':
                self.sWidgets['xsampposition'].setValue(self.stageBoss.getStagePosition(xkey))
            ykey = str(self.sWidgets['ykey'].currentText())
            if ykey != 'null':
                self.sWidgets['ysampposition'].setValue(self.stageBoss.getStagePosition(ykey))
        except Exception as e:
            print(e)
    
    def _set2currentReference(self):
        try:
            xkey = str(self.sWidgets['xkey'].currentText())
            if xkey != 'null':
                self.sWidgets['xrefposition'].setValue(self.stageBoss.getStagePosition(xkey))
            ykey = str(self.sWidgets['ykey'].currentText())
            if ykey != 'null':
                self.sWidgets['yrefposition'].setValue(self.stageBoss.getStagePosition(ykey))
        except Exception as e:
            print(e)


    def _widgetEnable(self, bool):
        for k in ['THzsetposition', 'gatesetposition', 'THzsetpositionref', 'gatesetpositionref', 'set2currentref', 'prescan', 'delays', 'start', 'comments', 'extension', 'startnum', 'numrounds', 'set2current', 'stepsize', 'filename', 'path', 'browse', 'numsteps', 'scanmode', 'xsampposition', 'ysampposition', 'xrefposition', 'yrefposition', 'updatepositions', 'THzkey', 'gatekey', 'rotkey', 'xkey', 'ykey', 'set2currentsamp', 'set2currentref', 'xlogunit', 'heaterpath', 'heatercontrol']:
            self.sWidgets[k].setEnabled(bool)

    def _start(self):
        try:
            self.firstTime = True
            for key in self.lockins:
                self._sensitivityChange(key, self.lockins[key].get_sensitivity())
                self.timeConstants[key-1] = self._timeConstantList[self.lockins[key].get_time_constant()]
            self.parent.scanStart()
            if self.sWidgets['heatercontrol'].isChecked():
                self.scanParseList = self._parseDelaysHeater()
                self.delays, self.numScans = self.scanParseList[0]['delays'], self.scanParseList[0]['numScans']
                print(self.scanParseList)
                self.rotPositions = self._parseRotationPositions()
                self.srPositions = self._parseSampRefPositions()
                comments = self._buildComments()
                self.heaterFilepath = self.sWidgets['heaterpath'].text()
                self.hippo = HungryHungryHippo(self, self.delays, self.numScans, self.sWidgets['numrounds'].value(), self.sWidgets['numsteps'].value(), self.sWidgets['path'].text(), self.sWidgets['filename'].text(), self.sWidgets['extension'].text(), self.sWidgets['startnum'].value(), comments)
                self.scanList = self.buildScansHeat(self.sWidgets['THzsetposition'].value(), self.sWidgets['THzsetpositionref'].value(), str(self.sWidgets['THzkey'].currentText()), self.sWidgets['gatesetposition'].value(), self.sWidgets['gatesetpositionref'].value(), str(self.sWidgets['gatekey'].currentText()), self.scanParseList, self.sWidgets['stepsize'].value(), self.sWidgets['numsteps'].value(), self.sWidgets['prescan'].value(), self.sWidgets['numrounds'].value(), str(self.sWidgets['xkey'].currentText()), str(self.sWidgets['ykey'].currentText()), self.srPositions, typo = str(self.CB_scanType.currentText()), xUnit = str(self.sWidgets['xlogunit'].currentText()))
            else:
                self.delays, self.numScans = self._parseDelays()
                self.rotPositions = self._parseRotationPositions()
                self.srPositions = self._parseSampRefPositions()
                comments = self._buildComments()
                self.heaterFilepath = self.sWidgets['heaterpath'].text()
                self.hippo = HungryHungryHippo(self, self.delays, self.numScans, self.sWidgets['numrounds'].value(), self.sWidgets['numsteps'].value(), self.sWidgets['path'].text(), self.sWidgets['filename'].text(), self.sWidgets['extension'].text(), self.sWidgets['startnum'].value(), comments)
                self.scanList = self.buildScans(self.sWidgets['THzsetposition'].value(), self.sWidgets['THzsetpositionref'].value(), str(self.sWidgets['THzkey'].currentText()), self.sWidgets['gatesetposition'].value(), self.sWidgets['gatesetpositionref'].value(), str(self.sWidgets['gatekey'].currentText()), self.delays, self.numScans, self.sWidgets['stepsize'].value(), self.sWidgets['numsteps'].value(), self.sWidgets['prescan'].value(), self.sWidgets['numrounds'].value(), str(self.sWidgets['rotkey'].currentText()), self.rotPositions, str(self.sWidgets['xkey'].currentText()), str(self.sWidgets['ykey'].currentText()), self.srPositions, typo = str(self.CB_scanType.currentText()), xUnit = str(self.sWidgets['xlogunit'].currentText()))
            print('scanList created')
            self.xlimit_change(self.plot, 0, 0)
            self.xlimit_change(self.plot, 1, self.sWidgets['numsteps'].value()*self.sWidgets['stepsize'].value()/.15/1000)
            self.x = []
            self.y[1] = {'X':[], 'Y':[]}
            self.y[2] = {'X':[], 'Y':[]}
            self._widgetEnable(False)
            scanDict = self.scanList.pop(0)
            self.initializeScan(*scanDict['args'], numSteps = scanDict['numSteps'], RDS = scanDict['RDS'], scanType = scanDict['scanType'])
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
        self.y[1] = {'X':[], 'Y':[]}
        self.y[2] = {'X':[], 'Y':[]}
        self.started = True

    def stopScan(self):
        self.started = False
        if self.logActive:
            self.hippo.closeFile()
        if len(self.scanList) < 1:
            self.stop()
        else:
            scanDict = self.scanList.pop(0)
            self.initializeScan(*scanDict['args'], numSteps = scanDict['numSteps'], RDS = scanDict['RDS'], scanType = scanDict['scanType'])
            while self.started != True:
                self.executeQueue()

    def _buildComments(self):
        delays = self.sWidgets['delays'].toPlainText()
        comments = self.sWidgets['comments'].toPlainText()
        stuff = 'rounds: ' + str(self.sWidgets['numrounds'].value()) + '    ' + 'steps: ' + str(self.sWidgets['numsteps'].value()) + '    ' + 'stepsize: ' + format(self.sWidgets['stepsize'].value(), '.4f')
        positions = 'THzSet: ' + format(self.sWidgets['THzsetposition'].value(), '.4f') + '    ' + 'gateSet: '+format(self.sWidgets['gatesetposition'].value(), '.4f') + '    ' + 'prescan: '+format(self.sWidgets['prescan'].value(), '.4f') + '      scanmode: ' + self.sWidgets['scanmode'].currentText()
        positions2 = 'THzSetRef: ' + format(self.sWidgets['THzsetpositionref'].value(), '.4f') + '    ' + 'gateSetRef: '+format(self.sWidgets['gatesetpositionref'].value(), '.4f') 
        samplePositions = 'samplePosition: ({0:.4f}, {1:.4f})    referencePosition: ({2:.4f}, {3:.4f})'.format(self.sWidgets['xsampposition'].value(), self.sWidgets['ysampposition'].value(), self.sWidgets['xrefposition'].value(), self.sWidgets['yrefposition'].value())
        theboy = self.sWidgets['filename'].text() + '\n' + delays + '\n' + comments + '\n' + stuff + '\n' + positions + '\n' + positions2 + '\n' + samplePositions
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
    
    def _parseDelaysHeater(self):
        text = self.sWidgets['delays'].toPlainText()
        tl = text.split('], ')
        scanParseList = []
        for item in tl:
            atTemp = item.strip('][ ').split(':')
            thisHeatCommand = atTemp[0].split('), ')
            heaterCommand = []
            for heatCom in thisHeatCommand:
                yessir = heatCom.strip('()').split(', ')
                heaterCommand.append([float(yessir[0]), int(yessir[1]), float(yessir[2])*60])
            delays = []
            numScans = []
            for scanStuff in atTemp[1].split(', '):
                delays.append(float(scanStuff.split('_')[0]))
                numScans.append(int(scanStuff.split('_')[1]))
            scanParseList.append({'delays':delays, 'numScans':numScans, 'heater':heaterCommand})
        return scanParseList
    
    def _parseRotationPositions(self):
        text = self.LE_rotPos.text()
        tl = text.split(', ')
        rotationPositions = []
        for item in tl:
            rotationPositions.append(float(item))
        print(rotationPositions)
        return rotationPositions
    
    def _parseSampRefPositions(self):
        sampPos = [self.sWidgets['xsampposition'].value(), self.sWidgets['ysampposition'].value()]
        refPos = [self.sWidgets['xrefposition'].value(), self.sWidgets['yrefposition'].value()]
        return [sampPos, refPos]

    def stop(self):
        print('stop')
        self._widgetEnable(True)
        self._storeSettings()
        self.started = False
        self.hippo.closeFile()
        self.parent.scanEnd()

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

    def _safetyCheckpoint(self, *stage_keys, bonusMod = 1.0, sleepTime = 0):
        if True in [self.stageBoss.moving(stage_key) for stage_key in stage_keys]:
            time.sleep(sleepTime)
            self.commandQueue.insert(0, self._lambMill(self._safetyCheckpoint, *stage_keys))
        else:
            if self.stageJustMoved == True:
                self.timeStageEnd = time.monotonic()
                self.stageJustMoved = False
                time.sleep(sleepTime)
                self.commandQueue.insert(0, self._lambMill(self._safetyCheckpoint, *stage_keys))
            elif time.monotonic() - self.timeStageEnd < (bonusMod*self.parent.TCcof*max(self.timeConstants) + self.parent.TCadd):
                time.sleep(sleepTime)
                self.commandQueue.insert(0, self._lambMill(self._safetyCheckpoint, *stage_keys))
            else:
                pass

    def _heaterSafetyCheckpoint(self, waitTime, startedNow = True):
        self.waitTime = waitTime
        if startedNow:
            self.heaterWaitStart = time.monotonic()
            time.sleep(5)
            self.commandQueue.insert(0, self._lambMill(self._heaterSafetyCheckpoint, waitTime, False))
        else:
            if time.monotonic() - self.heaterWaitStart < waitTime:
                time.sleep(5)
                self.LE_tempWait.setText('{:0.2f}'.format((waitTime - (time.monotonic() - self.heaterWaitStart))/60))
                print('time left: {:0.2f}'.format((waitTime - (time.monotonic() - self.heaterWaitStart))/60))
                self.commandQueue.insert(0, self._lambMill(self._heaterSafetyCheckpoint, waitTime, False))
                #self.commandQueue.insert(0, self._lambMill(self._update_temp_wait, (waitTime - (time.monotonic() - self.heaterWaitStart))/60))
            else:
                self.LE_tempWait.setText('{:0.2f}'.format(0.00))
                #self.commandQueue.insert(0, self._lambMill(self._update_temp_wait, 0.00))
                pass

    def _changeTemperature(self, setTemp, heaterSetting):
        self.adjustHeater(setTemp, heaterSetting)

    def adjustHeater(self, setTemp, heaterSetting):
        filepath = self.heaterFilepath
        try:
            with open(filepath, 'r') as file:
                content = file.readlines()

            if content:
                with open(filepath, 'w') as file:
                    file.write(r'{"A": {"HEAT_RANGE": ' + str(heaterSetting) + r', "SETPOINT": ' + '{:0.2f}'.format(setTemp) + r'} }' + '\n')
                    file.writelines(content[1:])
            else:
                with open(filepath, 'w') as file:
                    file.write(r'{"A": {"HEAT_RANGE": ' + str(heaterSetting) + r', "SETPOINT": ' + '{:0.2f}'.format(setTemp) + r'} }' + '\n')
                    
        except FileNotFoundError:
            print(f"Error: File not found at {filepath}")
        except Exception as e:
            print(f"An error occurred: {e}")

    def _lambMill(self, func, *args, **kwargs):
        return lambda:func(*args, **kwargs)

    def _update_scan_numbers(self, r, d, s):
        self.sWidgets['round'].setText(str(r))
        self.sWidgets['delay'].setText(format(self.delays[d], '.2f'))
        self.sWidgets['scan'].setText(str(s))

    def _update_temp_wait(self, wait):
        self.LE_tempWait.setText('{:0.2f}'.format(wait))

    def buildScansHeat(self, THzStart, THzStartRef, THzKey, gateStart, gateStartRef, gateKey, scanParseList, stepsize, numSteps, prescan, numRounds, xKey, yKey, srPositions, typo = 'THz', xUnit = 'ps'):
        scanList = []
        self.logUnit = xUnit
        print(typo)
        THzPositions = [THzStart, THzStartRef]
        gatePositions = [gateStart, gateStartRef]
        first = True
        if typo == 'THz_equ':
            dirnames = ['samp', 'ref']
            for i in range(numRounds):
                for scanControl in scanParseList:
                    delays = scanControl['delays']
                    numScans = scanControl['numScans']
                    heatCommands = scanControl['heater']
                    scanningTemp = heatCommands[-1][0]
                    if first:
                        first = False
                    else:
                        for hcom in heatCommands:
                            setTemp = hcom[0]
                            heaterSetting = hcom[1]
                            waitTime = hcom[2]
                            scanList.append( {'args':[setTemp, heaterSetting, waitTime, delays], 'numSteps':numSteps, 'RDS':None, 'scanType':'temperatureControl'} )
                    for j in range(len(delays)):
                        for jj in range(len(srPositions)):
                            if jj == 0:
                                for k in range(numScans[j]):
                                    startPosTHz = THzPositions[jj]
                                    startPosGate = gatePositions[jj]
                                    THzKerby = {'stage_key':THzKey, 'start':startPosTHz - prescan - delays[j]*0.15, 'moving':True, 'stepsize':stepsize, 'subdir':False, 'subdirname':None}
                                    gateKerby = {'stage_key':gateKey, 'start':startPosGate - delays[j]*0.15, 'moving':False, 'stepsize':0, 'subdir':False, 'subdirname':None}
                                    xKerby = {'stage_key':xKey, 'start':srPositions[jj][0], 'moving':False, 'stepsize':0, 'subdir':True, 'subdirname':'{:0.1f}K_'.format(scanningTemp)+dirnames[jj]}
                                    #yKerby = {'stage_key':yKey, 'start':srPositions[jj][1], 'moving':False, 'stepsize':0, 'subdir':False}
                                    print(i,j,k, scanningTemp, delays[j])
                                    scanList.append( {'args':[THzKerby.copy(), gateKerby.copy(), xKerby.copy()], 'numSteps':numSteps, 'RDS':[i,j,k], 'scanType':'sample-reference'} )
                            else:
                                k=0
                                startPosTHz = THzPositions[jj]
                                startPosGate = gatePositions[jj]
                                THzKerby = {'stage_key':THzKey, 'start':startPosTHz - prescan - delays[j]*0.15, 'moving':True, 'stepsize':stepsize, 'subdir':False, 'subdirname':None}
                                gateKerby = {'stage_key':gateKey, 'start':startPosGate - delays[j]*0.15, 'moving':False, 'stepsize':0, 'subdir':False, 'subdirname':None}
                                xKerby = {'stage_key':xKey, 'start':srPositions[jj][0], 'moving':False, 'stepsize':0, 'subdir':True, 'subdirname':'{:0.1f}K_'.format(scanningTemp)+dirnames[jj]}
                                #yKerby = {'stage_key':yKey, 'start':srPositions[jj][1], 'moving':False, 'stepsize':0, 'subdir':False}
                                print(i,j,k, scanningTemp, delays[j])
                                scanList.append( {'args':[THzKerby.copy(), gateKerby.copy(), xKerby.copy()], 'numSteps':numSteps, 'RDS':[i,j,k], 'scanType':'sample-reference'} )
        if typo == 'THz_2stage':
            for i in range(numRounds):
                for scanControl in scanParseList:
                    delays = scanControl['delays']
                    numScans = scanControl['numScans']
                    heatCommands = scanControl['heater']
                    scanningTemp = heatCommands[-1][0]
                    if first:
                        first = False
                    else:
                        for hcom in heatCommands:
                            setTemp = hcom[0]
                            heaterSetting = hcom[1]
                            waitTime = hcom[2]
                            scanList.append( {'args':[setTemp, heaterSetting, waitTime, delays], 'numSteps':numSteps, 'RDS':None, 'scanType':'temperatureControl'} )
                    for j in range(len(delays)):
                        for k in range(numScans[j]):
                            THzKerby = {'stage_key':THzKey, 'start':THzStart - prescan - delays[j]*0.15, 'moving':True, 'stepsize':stepsize, 'subdir':False}
                            gateKerby = {'stage_key':gateKey, 'start':gateStart - delays[j]*0.15, 'moving':False, 'stepsize':0, 'subdir':True, 'subdirname':'{:0.1f}K'.format(scanningTemp)}
                            #rotKerby = {'stage_key':rotKey, 'start':rotPos, 'moving':False, 'stepsize':0, 'subdir':True}
                            print(i,j,k, scanningTemp, delays[j])
                            scanList.append( {'args':[THzKerby.copy(), gateKerby.copy()], 'numSteps':numSteps, 'RDS':[i,j,k], 'scanType':'norm'} )
        return scanList

    def buildScans(self, THzStart, THzStartRef, THzKey, gateStart, gateStartRef, gateKey, delays, numScans, stepsize, numSteps, prescan, numRounds, rotKey, rotPositions, xKey, yKey, srPositions, typo = 'THz', xUnit = 'ps'):
        scanList = []
        self.logUnit = xUnit
        print(typo)
        THzPositions = [THzStart, THzStartRef]
        gatePositions = [gateStart, gateStartRef]
        if typo == 'THz_equV1':
            dirnames = ['samp', 'ref']
            for i in range(numRounds):
                for j in range(len(delays)):
                    for jj in range(len(srPositions)):
                        for k in range(numScans[j]):
                            startPosTHz = THzPositions[jj]
                            startPosGate = gatePositions[jj]
                            THzKerby = {'stage_key':THzKey, 'start':startPosTHz - prescan - delays[j]*0.15, 'moving':True, 'stepsize':stepsize, 'subdir':False, 'subdirname':None}
                            gateKerby = {'stage_key':gateKey, 'start':startPosGate - delays[j]*0.15, 'moving':False, 'stepsize':0, 'subdir':False, 'subdirname':None}
                            xKerby = {'stage_key':xKey, 'start':srPositions[jj][0], 'moving':False, 'stepsize':0, 'subdir':True, 'subdirname':dirnames[jj]}
                            #yKerby = {'stage_key':yKey, 'start':srPositions[jj][1], 'moving':False, 'stepsize':0, 'subdir':False}
                            print(i,j,jj,k)
                            scanList.append( {'args':[THzKerby.copy(), gateKerby.copy(), xKerby.copy()], 'numSteps':numSteps, 'RDS':[i,j,k], 'scanType':'sample-reference'} )
        if typo == 'THz_equ':
            dirnames = ['samp', 'ref']
            for i in range(numRounds):
                for j in range(len(delays)):
                    for jj in range(len(srPositions)):
                        if jj == 0:
                            for k in range(numScans[j]):
                                startPosTHz = THzPositions[jj]
                                startPosGate = gatePositions[jj]
                                THzKerby = {'stage_key':THzKey, 'start':startPosTHz - prescan - delays[j]*0.15, 'moving':True, 'stepsize':stepsize, 'subdir':False, 'subdirname':None}
                                gateKerby = {'stage_key':gateKey, 'start':startPosGate - delays[j]*0.15, 'moving':False, 'stepsize':0, 'subdir':False, 'subdirname':None}
                                xKerby = {'stage_key':xKey, 'start':srPositions[jj][0], 'moving':False, 'stepsize':0, 'subdir':True, 'subdirname':dirnames[jj]}
                                #yKerby = {'stage_key':yKey, 'start':srPositions[jj][1], 'moving':False, 'stepsize':0, 'subdir':False}
                                print(i,j,jj,k)
                                scanList.append( {'args':[THzKerby.copy(), gateKerby.copy(), xKerby.copy()], 'numSteps':numSteps, 'RDS':[i,j,k], 'scanType':'sample-reference'} )
                        else:
                            k=0
                            startPosTHz = THzPositions[jj]
                            startPosGate = gatePositions[jj]
                            THzKerby = {'stage_key':THzKey, 'start':startPosTHz - prescan - delays[j]*0.15, 'moving':True, 'stepsize':stepsize, 'subdir':False, 'subdirname':None}
                            gateKerby = {'stage_key':gateKey, 'start':startPosGate - delays[j]*0.15, 'moving':False, 'stepsize':0, 'subdir':False, 'subdirname':None}
                            xKerby = {'stage_key':xKey, 'start':srPositions[jj][0], 'moving':False, 'stepsize':0, 'subdir':True, 'subdirname':dirnames[jj]}
                            #yKerby = {'stage_key':yKey, 'start':srPositions[jj][1], 'moving':False, 'stepsize':0, 'subdir':False}
                            print(i,j,jj,k)
                            scanList.append( {'args':[THzKerby.copy(), gateKerby.copy(), xKerby.copy()], 'numSteps':numSteps, 'RDS':[i,j,k], 'scanType':'sample-reference'} )
        if typo == 'THz':
            dirnames = ['samp', 'ref']
            for i in range(numRounds):
                for j in range(len(delays)):
                    for k in range(numScans[j]):
                        THzKerby = {'stage_key':THzKey, 'start':startPosTHz - prescan - delays[j]*0.15, 'moving':True, 'stepsize':stepsize, 'subdir':False, 'subdirname':None}
                        gateKerby = {'stage_key':gateKey, 'start':startPosGate - delays[j]*0.15, 'moving':False, 'stepsize':0, 'subdir':False, 'subdirname':None}
                        #xKerby = {'stage_key':xKey, 'start':srPositions[jj][0], 'moving':False, 'stepsize':0, 'subdir':True, 'subdirname':dirnames[jj]}
                        #yKerby = {'stage_key':yKey, 'start':srPositions[jj][1], 'moving':False, 'stepsize':0, 'subdir':False}
                        print(i,j,jj,k)
                        scanList.append( {'args':[THzKerby.copy(), gateKerby.copy()], 'numSteps':numSteps, 'RDS':[i,j,k], 'scanType':'norm'} )
        if typo == 'THzOG':
            for i in range(numRounds):
                for rotPos in rotPositions:
                    for j in range(len(delays)):
                        for k in range(numScans[j]):
                            THzKerby = {'stage_key':THzKey, 'start':THzStart - prescan - delays[j]*0.15, 'moving':True, 'stepsize':stepsize, 'subdir':False}
                            gateKerby = {'stage_key':gateKey, 'start':gateStart - delays[j]*0.15, 'moving':False, 'stepsize':0, 'subdir':False}
                            rotKerby = {'stage_key':rotKey, 'start':rotPos, 'moving':False, 'stepsize':0, 'subdir':True}
                            print(i,j,k)
                            scanList.append( {'args':[THzKerby.copy(), gateKerby.copy(), rotKerby.copy()], 'numSteps':numSteps, 'RDS':[i,j,k], 'scanType':'norm'} )
        if typo == 'THz_2stage':
            for i in range(numRounds):
                for j in range(len(delays)):
                    for k in range(numScans[j]):
                        THzKerby = {'stage_key':THzKey, 'start':THzStart - prescan - delays[j]*0.15, 'moving':True, 'stepsize':stepsize, 'subdir':False}
                        gateKerby = {'stage_key':gateKey, 'start':gateStart - delays[j]*0.15, 'moving':False, 'stepsize':0, 'subdir':False}
                        #rotKerby = {'stage_key':rotKey, 'start':rotPos, 'moving':False, 'stepsize':0, 'subdir':True}
                        print(i,j,k)
                        scanList.append( {'args':[THzKerby.copy(), gateKerby.copy()], 'numSteps':numSteps, 'RDS':[i,j,k], 'scanType':'norm'} )
        if typo == 'POPF':
            for i in range(numRounds):
                for rotPos in rotPositions:
                    for j in range(len(delays)):
                        for k in range(numScans[j]):
                            THzKerby = {'stage_key':THzKey, 'start':THzStart - delays[j]*0.15, 'moving':True, 'stepsize':stepsize, 'subdir':False}
                            gateKerby = {'stage_key':gateKey, 'start':gateStart - delays[j]*0.15, 'moving':True, 'stepsize':stepsize, 'subdir':False}
                            rotKerby = {'stage_key':rotKey, 'start':rotPos, 'moving':False, 'stepsize':0, 'subdir':True}
                            print(i,j,k)
                            if k == 0:
                                scanList.append( {'args':[THzKerby.copy(), gateKerby.copy(), rotKerby.copy()], 'numSteps':numSteps, 'RDS':[i,j,k], 'scanType':'peakFinder'} )
                            scanList.append( {'args':[THzKerby.copy(), gateKerby.copy(), rotKerby.copy()], 'numSteps':numSteps, 'RDS':[i,j,k], 'scanType':'POP'} )

        elif typo == 'po':
            if True:
                rotPositions = [0]
            for i in range(numRounds):
                for rotPos in rotPositions:
                    for j in range(len(delays)):
                        for k in range(numScans[j]):
                            THzKerby = {'stage_key':THzKey, 'start':THzStart - delays[j]*0.15, 'moving':True, 'stepsize':stepsize, 'subdir':False}
                            gateKerby = {'stage_key':gateKey, 'start':gateStart - delays[j]*0.15, 'moving':True, 'stepsize':stepsize, 'subdir':False}
                            if False:
                                rotKerby = {'stage_key':rotKey, 'start':rotPos, 'moving':False, 'stepsize':0, 'subdir':True}
                                print(i,j,k)
                                scanList.append( {'args':[THzKerby.copy(), gateKerby.copy(), rotKerby.copy()], 'numSteps':numSteps, 'RDS':[i,j,k], 'scanType':'POP'} )
                            else:
                                scanList.append( {'args':[THzKerby.copy(), gateKerby.copy()], 'numSteps':numSteps, 'RDS':[i,j,k], 'scanType':'POP'} )
        return scanList

    def initializeScan(self, *args, numSteps = 3, RDS = None, scanType = 'norm'):
        print(scanType, ' ', RDS)
        self.movingKeys = []
        self.commandQueue = []
        self.stageBoss.clearAllChildren()
        self.logActive = True
        self.tempControl = False
        self.xlimit_change(self.plot, 0, 0)
        self.xlimit_change(self.plot, 1, self.sWidgets['numsteps'].value()*self.sWidgets['stepsize'].value()/.15/1000)
        if scanType == 'temperatureControl':
            print('changing temp')
            self.tempControl = True
            self.logActive = False
            setTemp = args[0]
            heaterSetting = args[1]
            waitTime = args[2]
            delays = args[3]
            self.delays = delays
            self.commandQueue.append(self._lambMill(self.hippo.setScanSettings, delays))
            self.commandQueue.append(self._lambMill(self._changeTemperature, setTemp, heaterSetting))
            self.commandQueue.append(self.beginScan)
            self.commandQueue.append(self._lambMill(self._heaterSafetyCheckpoint, waitTime, True))
            self.commandQueue.append(self.stopScan)
        elif scanType == 'POPV1':
            print('POP?')
            gateKerb = args[1].copy()
            THzKerb = args[0].copy()
            gate_key = gateKerb['stage_key']
            THz_key = THzKerb['stage_key']
            self.movingKeys = [THz_key, gate_key]
            rotKerb = args[2].copy()
            stage_key = rotKerb['stage_key']
            start_position = rotKerb['start']
            self.commandQueue.append(self._lambMill(self._moveStageAbsolute, stage_key = stage_key, position = start_position))
            self.commandQueue.append(self._lambMill(self._safetyCheckpoint, stage_key, bonusMod = 2.0, sleepTime = 0.2))
            self.commandQueue.append(self._lambMill(self._update_stage_position, stage_key))
            if rotKerb['subdir']:
                    subdir = '\\{0:.1f}'.format(start_position)
            gateKerb = args[1].copy()
            gate_key = gateKerb['stage_key']
            start_position = gateKerb['start']
            self.commandQueue.append(self._lambMill(self._moveStageAbsolute, stage_key = gate_key, position = start_position))
            self.commandQueue.append(self._lambMill(self._safetyCheckpoint, gate_key, bonusMod = 2.0, sleepTime = 0.2))
            self.commandQueue.append(self._lambMill(self._update_stage_position, gate_key))
            self._setStepsize(gate_key, gateKerb['stepsize'])
            THzKerb = args[0].copy()
            THz_key = THzKerb['stage_key']
            self.xLeadKey = THz_key
            if self.firstTime:
                self.THzPeak = THzKerb['start']
            start_position = self.THzPeak
            self.startPos = self.THzPeak
            self.commandQueue.append(self._lambMill(self._moveStageAbsolute, stage_key = THz_key, position = start_position))
            self.commandQueue.append(self._lambMill(self._safetyCheckpoint, THz_key, bonusMod = 2.0, sleepTime = 0.2))
            self.commandQueue.append(self._lambMill(self._update_stage_position, THz_key))
            self._setStepsize(THz_key, THzKerb['stepsize'])
            self.commandQueue.append(self._lambMill(self._update_scan_numbers, r = RDS[0], d = RDS[1], s = RDS[2]))
            self.commandQueue.append(self._lambMill(self.hippo.startFile, subdir = subdir, r = RDS[0], d = RDS[1], s = RDS[2]))
            self.commandQueue.append(self._lambMill(self._addWaitTime, 7.0))
            self.commandQueue.append(self.beginScan)
            self.commandQueue.append(self.appendData)
            self.commandQueue.append(self.updatePlot)
            for j in range(1,numSteps):
                self.commandQueue.append(self._lambMill(self._moveStep, stage_key = gate_key))
                self.commandQueue.append(self._lambMill(self._moveStep, stage_key = THz_key))
                self.commandQueue.append(self._lambMill(self._safetyCheckpoint, *[THz_key, gate_key]))
                self.commandQueue.append(self.appendData)
                self.commandQueue.append(self.updatePlot)
            self.commandQueue.append(self.stopScan)
        elif scanType == 'POP':
            print('POP?')
            gateKerb = args[1].copy()
            THzKerb = args[0].copy()
            gate_key = gateKerb['stage_key']
            THz_key = THzKerb['stage_key']
            self.movingKeys = [THz_key, gate_key]
            gateKerb = args[1].copy()
            gate_key = gateKerb['stage_key']
            start_position = gateKerb['start']
            self.commandQueue.append(self._lambMill(self._moveStageAbsolute, stage_key = gate_key, position = start_position))
            self.commandQueue.append(self._lambMill(self._safetyCheckpoint, gate_key, bonusMod = 2.0, sleepTime = 0.2))
            self.commandQueue.append(self._lambMill(self._update_stage_position, gate_key))
            self._setStepsize(gate_key, gateKerb['stepsize'])
            THzKerb = args[0].copy()
            THz_key = THzKerb['stage_key']
            self.xLeadKey = THz_key
            if self.firstTime:
                self.THzPeak = THzKerb['start']
            start_position = self.THzPeak
            self.startPos = self.THzPeak
            self.commandQueue.append(self._lambMill(self._moveStageAbsolute, stage_key = THz_key, position = start_position))
            self.commandQueue.append(self._lambMill(self._safetyCheckpoint, THz_key, bonusMod = 2.0, sleepTime = 0.2))
            self.commandQueue.append(self._lambMill(self._update_stage_position, THz_key))
            self._setStepsize(THz_key, THzKerb['stepsize'])
            self.commandQueue.append(self._lambMill(self._update_scan_numbers, r = RDS[0], d = RDS[1], s = RDS[2]))
            self.commandQueue.append(self._lambMill(self.hippo.startFile, subdir = '', r = RDS[0], d = RDS[1], s = RDS[2]))
            self.commandQueue.append(self._lambMill(self._addWaitTime, 7.0))
            self.commandQueue.append(self.beginScan)
            self.commandQueue.append(self.appendData)
            self.commandQueue.append(self.updatePlot)
            for j in range(1,numSteps):
                self.commandQueue.append(self._lambMill(self._moveStep, stage_key = gate_key))
                self.commandQueue.append(self._lambMill(self._moveStep, stage_key = THz_key))
                self.commandQueue.append(self._lambMill(self._safetyCheckpoint, *[THz_key, gate_key]))
                self.commandQueue.append(self.appendData)
                self.commandQueue.append(self.updatePlot)
            self.commandQueue.append(self.stopScan)
        elif scanType == 'peakFinder':
            print('peakFinder?')
            gateKerb = args[1].copy()
            THzKerb = args[0].copy()
            gate_key = gateKerb['stage_key']
            THz_key = THzKerb['stage_key']
            self.movingKeys = [THz_key, gate_key]
            self.logActive = False
            rotKerb = args[2].copy()
            stage_key = rotKerb['stage_key']
            start_position = rotKerb['start']
            self.commandQueue.append(self._lambMill(self._moveStageAbsolute, stage_key = stage_key, position = start_position))
            self.commandQueue.append(self._lambMill(self._safetyCheckpoint, stage_key, sleepTime = 0.2))
            self.commandQueue.append(self._lambMill(self._update_stage_position, stage_key))
            gateKerb = args[1].copy()
            gate_key = gateKerb['stage_key']
            start_position = gateKerb['start']
            self.commandQueue.append(self._lambMill(self._moveStageAbsolute, stage_key = gate_key, position = start_position))
            self.commandQueue.append(self._lambMill(self._safetyCheckpoint, gate_key, sleepTime = 0.2))
            self.commandQueue.append(self._lambMill(self._update_stage_position, gate_key))
            self._setStepsize(gate_key, gateKerb['stepsize'])
            THzKerb = args[0].copy()
            THz_key = THzKerb['stage_key']
            if self.firstTime:
                self.xLeadKey = THz_key
                self.THzPeak = THzKerb['start']
                start_position = self.THzPeak - 0.060
                self.startPos = self.THzPeak - 0.060
                self.firstTime = False
            else:
                start_position = self.THzPeak - 0.060
                self.startPos = self.THzPeak - 0.060
            self.commandQueue.append(self._lambMill(self._moveStageAbsolute, stage_key = THz_key, position = start_position))
            self.commandQueue.append(self._lambMill(self._safetyCheckpoint, THz_key, sleepTime = 0.2))
            self.commandQueue.append(self._lambMill(self._update_stage_position, THz_key))
            self._setStepsize(THz_key, 3.0)
            self.commandQueue.append(self._lambMill(self._update_scan_numbers, r = RDS[0], d = RDS[1], s = RDS[2]))
            self.commandQueue.append(self._lambMill(self._addWaitTime, 3.0))
            self.commandQueue.append(self.beginScan)
            self.commandQueue.append(self.appendData)
            self.commandQueue.append(self.updatePlot)
            for j in range(1,40):
                self.commandQueue.append(self._lambMill(self._moveStep, stage_key = THz_key))
                self.commandQueue.append(self._lambMill(self._safetyCheckpoint, *[THz_key]))
                self.commandQueue.append(self.appendData)
                self.commandQueue.append(self.updatePlot)
            self.commandQueue.append(self.determineTHzPeak)
            self.commandQueue.append(self.stopScan)
            self.xlimit_change(self.plot, 0, 0)
            self.xlimit_change(self.plot, 1, 40*3.0/.15/1000)
        elif scanType == 'sample-reference':
            print('initialize ['+','.join([str(x) for x in RDS])+']')
            self.commandQueue = []
            self.movingKeys = []
            subdir = ''
            self.stageBoss.clearAllChildren()
            for arg in args:
                print(arg)
                stage_key = arg['stage_key']
                start = arg['start']
                self.commandQueue.append(self._lambMill(self._moveStageAbsolute, stage_key = stage_key, position = start))
                self.commandQueue.append(self._lambMill(self._safetyCheckpoint, stage_key))
                self.commandQueue.append(self._lambMill(self._update_stage_position, stage_key))
                if arg['moving']:
                    self.movingKeys.append(stage_key)
                    self.xLeadKey = stage_key
                    self._setStepsize(stage_key, arg['stepsize']) # instead of this we just have to set step size
                    self.startPos = start
                if arg['subdir']:
                    if arg['subdirname'] != None:
                        subdir = '\\{0}'.format(arg['subdirname'])
                    else:
                        subdir = '\\{0:.1f}'.format(start)
            self.commandQueue.append(self._lambMill(self._update_scan_numbers, r = RDS[0], d = RDS[1], s = RDS[2]))
            self.commandQueue.append(self._lambMill(self.hippo.startFile, subdir = subdir, r = RDS[0], d = RDS[1], s = RDS[2]))
            self.commandQueue.append(self._lambMill(self._addWaitTime, 15.0))
            self.commandQueue.append(self.beginScan)
            self.commandQueue.append(self.appendData)
            self.commandQueue.append(self.updatePlot)
            for j in range(1,numSteps):
                for i in range(len(self.movingKeys)):
                    self.commandQueue.append(self._lambMill(self._moveStep, stage_key = self.movingKeys[i]))
                self.commandQueue.append(self._lambMill(self._safetyCheckpoint, *self.movingKeys))
                self.commandQueue.append(self.appendData)
                self.commandQueue.append(self.updatePlot)
            self.commandQueue.append(self.stopScan)
        else:
            print('initialize ['+','.join([str(x) for x in RDS])+']')
            self.commandQueue = []
            self.movingKeys = []
            subdir = ''
            self.stageBoss.clearAllChildren()
            for arg in args:
                print(arg)
                stage_key = arg['stage_key']
                start = arg['start']
                self.commandQueue.append(self._lambMill(self._moveStageAbsolute, stage_key = stage_key, position = start))
                self.commandQueue.append(self._lambMill(self._safetyCheckpoint, stage_key))
                self.commandQueue.append(self._lambMill(self._update_stage_position, stage_key))
                if arg['moving']:
                    self.xLeadKey = stage_key
                    self.movingKeys.append(stage_key)
                    self._setStepsize(stage_key, arg['stepsize']) # instead of this we just have to set step size
                    self.startPos = start
                if arg['subdir']:
                    if arg['subdirname'] != None:
                        subdir = '\\{0}'.format(arg['subdirname'])
                    else:
                        subdir = '\\{0:.1f}'.format(start)
            self.commandQueue.append(self._lambMill(self._update_scan_numbers, r = RDS[0], d = RDS[1], s = RDS[2]))
            self.commandQueue.append(self._lambMill(self.hippo.startFile, subdir = subdir, r = RDS[0], d = RDS[1], s = RDS[2]))
            self.commandQueue.append(self._lambMill(self._addWaitTime, 4.0))
            self.commandQueue.append(self.beginScan)
            self.commandQueue.append(self.appendData)
            self.commandQueue.append(self.updatePlot)
            for j in range(1,numSteps):
                for i in range(len(self.movingKeys)):
                    self.commandQueue.append(self._lambMill(self._moveStep, stage_key = self.movingKeys[i]))
                self.commandQueue.append(self._lambMill(self._safetyCheckpoint, *self.movingKeys))
                self.commandQueue.append(self.appendData)
                self.commandQueue.append(self.updatePlot)
            self.commandQueue.append(self.stopScan)

    def initializeScanV1(self, *args, numSteps = 3, RDS = None):
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
            self.commandQueue.append(self._lambMill(self._moveStageAbsolute, stage_key = stage_key, position = start))
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

    def determineTHzPeak(self):
        arrY = np.array(self.y[1]['live'])
        print(self.THzPeak)
        self.THzPeak = self.THzPeak + (np.argmax(arrY) - 20)*3.0/1000
        print(self.THzPeak)

    def _moveStageAbsolute(self, stage_key, position):
        self.stageBoss.moveStageAbsolute(stage_key, position)
        self.stageJustMoved = True

    def _addWaitTime(self, sleepTime):
        time.sleep(sleepTime)

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

    def _recallStageKeys(self):
        try:
            self.sWidgets['THzkey'].setCurrentText(self.settings.value('THzkey'))
            self.sWidgets['gatekey'].setCurrentText(self.settings.value('gatekey'))
            self.sWidgets['rotkey'].setCurrentText(self.settings.value('rotkey'))
            self.sWidgets['xkey'].setCurrentText(self.settings.value('xkey'))
            self.sWidgets['ykey'].setCurrentText(self.settings.value('ykey'))
        except Exception as e:
            print('_recallStageKeys problem:')
            print(e)

    def _recallSettings(self):
        try:
            # numbers
            self.sWidgets['THzsetposition'].setValue(float(self.settings.value('THzsetposition')))
            self.sWidgets['gatesetposition'].setValue(float(self.settings.value('gatesetposition')))
            self.sWidgets['THzsetpositionref'].setValue(float(self.settings.value('THzsetpositionref')))
            self.sWidgets['gatesetpositionref'].setValue(float(self.settings.value('gatesetpositionref')))
            self.sWidgets['prescan'].setValue(float(self.settings.value('prescan')))
            self.sWidgets['startnum'].setValue(self.settings.value('startnum'))
            self.sWidgets['stepsize'].setValue(float(self.settings.value('stepsize')))
            self.sWidgets['numsteps'].setValue(self.settings.value('numsteps'))
            self.sWidgets['numrounds'].setValue(self.settings.value('numrounds'))
            # text
            self.sWidgets['delays'].setPlainText(self.settings.value('delays'))
            self.sWidgets['comments'].setPlainText(self.settings.value('comments'))
            self.sWidgets['extension'].setText(self.settings.value('extension'))
            self.sWidgets['path'].setText(self.settings.value('path'))
            self.sWidgets['filename'].setText(self.settings.value('filename'))
            self.sWidgets['scanmode'].setCurrentIndex(int(self.settings.value('scanmode')))

            print('xsampposition saved as ', self.settings.value('xsampposition'))
            self.sWidgets['xsampposition'].setValue(float(self.settings.value('xsampposition')))
            self.sWidgets['ysampposition'].setValue(float(self.settings.value('ysampposition')))
            self.sWidgets['xrefposition'].setValue(float(self.settings.value('xrefposition')))
            self.sWidgets['yrefposition'].setValue(float(self.settings.value('yrefposition')))
        except Exception as e:
            print(e)

    def _storeSettings(self):
        try:
            # numbers
            self.settings.setValue('THzsetposition', self.sWidgets['THzsetposition'].value())
            self.settings.setValue('gatesetposition', self.sWidgets['gatesetposition'].value())
            self.settings.setValue('THzsetpositionref', self.sWidgets['THzsetpositionref'].value())
            self.settings.setValue('gatesetpositionref', self.sWidgets['gatesetpositionref'].value())
            self.settings.setValue('prescan', self.sWidgets['prescan'].value())
            self.settings.setValue('startnum', self.sWidgets['startnum'].value())
            self.settings.setValue('stepsize', self.sWidgets['stepsize'].value())
            self.settings.setValue('numsteps', self.sWidgets['numsteps'].value())
            self.settings.setValue('numrounds', self.sWidgets['numrounds'].value())
            # text
            self.settings.setValue('delays', self.sWidgets['delays'].toPlainText())
            self.settings.setValue('comments', self.sWidgets['comments'].toPlainText())
            self.settings.setValue('extension', self.sWidgets['extension'].text())
            self.settings.setValue('path', self.sWidgets['path'].text())
            self.settings.setValue('filename', self.sWidgets['filename'].text())
            self.settings.setValue('scanmode', self.sWidgets['scanmode'].currentIndex())

            self.settings.setValue('THzkey', self.sWidgets['THzkey'].currentText())
            self.settings.setValue('gatekey', self.sWidgets['gatekey'].currentText())
            self.settings.setValue('rotkey', self.sWidgets['rotkey'].currentText())
            self.settings.setValue('xkey', self.sWidgets['xkey'].currentText())
            self.settings.setValue('ykey', self.sWidgets['ykey'].currentText())
            
            self.settings.setValue('xsampposition', self.sWidgets['xsampposition'].value())
            self.settings.setValue('ysampposition', self.sWidgets['ysampposition'].value())
            self.settings.setValue('xrefposition', self.sWidgets['xrefposition'].value())
            self.settings.setValue('yrefposition', self.sWidgets['yrefposition'].value())
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

    def setScanSettings(self, delays):
        self.delays = delays

    def startFile(self, subdir = '', r = None, d = None, s = None):
        self.wto = self.openFile(comment = False, subdir = subdir, r = r, d = d, s = s)
        self.x = []
        self.y0X = []
        self.y0Y = []
        self.y1X = []
        self.y1Y = []

    def feedData(self, x, y0X, y0Y, y1X, y1Y):
        self.x.append(x)
        self.y0X.append(y0X)
        self.y0Y.append(y0Y)
        self.y1X.append(y1X)
        self.y1Y.append(y1Y)
        self.wto.write(format(x, '.4f') + ' ' + format(y0X, '.4f') + ' ' + format(y0Y, '.4f') + ' ' + format(y1X, '.4f') + ' ' + format(y1Y, '.4f') + '\n')

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
        try:
            self.wto.close()
        except:
            print('no file to close')

class cuteWorker(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    def __init__(self, parent, plot):
        super(cuteWorker, self).__init__()
        self.parent = parent
        self.plot = plot
        
    def run(self, x, y):
        self.plot.updateCanvas(x, y)
        self.plot._drawPlot()

class Worker(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    def __init__(self, parent, function):
        super(Worker, self).__init__()
        self.parent = parent
        self.function = function
        
    def run(self):
        self.function()
        self.finished.emit()