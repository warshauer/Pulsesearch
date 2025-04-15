import numpy as np
import os
import testingClasses as tC
import sys
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.qt_compat import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvas
import matplotlib as mpl
import matplotlib.figure as mpl_fig
import matplotlib.animation as anim
from matplotlib.figure import Figure
import matplotlib.ticker as ticker
import numpy as np
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot
import appClasses as dd
#import qt5_controller as qc
#from flowControllerClasses import Flowmeter
from instrumentControl import esp301_GPIB, sr830, CONEX
import time
from scipy.fft import fft, fftfreq
#from scanProgV3p4 import DLscanWindow
from scanProgV4p0 import DLscanWindow

class pulsesearchWindow(QtWidgets.QMainWindow):
    def __init__(self, whoami = 'pulseSearch', version = 'v4.0', ESP_port = 1, lockin1_port = 8, lockin2_port = 7):
        QtWidgets.QMainWindow.__init__(self)
        self.ui = uic.loadUi('pulsesearchv4.ui',self) # swap this to pyui5 instead, then we may export it out to a class to make generic, contain and sort widgets and variables
        self.resize(1700, 1000)
        self.me = whoami
        self.stageBoss = stageBoss()

        self.instrumentsConnected = False

        self.threadpool = QtCore.QThreadPool()	
        self.threadpool.setMaxThreadCount(1)

        self.settings = QtCore.QSettings(self.me, version)

        self._timeConstantList = [.00001, .00003, .0001, .0003, .001, .003, .01, .03, .1, .3, 1, 3, 10, 30, 100, 300, 1000, 3000, 10000, 30000]
        self._sensitivityList = [2, 5, 10, 20, 50, 100, 200, 500, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1]

        #self.plot = dd.fastCanvas(self, line_dict = line_dict, xlabel = 'time (ps)', plot_dict = plot_dict, autolim = False, xlimits = [-1, 1], last_point = True)
        self.plot = PulsesearchCanvasXY(self, xlabel = 'time (ps)', ylabel1 = 'lock-in 1', ylabel2 = 'lock-in 2', xlimits = [-1, 1])
        self.ui.GL_plot.addWidget(self.plot,0,0,1,1)

        self._move = False
        self._cmi = 0
        self._cmpn = 1
        #self._toggles = {'1_opX':True, '1_opY':True, '2_opX':False, '2_opY':False}
        self.avgCounter = 0
        self.counter0 = 0
        self.counter1 = 0
        self.TCsafety = True
        self._onPlot_ = {'1X':True, '1Y':True, '2X':False, '2Y':False}

        self.motionAllowed = True
        self.addNext = False
        self.stageJustMoved = False
        self.timeStageEnd = time.monotonic()

        self.timeConstants = [0,0]

        self.quickFFT = quickFFTWindow(self)
        self.scanWindow = DLscanWindow(self)
        self.savePlotWindow = savePlotWindow(self)

        self.PB_quickFFT.clicked.connect(lambda : self._openWindow(self.quickFFT))
        self.PB_savePlot.clicked.connect(lambda : self._openWindow(self.savePlotWindow))
        self.PB_scans.clicked.connect(self._openScans)
        self.PB_connect.clicked.connect(self._connectInstruments)
        


        if True:
            self.yVals = {1:[0,0,0,0,0,0,0,0,0,0], 2:[0,0,0,0,0,0,0,0,0,0]}
            self.mWidgets = {}
            self.mWidgets[1] = {'E':self.LE_E1, 'freq':self.LE_freq1, 'onplotX':self.CB_onplot1X, 'onplotY':self.CB_onplot1Y, 'sensitivity':self.CB_sens1, 'timeconstant':self.CB_tc1, 'inputconfig':self.CB_ic1, 'ylim0':self.SB_ylim01, 'ylim1':self.SB_ylim11, 'autophase':self.PB_autophase1, 'displayE':self.CB_dispE1, 'ras':self.SP_ras1}
            self.mWidgets[2] = {'E':self.LE_E2, 'freq':self.LE_freq2, 'onplotX':self.CB_onplot2X, 'onplotY':self.CB_onplot2Y, 'sensitivity':self.CB_sens2, 'timeconstant':self.CB_tc2, 'inputconfig':self.CB_ic2, 'ylim0':self.SB_ylim02, 'ylim1':self.SB_ylim12, 'autophase':self.PB_autophase2, 'displayE':self.CB_dispE2, 'ras':self.SP_ras2}


            self.mWidgets[1]['onplotX'].stateChanged.connect(lambda:self._onPlotPlot('1X', self.mWidgets[1]['onplotX'].isChecked()))
            self.mWidgets[1]['onplotY'].stateChanged.connect(lambda:self._onPlotPlot('1Y', self.mWidgets[1]['onplotY'].isChecked()))
            self.mWidgets[2]['onplotX'].stateChanged.connect(lambda:self._onPlotPlot('2X', self.mWidgets[2]['onplotX'].isChecked()))
            self.mWidgets[2]['onplotY'].stateChanged.connect(lambda:self._onPlotPlot('2Y', self.mWidgets[2]['onplotY'].isChecked()))

            self.mWidgets[1]['sensitivity'].currentIndexChanged.connect(lambda : self._sensitivityChange(1, self.mWidgets[1]['sensitivity'].currentIndex()))
            self.mWidgets[1]['timeconstant'].currentIndexChanged.connect(lambda : self._timeconstantChange(1, self.mWidgets[1]['timeconstant'].currentIndex()))
            self.mWidgets[1]['inputconfig'].currentIndexChanged.connect(lambda : self._inputconfigChange(1, self.mWidgets[1]['inputconfig'].currentIndex()))

            self.mWidgets[2]['sensitivity'].currentIndexChanged.connect(lambda : self._sensitivityChange(2, self.mWidgets[2]['sensitivity'].currentIndex()))
            self.mWidgets[2]['timeconstant'].currentIndexChanged.connect(lambda : self._timeconstantChange(2, self.mWidgets[2]['timeconstant'].currentIndex()))
            self.mWidgets[2]['inputconfig'].currentIndexChanged.connect(lambda : self._inputconfigChange(2, self.mWidgets[2]['inputconfig'].currentIndex()))

        if True:
            self.sWidgets = {}
            self.sWidgets['ESP1'] = {'sn':self.PB_sn0, 'sp':self.PB_sp0, 'sethome':self.PB_sethome0, 'returnhome':self.PB_returnhome0, 
                                'mn':self.PB_mn0, 'mp':self.PB_mp0, 'link':self.CB_linkedstage0, 'ss':self.SB_ss0, 'si':self.SB_si0, 'multiplier':self.SB_multiplier0, 
                                'pmm':self.LE_pmm0, 'home':self.LE_home0, 'stop':self.PB_stop0, 'updatefrequency':self.SB_updateFreq0, 'unitbox':self.CB_units0, 
                                'xlead':self.RB_xAxis0, 'unitlabel':self.L_units0, 'setabsolute':self.PB_setabsolute0, 'absolute':self.LE_absolute0, 'moveabsolute':self.PB_moveabsolute0}
            self.sWidgets['ESP2'] = {'sn':self.PB_sn1, 'sp':self.PB_sp1, 'sethome':self.PB_sethome1, 'returnhome':self.PB_returnhome1, 
                                'mn':self.PB_mn1, 'mp':self.PB_mp1, 'link':self.CB_linkedstage1, 'ss':self.SB_ss1, 'si':self.SB_si1, 'multiplier':self.SB_multiplier1, 
                                'pmm':self.LE_pmm1, 'home':self.LE_home1, 'stop':self.PB_stop1, 'updatefrequency':self.SB_updateFreq1, 'unitbox':self.CB_units1, 
                                'xlead':self.RB_xAxis1, 'unitlabel':self.L_units1, 'setabsolute':self.PB_setabsolute1, 'absolute':self.LE_absolute1, 'moveabsolute':self.PB_moveabsolute1}
            self.sWidgets['ESP3'] = {'sn':self.PB_sn2, 'sp':self.PB_sp2, 'sethome':self.PB_sethome2, 'returnhome':self.PB_returnhome2, 
                                'mn':self.PB_mn2, 'mp':self.PB_mp2, 'link':self.CB_linkedstage2, 'ss':self.SB_ss2, 'si':self.SB_si2, 'multiplier':self.SB_multiplier2, 
                                'pmm':self.LE_pmm2, 'home':self.LE_home2, 'stop':self.PB_stop2, 'updatefrequency':self.SB_updateFreq2, 'unitbox':self.CB_units2, 
                                'xlead':self.RB_xAxis2, 'unitlabel':self.L_units2, 'setabsolute':self.PB_setabsolute2, 'absolute':self.LE_absolute2, 'moveabsolute':self.PB_moveabsolute2}
            if False:
                self.sWidgets['CONEX'] = {'sn':self.PB_sn3, 'sp':self.PB_sp3, 'sethome':self.PB_sethome3, 'returnhome':self.PB_returnhome3, 'mn':self.PB_mn3, 'mp':self.PB_mp3, 'link':self.CB_linkedstage3, 'ss':self.SB_ss3, 'si':self.SB_si3, 'multiplier':self.SB_multiplier3, 'pmm':self.LE_pmm3, 'home':self.LE_home3, 'stop':self.PB_stop3, 'updatefrequency':self.SB_updateFreq3, 'unitbox':self.CB_units3, 'xlead':self.RB_xAxis3, 'unitlabel':self.L_units3, 'setabsolute':self.PB_setabsolute3, 'absolute':self.LE_absolute3, 'moveabsolute':self.PB_moveabsolute3}

        if True:
            self.unitMod = 0.15
            self.CB_xUnits.currentIndexChanged.connect(self._xUnitChange)
            self.invert = [1,1]
            self.CB_invert1.stateChanged.connect(lambda : self._invertChange(0, self.CB_invert1.isChecked()))
            self.CB_invert2.stateChanged.connect(lambda : self._invertChange(1, self.CB_invert2.isChecked()))

            self.SB_TCcof.valueChanged.connect( lambda : self.adjustTCwait( 0, self.SB_TCcof.value() ) )
            self.TCcof = 1.6
            self.SB_TCadd.valueChanged.connect( lambda : self.adjustTCwait( 1, self.SB_TCadd.value() ) )
            self.TCadd = 0.00
            self.SB_xlim0.valueChanged.connect( lambda : self.xlimit_change( 0, self.SB_xlim0.value() ) )
            self.SB_xlim1.valueChanged.connect( lambda : self.xlimit_change( 1, self.SB_xlim1.value() ) )
            self.SB_ylim01.valueChanged.connect( lambda : self.ylimit_change( 1, 0, self.SB_ylim01.value()) )
            self.SB_ylim11.valueChanged.connect( lambda : self.ylimit_change( 1, 1, self.SB_ylim11.value()) )
            self.SB_ylim02.valueChanged.connect( lambda : self.ylimit_change( 2, 0, self.SB_ylim02.value()) )
            self.SB_ylim12.valueChanged.connect( lambda : self.ylimit_change( 2, 1, self.SB_ylim12.value()) )

        self.commandQueue = []
        self.PB_clearQueue.clicked.connect(self._clearQueue)
        self.PB_clearChildren.clicked.connect(self._clear_all_children)

        self._sample_interval = 50
        self._timer = QtCore.QTimer()
        self._timer.setInterval(self._sample_interval) #msec
        self._timer.timeout.connect(self.runtime_functionV2)
        self.rtTime0 = time.monotonic(); self.rtList0 = list(np.zeros(10))
        self.rtTime1 = time.monotonic(); self.rtList1 = list(np.zeros(10))
        self.rtTime2 = time.monotonic(); self.rtList2 = list(np.zeros(10))
        self._timer.start()

        self.workerFinished0 = True
        self.workerFinished1 = True

        try:
            self._recallSettings()
        except Exception as e:
            print(e)
        

        quit = QtWidgets.QAction("Quit", self)
        quit.triggered.connect(self.close)




    def _stageControllerInitialization(self, stagePort):
        # swap out the following line for whichever class connects to the stage controller:
        self.esp301 = esp301_GPIB(stagePort)
        #self.conex = CONEX(port = 3)
        # update how many stages are active:
        #self.activeStages = [1, 2, 3]#, 4]
        self.xLeadingStage = 'ESP1'
        stages = {'ESP1':self.esp301, 'ESP2':self.esp301, 'ESP3':self.esp301}#, 'CONEX':self.conex}
        self.activeStages = list(stages.keys())
        self.stageBoss.assignMotionController(motionController(stages, unitMultiplier = {'ESP1':0.001, 'ESP2':0.001, 'ESP3':0.001}))#, 'CONEX':1}))
        indy500 = 1
        for key in stages:
            if key in list(self.stageValueInit.keys()):
                self.stageBoss.addStage(key, self.stageValueInit[key].copy())
                self.stageBoss.clearChildren(key)
            else:
                print('no stage recall')
                self.stageBoss.addStage(key, {'home':0.00, 'position':0.0, 'link':None, 'children':[], 'stepsize':5, 'index':indy500, 'multiplier':1, 'updatefrequency':1, 
                                              'updatetime':time.monotonic()})
                indy500 += 1
        self._stageInterfaceInitialization(list(self.stageBoss.keys()))

    def _stageInterfaceInitialization(self, stage_keys):
        for stage_key in stage_keys:
            keyList = stage_keys.copy()
            keyList.remove(stage_key)
            self.sWidgets[stage_key]['sn'].clicked.connect(self._lambMill(self._move_stage_step, stage_key, -1))
            self.sWidgets[stage_key]['sp'].clicked.connect(self._lambMill(self._move_stage_step, stage_key, 1))
            self.sWidgets[stage_key]['mn'].clicked.connect(self._lambMill(self._move_stage_continuous, stage_key, -1))
            self.sWidgets[stage_key]['mp'].clicked.connect(self._lambMill(self._move_stage_continuous, stage_key, 1))
            self.sWidgets[stage_key]['stop'].clicked.connect(self._stop_stage_continuous)
            self.sWidgets[stage_key]['sethome'].clicked.connect(self._lambMill(self._set_home, stage_key))
            self.sWidgets[stage_key]['returnhome'].clicked.connect(self._lambMill(self._return_to_home, stage_key))
            self.sWidgets[stage_key]['link'].addItems(keyList)
            self.sWidgets[stage_key]['link'].currentIndexChanged.connect(self._lambMill(self._set_stage_link, stage_key))
            self.sWidgets[stage_key]['multiplier'].valueChanged.connect(self._lambMill(self._set_stage_multiplier, stage_key))
            self.sWidgets[stage_key]['ss'].valueChanged.connect(self._lambMill(self._set_stage_stepsize, stage_key))
            self.sWidgets[stage_key]['si'].valueChanged.connect(self._lambMill(self._set_stage_index, stage_key))
            self.sWidgets[stage_key]['updatefrequency'].valueChanged.connect(self._lambMill(self._set_stage_update_frequency, stage_key))
            self.sWidgets[stage_key]['xlead'].toggled.connect(self._lambMill(self._set_x_lead, stage_key))
            self.sWidgets[stage_key]['setabsolute'].clicked.connect(self._lambMill(self._set_absolute, stage_key))
            self.sWidgets[stage_key]['moveabsolute'].clicked.connect(self._lambMill(self._move_absolute, stage_key))
            #self.sWidgets[stage_key]['si'].setEnabled(False)

    def _connectInstruments(self):
        try:
            self.stageController.close_connection()
            for key in self.lockins:
                key1 = key
                for key in self.mWidgets[key1]:
                    self.mWidgets[key1][key].setEnabled(True)
                self.lockins[key1].close_connection()
            time.sleep(1)
        except:
            print('new connections')
        stagePort = self.SP_ESPaddress.value()
        self.SP_ESPaddress.setEnabled(False)
        self._stageControllerInitialization(stagePort)
        self._updateAllStagePositions()
        self.lockins = {}
        if self.CB_connect1.isChecked():
            lockin1_port = self.SP_address1.value()
            self.SP_address1.setEnabled(False)
            self.CB_connect1.setEnabled(False)
            l1 = sr830(lockin1_port)
            l1.set_input_config(l1.get_input_config())
            l1.set_sensitivity(l1.get_sensitivity())
            l1.set_time_constant(l1.get_time_constant())
            self.lockins[1] = l1
            for key in self.mWidgets[1]:
                self.mWidgets[1][key].setEnabled(True)
        else:
            for key in self.mWidgets[1]:
                self.mWidgets[1][key].setEnabled(False)
        if self.CB_connect2.isChecked():
            lockin2_port = self.SP_address2.value()
            self.SP_address2.setEnabled(False)
            self.CB_connect2.setEnabled(False)
            l2 = sr830(lockin2_port)
            l2.set_input_config(l2.get_input_config())
            l2.set_sensitivity(l2.get_sensitivity())
            l2.set_time_constant(l2.get_time_constant())
            self.lockins[2] = l2
            for key in self.mWidgets[2]:
                self.mWidgets[2][key].setEnabled(True)
        else:
            for key in self.mWidgets[2]:
                self.mWidgets[2][key].setEnabled(False)
        self.x = np.array([])
        self.y = {}
        self.y[1] = {'X':np.array([]), 'Y':np.array([])}
        self.y[2] = {'X':np.array([]), 'Y':np.array([])}
        for key in self.lockins:
            self.y[key]['X'] = np.append(self.y[key]['X'], [self._get_measurement(self.lockins[key], 'X')])
            self.y[key]['Y'] = np.append(self.y[key]['Y'], [self._get_measurement(self.lockins[key], 'Y')])
            self._sensitivityChange(key, self.lockins[key].get_sensitivity())
            self.timeConstants[key-1] = self._timeConstantList[self.lockins[key].get_time_constant()]
            self.mWidgets[key]['autophase'].clicked.connect(self.lockins[key].auto_phase)
            self.mWidgets[key]['sensitivity'].setCurrentIndex(self.lockins[key].get_sensitivity())
            self.mWidgets[key]['timeconstant'].setCurrentIndex(self.lockins[key].get_time_constant())
            self.mWidgets[key]['inputconfig'].setCurrentIndex(self.lockins[key].get_input_config())
        self.x = np.append(self.x, [0])
        self.instrumentsConnected = True

    def _clearQueue(self):
        self.commandQueue = []

    def _sensitivityChange(self, index, value):
        self.lockins[index].set_sensitivity(value)
        self.mWidgets[index]['ylim0'].setValue(-self._sensitivityList[value])
        self.mWidgets[index]['ylim1'].setValue(self._sensitivityList[value])
        self.ylimit_change( index, 0, -self._sensitivityList[value])
        self.ylimit_change( index, 1, self._sensitivityList[value])

    def _timeconstantChange(self, index, value):
        print(index, value)
        self.lockins[index].set_time_constant(value)
        self.timeConstants[index-1] = self._timeConstantList[value]

    def _inputconfigChange(self, index, value):
        self.lockins[index].set_input_config(value)

    def _xUnitChange(self):
        unit = str(self.CB_xUnits.currentText())
        if unit == 'ps':
            self.unitMod = 0.15
        elif unit == 'mm':
            self.unitMod = 1
        elif unit == 'um':
            self.unitMod = 1000

    def _set_stage_multiplier(self, stage_key):
        self.stageBoss.setMultiplier(stage_key, self.sWidgets[stage_key]['multiplier'].value())
    def _set_stage_stepsize(self, stage_key):
        self.stageBoss.setStepsize(stage_key, self.sWidgets[stage_key]['ss'].value())
    def _set_stage_index(self, stage_key):
        self.stageBoss.setIndex(stage_key, self.sWidgets[stage_key]['si'].value())
    def _set_stage_update_frequency(self, stage_key):
        self.stageBoss.setUpdateFrequency(stage_key, self.sWidgets[stage_key]['updatefrequency'].value())
    def _set_x_lead(self, stage_key):
        boo = self.sWidgets[stage_key]['xlead'].isChecked()
        if boo:
            self.xLeadingStage = stage_key

    def _set_stage_link(self, stage_key):
        link = str(self.sWidgets[stage_key]['link'].currentText())
        if link == 'None':
            self.stageBoss.unlinkStage(stage_key)
            self._link_enable(stage_key, True)
        else:
            self.stageBoss.linkStage(stage_key, link)
            self._link_enable(stage_key, False)
    def _link_enable(self, stage_key, boo):
        for widg in ['mn', 'sn', 'sp', 'mp', 'returnhome', 'stop', 'ss', 'si']:
            self.sWidgets[stage_key][widg].setEnabled(boo)
    def _clear_all_children(self, full = True):
        if full:
            self.stageBoss.clearAllChildren()
        else:
            self.stageBoss.clearAllChildren()
            for stage_key in self.stageBoss.keys():
                link = str(self.sWidgets[stage_key]['link'].currentText())
                if link != 'None':
                    self._set_stage_link(stage_key)

    def _set_absolute(self, stage_key):
        try:
            self.sWidgets[stage_key]['absolute'].setText(format(self.stageBoss.getStagePosition(stage_key), '.4f'))
        except Exception as e:
            print(e)
    def _move_absolute(self, stage_key):
        try:
            absolutePos = float(self.sWidgets[stage_key]['absolute'].text())
        except Exception as e:
            print('Issue with absolute position, ', e)
        self._move_stage_absolute(stage_key, absolutePos)

    def _moveStageAbsolute(self, stage_key, position):
        self.stageBoss.moveStageAbsolute(stage_key, position)
        self.stageJustMoved = True
    def _move_stage_absolute(self, stage_key, position):
        self._addFunctionToQueue(self._moveStageAbsolute, stage_key, position)
        if self.xLeadingStage == stage_key:
            self._addFunctionToQueue(self._safetyCheckpoint, stage_key)
            self._addFunctionToQueue(self.appendData)

    def _set_home(self, stage_key):
        try:
            self.sWidgets[stage_key]['home'].setText(format(self.stageBoss.getStagePosition(stage_key), '.4f'))
        except Exception as e:
            print(e)
    def _return_to_home(self, stage_key):
        stage_keys = self.stageBoss.getChildren(stage_key)
        stage_keys.insert(0, stage_key)
        for skey in stage_keys:
            try:
                hpos = float(self.sWidgets[skey]['home'].text())
                self.stageBoss.setHomePosition(skey, hpos)
            except Exception as e:
                print('Issue with home position, ', e)
        if self.xLeadingStage in stage_keys:
            self.x = np.array([0])
            self.y = {}
            self.y[1] = {'X':np.array([0]), 'Y':np.array([0])}
            self.y[2] = {'X':np.array([0]), 'Y':np.array([0])}
        self._move_stage_home(stage_key)
        self._clear_all_children(full = False)

    def _moveStageStep(self, stage_key, pn):
        self.stageBoss.moveStageStep(stage_key, pn)
        self.stageJustMoved = True
        self._speedCheck0(p0 = True)
    def _move_stage_step(self, stage_key, pn):
        self._addFunctionToQueue(self._moveStageStep, stage_key, pn)
        if self.xLeadingStage == stage_key or self.xLeadingStage in self.stageBoss.getChildren(stage_key):
            self._addFunctionToQueue(self._safetyCheckpoint, stage_key, *self.stageBoss.getChildren(stage_key))
            #self._addFunctionToQueue(self._updateStagePosition, stage_key, *self.stageBoss.getChildren(stage_key))
            self._addFunctionToQueue(self.appendData, stage_key, *self.stageBoss.getChildren(stage_key))

    def _moveStageContinuous(self, index, pn):
        self._move = True
        self._cmi = index
        self._cmpn = pn
    def _move_stage_continuous(self, index, pn):
        self._addFunctionToQueue(self._moveStageContinuous, index, pn)

    def _stopStageContinuous(self):
        self._move = False
    def _stop_stage_continuous(self):
        self._addFunctionToQueue(self._stopStageContinuous)

    def _moveStageHome(self, stage_key):
        self.stageBoss.moveStageHome(stage_key)
        self.stageJustMoved = True
    def _move_stage_home(self, stage_key):
        self._addFunctionToQueue(self._moveStageHome, stage_key)
        if self.xLeadingStage == stage_key or self.xLeadingStage in self.stageBoss.getChildren(stage_key):
            self._addFunctionToQueue(self._safetyCheckpoint, stage_key, *self.stageBoss.getChildren(stage_key))
            self._addFunctionToQueue(self.appendData)

    def appendData(self, *stage_keys):
        self._speedCheck0(p1 = True)
        for key in self.lockins:
            self.y[key]['X'][-1] = self._get_measurement(self.lockins[key], 'X')
            self.y[key]['X'] = np.append(self.y[key]['X'], [self._get_measurement(self.lockins[key], 'X')])
            self.y[key]['Y'][-1] = self._get_measurement(self.lockins[key], 'Y')
            self.y[key]['Y'] = np.append(self.y[key]['Y'], [self._get_measurement(self.lockins[key], 'Y')])
        self._update_measurement_values()
        self._updateStagePosition(*stage_keys)
        pos = self.stageBoss.getStagePosition(self.xLeadingStage) - self.stageBoss.getHomePosition(self.xLeadingStage)
        self.x[-1] = pos
        self.x = np.append(self.x, [pos])

    def _change_sample_interval(self, value):
        self._sample_interval = value
        self._timer.setInterval(self._sample_interval)

    def _get_measurement(self, lockin, output = 'X'):
        return lockin.get_specific_output(output)
        
    def refreshData(self):
        for key in self.lockins:
            if self.mWidgets[key]['displayE'].currentIndex() == 3:
                if self.TCsafety:
                    yX = self._get_measurement(self.lockins[key], 'X')
                    yY = self._get_measurement(self.lockins[key], 'Y')
                    self.yVals[key].append(yX)
                    self.yVals[key] = self.yVals[key][1:]
                    self.y[key]['X'][-1] = yX
                    self.y[key]['Y'][-1] = yY
                else:
                    pass
            else:
                yX = self._get_measurement(self.lockins[key], 'X')
                yY = self._get_measurement(self.lockins[key], 'Y')
                self.yVals[key].append(yX)
                self.yVals[key] = self.yVals[key][1:]
                self.y[key]['X'][-1] = yX
                self.y[key]['Y'][-1] = yY

    def plotUpdate(self):
        if self.workerFinished0:
            self.workerFinished0 = False
            if self._onPlot_['1X']:
                x1LIX = self.x * self.invert[0]
                y1LIX = self.y[1]['X']
            else:
                x1LIX = np.array([])
                y1LIX = np.array([])
            if self._onPlot_['1Y']:
                x1LIY = self.x * self.invert[0]
                y1LIY = self.y[1]['Y']
            else:
                x1LIY = np.array([])
                y1LIY = np.array([])
            if self._onPlot_['2X']:
                x2LIX = self.x * self.invert[1]
                y2LIX = self.y[2]['X']
            else:
                x2LIX = np.array([])
                y2LIX = np.array([])
            if self._onPlot_['2Y']:
                x2LIY = self.x * self.invert[1]
                y2LIY = self.y[2]['Y']
            else:
                x2LIY = np.array([])
                y2LIY = np.array([])
            if len(x1LIX) == len(y1LIX) and len(x2LIX) == len(y2LIX) and len(x1LIY) == len(y1LIY) and len(x2LIY) == len(y2LIY):
                self.plot.update_plot(x1LIX/self.unitMod, x1LIY/self.unitMod, x2LIX/self.unitMod, x2LIY/self.unitMod, y1LIX, y1LIY, y2LIX, y2LIY)
            self.workerFinished0 = True

    def getPlotValues(self):
        try:
            xx = self.x*self.invert[0]/self.unitMod
            plotVals = np.array([xx])
            units = [str(self.CB_xUnits.currentText())]
            if self._onPlot_['1X']:
                plotVals = np.concatenate((plotVals, np.array([self.y[1]['X']])))
                units.append('1X_'+self.mWidgets[1]['sensitivity'].currentText().split('/')[0].split(' ')[1])
            if self._onPlot_['1Y']:
                plotVals = np.concatenate((plotVals, np.array([self.y[1]['Y']])))
                units.append('1Y_'+self.mWidgets[2]['sensitivity'].currentText().split('/')[0].split(' ')[1])
            if self._onPlot_['2X']:
                plotVals = np.concatenate((plotVals, np.array([self.y[2]['X']])))
                units.append('2X_'+self.mWidgets[1]['sensitivity'].currentText().split('/')[0].split(' ')[1])
            if self._onPlot_['2Y']:
                plotVals = np.concatenate((plotVals, np.array([self.y[2]['Y']])))
                units.append('2Y_'+self.mWidgets[2]['sensitivity'].currentText().split('/')[0].split(' ')[1])
            return plotVals, units
        except Exception as e:
            print(e)
            return None, None

    # ---- MAIN RUNTIME ----
    def runtime_functionV2(self):
        if self.instrumentsConnected:
            self._updateQueueLen() #hi
            self.executeQueue()
            self.refreshData()
            self._update_measurement_values()
            self._updateAllStagePositions()
            self._speedCheck2(p0 = True)
            self._speedCheck1()
            if self._move == True and len(self.commandQueue) < 1:
                self._addFunctionToQueue(self._move_stage_step, self._cmi, self._cmpn)
            self._threadWork(self.plotUpdate)
            if self.counter1 > 250:
                self.counter1 = 0
                self._update_ref_freq()
            else:
                self.counter1 += 1 
            self._speedCheck2(p1 = True)

    def executeQueue(self):
        if len(self.commandQueue) < 1:
            pass
        else:
            funky = self.commandQueue.pop(0)
            funky()

    def _updateQueueLen(self):
        self.LE_queue.setText(str(len(self.commandQueue)))

    def _addFunctionToQueue(self, func, *args, **kwargs):
        self.commandQueue.append(self._lambMill(func, *args, **kwargs))
        print('add to queue: ', func)

    def _safetyCheckpointOriginal(self, *stage_keys):
        if True in [self.stageBoss.moving(stage_key) for stage_key in stage_keys]:
            self.commandQueue.insert(0, self._lambMill(self._safetyCheckpoint, *stage_keys))
        else:
            if self.stageJustMoved == True:
                self.timeStageEnd = time.monotonic()
                self.stageJustMoved = False
                self.commandQueue.insert(0, self._lambMill(self._safetyCheckpoint, *stage_keys))
            elif time.monotonic() - self.timeStageEnd < (self.TCcof*max(self.timeConstants) + self.TCadd):
                self.commandQueue.insert(0, self._lambMill(self._safetyCheckpoint, *stage_keys))
            else:
                pass

    def _safetyCheckpoint(self, *stage_keys):
        if self.stageJustMoved == True:
            self.timeStageEnd = time.monotonic()
            self.stageJustMoved = False
            self.commandQueue.insert(0, self._lambMill(self._safetyCheckpoint, *stage_keys))
        elif time.monotonic() - self.timeStageEnd < (self.TCcof*max(self.timeConstants) + self.TCadd):
            self.commandQueue.insert(0, self._lambMill(self._safetyCheckpoint, *stage_keys))
        else:
            pass
    
    def _safetyCheckpointMEGA(self, *stage_keys):
        while True in [self.stageBoss.moving(stage_key) for stage_key in stage_keys]:
            time.sleep(0.2)
        if self.stageJustMoved == True:
            self.timeStageEnd = time.monotonic()
            self.stageJustMoved = False
        while time.monotonic() - self.timeStageEnd < (self.TCcof*max(self.timeConstants) + self.TCadd):
            time.sleep(0.2)

    def _lambMill(self, func, *args, **kwargs):
        return lambda:func(*args, **kwargs)

    def _onPlotPlot(self, key, bool):
        self._onPlot_[key] = bool
    
    def _update_measurement_values(self):
        for key in self.lockins:
            if self.mWidgets[key]['displayE'].currentIndex() == 1:
                n = self.mWidgets[key]['ras'].value()
                if self.avgCounter > 5:
                    self.mWidgets[key]['E'].setText(format(sum(self.yVals[key][-n:])/n, '.3f'))
                    self.avgCounter = 0
                else:
                    self.avgCounter += 1
            elif self.mWidgets[key]['displayE'].currentIndex() == 2:
                try:
                    self.mWidgets[key]['E'].setText(format(self.y[key]['X'][-2], '.3f'))
                except:
                    self.mWidgets[key]['E'].setText(format(self.y[key]['X'][-1], '.3f'))
                    print('small list huh')
            elif self.mWidgets[key]['displayE'].currentIndex() == 4:
                self.mWidgets[key]['E'].setText(format(self.y[key]['Y'][-1], '.3f'))
            else:
                self.mWidgets[key]['E'].setText(format(self.yVals[key][-1], '.3f'))

    def _update_ref_freq(self):
        try:
            for key in self.lockins:
                self.mWidgets[key]['freq'].setText(format(float(self.lockins[key].get_reference_freq()), '.1f'))
        except Exception as e:
            print(e)

    def _updateAllStagePositions(self):
        try:
            if self._move != True:
                self.stageBoss.updateStagePositions()
            for stage_key in list(self.sWidgets.keys()):
                pos = self.stageBoss.getStagePosition(stage_key)
                self.sWidgets[stage_key]['pmm'].setText(format(pos, '.4f'))
        except Exception as e:
            print(e)
    
    def _updateStagePosition(self, *stage_keys):
        try:
            for stage_key in stage_keys:
                print('5 ', stage_key)
                self.stageBoss.updateStagePosition(stage_key)
                print('6 ', stage_key)
                pos = self.stageBoss.getStagePosition(stage_key)
                print('7 ', stage_key)
                self.sWidgets[stage_key]['pmm'].setText(format(pos, '.4f'))
        except Exception as e:
            print(e)

    def xlimit_change(self, index, value):
        self.plot.set_xlimit(index, value)

    def ylimit_change(self, axis, index, value):
        self.plot.set_ylimit(axis - 1, index, value)

    def _invertChange(self, index, value):
        if value:
            self.invert[index] = -1
        else:
            self.invert[index] = 1
        print(self.invert)

    def adjustTCwait(self, index, value):
        if index == 0:
            self.TCcof = value
        elif index == 1:
            self.TCadd = value

    def closeEvent(self, event):
        self._stop_stage_continuous()
        self._storeSettings()
        reply = QtWidgets.QMessageBox.question(self, 'Quit?',
                                     'Are you sure you want to quit?',
                                     QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
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
        print(stringer)

    def _storeSettings(self):
        stageSets = {}
        for stage_key in list(self.stageBoss.keys()):
            stageVals = self.stageBoss.getStageValues(stage_key)
            stageSets[stage_key] = {}
            stageSets[stage_key]['homeMem'] = self.stageBoss.getHomePosition(stage_key)
            stageSets[stage_key]['home'] = self.sWidgets[stage_key]['home'].text()
            stageSets[stage_key]['link'] = stageVals['link']
            stageSets[stage_key]['ss'] = stageVals['stepsize']
            stageSets[stage_key]['si'] = stageVals['index']
            stageSets[stage_key]['multiplier'] = stageVals['multiplier']
            stageSets[stage_key]['updatefrequency'] = stageVals['updatefrequency']
            stageSets[stage_key]['stageValues'] = stageVals.copy()
            try:
                stageSets[stage_key]['absolute'] = float(self.sWidgets[stage_key]['absolute'].text())
            except:
                stageSets[stage_key]['absolute'] = 0.0
        try:
            self.settings.setValue('stageSets', stageSets)
            self.settings.setValue('xlim0', self.SB_xlim0.value())
            self.settings.setValue('xlim1', self.SB_xlim1.value())
            self.settings.setValue('connect1', self.CB_connect1.isChecked())
            self.settings.setValue('address1', self.SP_address1.value())
            self.settings.setValue('connect2', self.CB_connect2.isChecked())
            self.settings.setValue('address2', self.SP_address2.value())
            self.settings.setValue('ESPaddress', self.SP_ESPaddress.value())
            self.settings.setValue('xunits', self.CB_xUnits.currentText())
            self.settings.setValue('xLeading', self.xLeadingStage)
        except Exception as e:
            print(e)

    def _recallSettings(self):
        try:
            self.SB_xlim0.setValue(float(self.settings.value('xlim0')))
            self.SB_xlim1.setValue(float(self.settings.value('xlim1')))
            #self.CB_xUnits.setText(str(self.settings.value('xunits')))
            stageSets = self.settings.value('stageSets')
            self.stageValueInit = {}
            for stage_key in list(stageSets.keys()):
                self.stageValueInit[stage_key] = stageSets[stage_key]['stageValues'].copy()
                #self.sVals[i]['home'] = stageSets[stage_key]['homeMem']
                self.sWidgets[stage_key]['home'].setText(format(stageSets[stage_key]['homeMem'], '.4f'))
                #self.sWidgets[stage_key]['link'].setCurrentText(stageSets[stage_key]['link'])
                self.sWidgets[stage_key]['ss'].setValue(stageSets[stage_key]['ss'])
                self.sWidgets[stage_key]['si'].setValue(stageSets[stage_key]['si'])
                self.sWidgets[stage_key]['multiplier'].setValue(stageSets[stage_key]['multiplier'])
                self.sWidgets[stage_key]['updatefrequency'].setValue(stageSets[stage_key]['updatefrequency'])
                try:
                    self.sWidgets[stage_key]['absolute'].setText(format(stageSets[stage_key]['absolute'], '.4f'))
                except:
                    self.sWidgets[stage_key]['absolute'].setText(format(0.0, '.4f'))
            self.xLeadingStage = self.settings.value('xLeading')
            self.sWidgets[self.xLeadingStage]['xlead'].setChecked(True)
            self.SP_address1.setValue(int(self.settings.value('address1')))
            self.SP_address2.setValue(int(self.settings.value('address2')))
            self.CB_connect1.setChecked(bool(self.settings.value('connect1')))
            self.CB_connect2.setChecked(bool(self.settings.value('connect2')))
            self.SP_ESPaddress.setValue(int(self.settings.value('ESPaddress')))
        except Exception as e:
            print(e)

    def _openWindow(self, window):
        window.show()

    def _openScans(self):
        self.scanWindow.show()
        self.scanWindow.onWindowOpen()

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

    def scanStart(self):
        # lock widgets, stop timer
        for key1 in self.sWidgets.keys():
            for key2 in self.sWidgets[key1].keys():
                self.sWidgets[key1][key2].setEnabled(False)
        for key1 in self.mWidgets.keys():
            for key2 in self.mWidgets[key1].keys():
                self.mWidgets[key1][key2].setEnabled(False)
        self.PB_quickFFT.setEnabled(False)
        self.CB_invert1.setEnabled(False)
        self.CB_invert2.setEnabled(False)
        self.PB_scans.setEnabled(False)
        self.SB_xlim0.setEnabled(False)
        self.SB_xlim1.setEnabled(False)
        self._timer.stop()

    def scanEnd(self):
        # resume timer, unlock all widgets
        self._timer.start()
        for key1 in self.sWidgets.keys():
            for key2 in self.sWidgets[key1].keys():
                self.sWidgets[key1][key2].setEnabled(True)
        for key1 in self.mWidgets.keys():
            for key2 in self.mWidgets[key1].keys():
                self.mWidgets[key1][key2].setEnabled(True)
        self.PB_quickFFT.setEnabled(True)
        self.CB_invert1.setEnabled(True)
        self.CB_invert2.setEnabled(True)
        self.PB_scans.setEnabled(True)
        self.SB_xlim0.setEnabled(True)
        self.SB_xlim1.setEnabled(True)
        self.PB_clearQueue.setEnabled(True)

    # ---- trouble shooting functions ----
    def _speedCheck0(self, p0 = None, p1 = None):
        if p0 == None and p1 == None:
            loopTime = time.monotonic() - self.rtTime0
            self.rtTime0 = time.monotonic()
            self.LE_speedLast0.setText(format(loopTime, '.2f'))
            self.rtList0.append(loopTime)
            self.rtList0.pop(0)
            self.LE_speedAvg0.setText(format(np.average(self.rtList0), '.2f'))
        elif p0:
            self.rtTime0 = time.monotonic()
        elif p1:
            loopTime = time.monotonic() - self.rtTime0
            self.LE_speedLast0.setText(format(loopTime, '.2f'))
            self.rtList0.append(loopTime)
            self.rtList0.pop(0)
            self.LE_speedAvg0.setText(format(np.average(self.rtList0), '.2f'))
    def _speedCheck1(self, p0 = None, p1 = None):
        if p0 == None and p1 == None:
            loopTime = time.monotonic() - self.rtTime1
            self.rtTime1 = time.monotonic()
            self.LE_speedLast1.setText(format(loopTime, '.2f'))
            self.rtList1.append(loopTime)
            self.rtList1.pop(0)
            self.LE_speedAvg1.setText(format(np.average(self.rtList1), '.2f'))
        elif p0:
            self.rtTime1 = time.monotonic()
        elif p1:
            loopTime = time.monotonic() - self.rtTime1
            self.LE_speedLast1.setText(format(loopTime, '.2f'))
            self.rtList1.append(loopTime)
            self.rtList1.pop(0)
            self.LE_speedAvg1.setText(format(np.average(self.rtList1), '.2f'))
    def _speedCheck2(self, p0 = None, p1 = None):
        if p0 == None and p1 == None:
            loopTime = time.monotonic() - self.rtTime2
            self.rtTime2 = time.monotonic()
            self.LE_speedLast2.setText(format(loopTime, '.2f'))
            self.rtList2.append(loopTime)
            self.rtList2.pop(0)
            self.LE_speedAvg2.setText(format(np.average(self.rtList2), '.2f'))
        elif p0:
            self.rtTime2 = time.monotonic()
        elif p1:
            loopTime = time.monotonic() - self.rtTime2
            self.LE_speedLast2.setText(format(loopTime, '.2f'))
            self.rtList2.append(loopTime)
            self.rtList2.pop(0)
            self.LE_speedAvg2.setText(format(np.average(self.rtList2), '.2f'))


class quickFFTWindow(QtWidgets.QWidget):
    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self)
        self.ui = uic.loadUi('quickFFT.ui',self)
        self.parent = parent

        self.PB_add.clicked.connect( self.add )

        line_dict = {1:{0:{'color':'w', 'alpha':1, 'linewidth':1}, 1:{'color':'w', 'alpha':1, 'linewidth':1}, 2:{'color':'w', 'alpha':1, 'linewidth':1}, 3:{'color':'w', 'alpha':1, 'linewidth':1}, 4:{'color':'w', 'alpha':1, 'linewidth':1}}}
        plot_dict = {1:{'ylabel':'lock-in 1', 'ylimits':[0,100]}}

        self.x = []
        self.y = {1:{}}
        self.xf = []
        self.yf = {1:{}}
        self.filled = 0
        self.len = 1000

        self.plot = dd.plotCanvas(self, line_dict = line_dict, xlabel = 'freq (ps)', plot_dict = plot_dict, autolim = False, xlimits = [10, 20], last_point = False, log = True)
        #self.logger = dd.logfileManager(self, downsample = 4)
        self.ui.GL_plot.addWidget(self.plot,0,0,1,1)

        self.SB_xlim0.valueChanged.connect( lambda : self.xlimit_change(0, self.SB_xlim0.value() ) )
        self.SB_xlim1.valueChanged.connect( lambda : self.xlimit_change(1, self.SB_xlim1.value() ) )
        self.SB_ylim01.valueChanged.connect( lambda : self.ylimit_change(0, self.SB_ylim01.value(), axis = 1 ) )
        self.SB_ylim11.valueChanged.connect( lambda : self.ylimit_change(1, self.SB_ylim11.value(), axis = 1 ) )

        quit = QtWidgets.QAction("Quit", self)
        quit.triggered.connect(self.close)

    def xlimit_change(self, index, value):
        self.plot.set_xlimit(index, value)
        self.plot.update_plot([], {1:{}})

    def ylimit_change(self, index, value, **kwargs):
        self.plot.set_ylimit(index, value, **kwargs)
        self.plot.update_plot([], {1:{}})

    def add(self):
        try:
            x = np.array(self.parent.x[:-1])/.15
            y = self.parent.y[1]['X'][:-1]
            try:
                xf, yf = self.FFT(x, y)
            except Exception as e:
                print(e)
            self.plot.add_static_line(xf, abs(yf))
            self.plot.update_plot([], {1:{}})
        except Exception as e:
            print(e)

    def closeEvent(self, event):
        self.plot.clear()
        pass

    def FFT(self, x, y):
        N = len(x)
        T = x[2] - x[1]
        yf = np.conj(fft(y))
        xf = fftfreq(N, T)[:N//2]
        return xf, 2.0/N * yf[0:N//2]

class Worker(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    def __init__(self, parent, function):
        super(Worker, self).__init__()
        self.parent = parent
        self.function = function
        
    def run(self):
        self.function()
        self.finished.emit()

class PulsesearchCanvas(FigureCanvas):
    def __init__(self, parent, xlabel = '', ylabel1 = '', ylabel2 = '', xlimits = [-1,1], ylimits = np.array([[-1,1],[-1,1]])):
        super().__init__(mpl.figure.Figure())
        self.parent = parent
        
        self.ax0 = self.figure.subplots()
        self.ax0.set_ylabel(ylabel1, fontsize=16)
        self.ax0.set_xlabel(xlabel, fontsize=16)
        self.ax0.tick_params(axis='y', labelsize = 10)
        self.ax0.minorticks_on()
        self.ax0.grid(which = 'major', color = 'yellow', linestyle = '--', linewidth = 0.5)
        self.ax0.grid(which = 'minor', color = 'yellow', linestyle = '--', linewidth = 0.25, alpha = .5)
        self.ax0.set_facecolor((0,0,0))

        self.xlimits = xlimits
        self.ylimits = ylimits

        self.ax1 = self.ax0.twinx()
        #self.ax1.spines.right.set_position(("axes", 1+.07*(0-1)))
        self.ax1.tick_params(axis='y', labelsize = 10)
        self.ax1.set_ylabel(ylabel2, fontsize=16)

        self.line0, = self.ax0.plot([], [], color = 'w', linewidth = 1)
        self.line1, = self.ax1.plot([], [], color = 'tab:red', linewidth = 1)
        self.dot0, = self.ax0.plot([], [], ms = 7, color = 'c',marker = 'D',ls = '')
        self.dot1, = self.ax1.plot([], [], ms = 7, color = 'm',marker = 'D',ls = '')

        self.figure.subplots_adjust(top=0.985,bottom=0.07,left=0.07,right=0.93,hspace=0.1,wspace=0.1)
        #self.figure.tight_layout()

        return

    def update_plot(self, x0 = [], x1 = [], y0 = [], y1 = []):
        self._update_canvas(x0, x1, y0, y1)

    def set_ylimit(self, axis, index, value):
        self.ylimits[axis, index] = value
        self._limiter()

    def set_xlimit(self, index, value):
        self.xlimits[index] = value
        self._limiter()

    def _limiter(self):
        self.ax0.set_xlim(self.xlimits[0], self.xlimits[1])
        self.ax0.set_ylim(self.ylimits[0,0], self.ylimits[0,1])
        self.ax1.set_xlim(self.xlimits[0], self.xlimits[1])
        self.ax1.set_ylim(self.ylimits[1,0], self.ylimits[1,1])

    def _update_canvas(self, x0, x1, y0, y1):
        x0, x1, y0, y1 = np.array(x0).copy(), np.array(x1).copy(), np.array(y0).copy(), np.array(y1).copy()
        self.line0.set_data( x0, y0 )
        self.line1.set_data( x1, y1 )
        if len(x0) > 0:
            self.dot0.set_data( [x0[-1]], [y0[-1]] )
        else:
            self.dot0.set_data( [], [] )
        if len(x1) > 0:
            self.dot1.set_data( [x1[-1]], [y1[-1]] )
        else:
            self.dot1.set_data( [], [] )
        if len(x0) == len(y0) and len(x1) == len(y1):
            try:
                time.sleep(.05)
                self.draw()
                time.sleep(.05)
            except Exception as e:
                print(e)
                print(x0, x1, y0, y1)
        return
    
    def _updateLastPoint(self, x0, x1, y0, y1):
        self.dot0.set_data( x0, y0 )
        self.dot1.set_data( x1, y1 )
        self.draw()
        return

    def updateLastPoint(self, x0 = [], x1 = [], y0 = [], y1 = []):
        self._updateLastPoint(x0, x1, y0, y1)

class PulsesearchCanvasXY(FigureCanvas):
    def __init__(self, parent, xlabel = '', ylabel1 = '', ylabel2 = '', xlimits = [-1,1], ylimits = np.array([[-1,1],[-1,1]])):
        super().__init__(mpl.figure.Figure())
        self.parent = parent
        
        self.ax0 = self.figure.subplots()
        self.ax0.set_ylabel(ylabel1, fontsize=16)
        self.ax0.set_xlabel(xlabel, fontsize=16)
        self.ax0.tick_params(axis='y', labelsize = 10)
        self.ax0.minorticks_on()
        self.ax0.grid(which = 'major', color = 'yellow', linestyle = '--', linewidth = 0.5)
        self.ax0.grid(which = 'minor', color = 'yellow', linestyle = '--', linewidth = 0.25, alpha = .5)
        self.ax0.set_facecolor((0,0,0))

        self.xlimits = xlimits
        self.ylimits = ylimits

        self.ax1 = self.ax0.twinx()
        #self.ax1.spines.right.set_position(("axes", 1+.07*(0-1)))
        self.ax1.tick_params(axis='y', labelsize = 10)
        self.ax1.set_ylabel(ylabel2, fontsize=16)

        self.line0X, = self.ax0.plot([], [], color = 'w', linewidth = 1)
        self.line1X, = self.ax1.plot([], [], color = 'tab:red', linewidth = 1)
        self.line0Y, = self.ax0.plot([], [], color = 'w', linewidth = 1, linestyle = 'dashed')
        self.line1Y, = self.ax1.plot([], [], color = 'tab:red', linewidth = 1, linestyle = 'dashed')
        self.dot0X, = self.ax0.plot([], [], ms = 7, color = 'c',marker = 'D',ls = '')
        self.dot1X, = self.ax1.plot([], [], ms = 7, color = 'm',marker = 'D',ls = '')
        self.dot0Y, = self.ax0.plot([], [], ms = 4, color = 'c',marker = 's',ls = '')
        self.dot1Y, = self.ax1.plot([], [], ms = 4, color = 'm',marker = 's',ls = '')

        self.figure.subplots_adjust(top=0.985,bottom=0.07,left=0.07,right=0.93,hspace=0.1,wspace=0.1)

        return

    def update_plot(self, x0X = [], x0Y = [], x1X = [], x1Y = [], y0X = [], y0Y = [], y1X = [], y1Y = []):
        self._update_canvas(x0X, x0Y, x1X, x1Y, y0X, y0Y, y1X, y1Y)

    def set_ylimit(self, axis, index, value):
        self.ylimits[axis, index] = value
        self._limiter()

    def set_xlimit(self, index, value):
        self.xlimits[index] = value
        self._limiter()

    def _limiter(self):
        self.ax0.set_xlim(self.xlimits[0], self.xlimits[1])
        self.ax0.set_ylim(self.ylimits[0,0], self.ylimits[0,1])
        self.ax1.set_xlim(self.xlimits[0], self.xlimits[1])
        self.ax1.set_ylim(self.ylimits[1,0], self.ylimits[1,1])

    def _update_canvas(self, x0X, x0Y, x1X, x1Y, y0X, y0Y, y1X, y1Y):
        x0X, x0Y, x1X, x1Y, y0X, y0Y, y1X, y1Y = np.array(x0X).copy(), np.array(x0Y).copy(), np.array(x1X).copy(), np.array(x1Y).copy(), np.array(y0X).copy(), np.array(y0Y).copy(), np.array(y1X).copy(), np.array(y1Y).copy()
        self.line0X.set_data( x0X, y0X )
        self.line1X.set_data( x1X, y1X )
        self.line0Y.set_data( x0Y, y0Y )
        self.line1Y.set_data( x1Y, y1Y )
        if len(x0X) > 0:
            self.dot0X.set_data( [x0X[-1]], [y0X[-1]] )
        else:
            self.dot0X.set_data( [], [] )
        if len(x0Y) > 0:
            self.dot0Y.set_data( [x0Y[-1]], [y0Y[-1]] )
        else:
            self.dot0Y.set_data( [], [] )
        if len(x1X) > 0:
            self.dot1X.set_data( [x1X[-1]], [y1X[-1]] )
        else:
            self.dot1X.set_data( [], [] )
        if len(x1Y) > 0:
            self.dot1Y.set_data( [x1Y[-1]], [y1Y[-1]] )
        else:
            self.dot1Y.set_data( [], [] )
        if len(x0X) == len(y0X) and len(x1X) == len(y1X) and len(x0Y) == len(y0Y) and len(x1Y) == len(y1Y):
            try:
                time.sleep(.05)
                self.draw()
                time.sleep(.05)
            except Exception as e:
                print(e)
                print(x0X, x0Y, x1X, x1Y, y0X, y0Y, y1X, y1Y)
        return
    
    def _updateLastPoint(self, x0X, x0Y, x1X, x1Y, y0X, y0Y, y1X, y1Y):
        self.dot0X.set_data( x0X, y0X )
        self.dot1X.set_data( x1X, y1X )
        self.dot0Y.set_data( x0Y, y0Y )
        self.dot1Y.set_data( x1Y, y1Y )
        self.draw()
        return

    def updateLastPoint(self, x0X = [], x0Y = [], x1X = [], x1Y = [], y0X = [], y0Y = [], y1X = [], y1Y = []):
        self._updateLastPoint(x0X, x0Y, x1X, x1Y, y0X, y0Y, y1X, y1Y)

class PulsesearchCanvasXYdel(FigureCanvas):
    def __init__(self, parent, xlabel = '', ylabel1 = '', ylabel2 = '', xlimits = [-1,1], ylimits = np.array([[-1,1],[-1,1]])):
        super().__init__(mpl.figure.Figure())
        self.parent = parent

        self.ax0 = self.figure.subplots()
        self.ax0.set_ylabel(ylabel1, fontsize=20)
        self.ax0.set_xlabel(xlabel, fontsize=20)
        self.ax0.minorticks_on()
        self.ax0.grid(which = 'major', color = 'yellow', linestyle = '--', linewidth = 0.5)
        self.ax0.grid(which = 'minor', color = 'yellow', linestyle = '--', linewidth = 0.25, alpha = .5)
        self.ax0.set_facecolor((0,0,0))

        self.xlimits = xlimits
        self.ylimits = ylimits

        self.ax1 = self.ax0.twinx()
        self.ax1.spines.right.set_position(("axes", 1+.07*(0-1)))
        self.ax1.tick_params(axis='y', labelsize = 7)
        self.ax1.set_ylabel(ylabel2, fontsize=16)

        self.line0X, = self.ax0.plot([], [], color = 'w', linewidth = 1)
        self.line1X, = self.ax1.plot([], [], color = 'tab:red', linewidth = 1)
        self.line0Y, = self.ax0.plot([], [], color = 'w', linewidth = 1, linestyle = 'dashed')
        self.line1Y, = self.ax1.plot([], [], color = 'tab:red', linewidth = 1, linestyle = 'dashed')
        self.dot0X, = self.ax0.plot([], [], ms = 7, color = 'c',marker = 'D',ls = '')
        self.dot1X, = self.ax1.plot([], [], ms = 7, color = 'm',marker = 'D',ls = '')
        self.dot0Y, = self.ax0.plot([], [], ms = 4, color = 'c',marker = 's',ls = '')
        self.dot1Y, = self.ax1.plot([], [], ms = 4, color = 'm',marker = 's',ls = '')
        return

    def update_plot(self, x0X = [], x0Y = [], x1X = [], x1Y = [], y0X = [], y0Y = [], y1X = [], y1Y = []):
        self._update_canvas(x0X, x0Y, x1X, x1Y, y0X, y0Y, y1X, y1Y)

    def set_ylimit(self, axis, index, value):
        self.ylimits[axis, index] = value
        self._limiter()

    def set_xlimit(self, index, value):
        self.xlimits[index] = value
        self._limiter()

    def _limiter(self):
        self.ax0.set_xlim(self.xlimits[0], self.xlimits[1])
        self.ax0.set_ylim(self.ylimits[0,0], self.ylimits[0,1])
        self.ax1.set_xlim(self.xlimits[0], self.xlimits[1])
        self.ax1.set_ylim(self.ylimits[1,0], self.ylimits[1,1])

    def _update_canvas(self, x0X, x0Y, x1X, x1Y, y0X, y0Y, y1X, y1Y):
        self.line0X.set_data( x0X, y0X )
        self.line1X.set_data( x1X, y1X )
        self.line0X.set_data( x0Y, y0Y )
        self.line1X.set_data( x1Y, y1Y )
        self.draw()
        return
    
    def _updateLastPoint(self, x0X, x0Y, x1X, x1Y, y0X, y0Y, y1X, y1Y):
        self.dot0X.set_data( x0X, y0X )
        self.dot1X.set_data( x1X, y1X )
        self.dot0Y.set_data( x0Y, y0Y )
        self.dot1Y.set_data( x1Y, y1Y )
        self.draw()
        return

    def updateLastPoint(self, x0X = [], x0Y = [], x1X = [], x1Y = [], y0X = [], y0Y = [], y1X = [], y1Y = []):
        self._updateLastPoint(x0X, x0Y, x1X, x1Y, y0X, y0Y, y1X, y1Y)


class stageBoss():
    def __init__(self):
        self.stages = {}
        self.stageValues = {}
        
    def assignMotionController(self, motionController):
        self.motionController = motionController
    def addStage(self, stage_key, stage_dict):
        self.stageValues[stage_key] = stage_dict

    def setMultiplier(self, stage_key, value):
        self.stageValues[stage_key]['multiplier'] = value
    def setIndex(self, stage_key, value):
        self.stageValues[stage_key]['index'] = value
    def setStepsize(self, stage_key, value):
        self.stageValues[stage_key]['stepsize'] = value
    def setUpdateFrequency(self, stage_key, value):
        self.stageValues[stage_key]['updatefrequency'] = value

    def linkStage(self, stage_key, link_key):
        if self.stageValues[stage_key]['link'] == None:
            self.stageValues[stage_key]['link'] = link_key
            if stage_key not in self.stageValues[link_key]['children'] and stage_key != link_key:
                self.stageValues[link_key]['children'].append(stage_key)
                print(self.stageValues[link_key]['children'])
        else:
            self.unlinkStage(stage_key)
            self.stageValues[stage_key]['link'] = link_key
            if stage_key not in self.stageValues[link_key]['children'] and stage_key != link_key:
                self.stageValues[link_key]['children'].append(stage_key)
                print(self.stageValues[link_key]['children'])
    def unlinkStage(self, stage_key):
        while stage_key in self.stageValues[self.stageValues[stage_key]['link']]['children']:
            self.stageValues[self.stageValues[stage_key]['link']]['children'].remove(stage_key)
        self.stageValues[stage_key]['link'] = None
    def getChildren(self, stage_key):
        return self.stageValues[stage_key]['children']
    def clearChildren(self, stage_key):
        self.stageValues[stage_key]['children'] = []
    def clearAllChildren(self):
        for key in self.stageValues:
            print(self.stageValues[key]['children'])
            self.stageValues[key]['children'] = []

    def updateStagePositions(self):
        for stage_key in self.stageValues:
            if self.stageValues[stage_key]['updatefrequency'] == 0:
                self.stageValues[stage_key]['position'] = self.motionController.get_absolute_position(stage_key = stage_key, index = self.stageValues[stage_key]['index'])
            elif self.stageValues[stage_key]['updatefrequency'] < 0:
                pass
            elif time.monotonic() - self.stageValues[stage_key]['updatetime'] > self.stageValues[stage_key]['updatefrequency']:
                self.stageValues[stage_key]['position'] = self.motionController.get_absolute_position(stage_key = stage_key, index = self.stageValues[stage_key]['index'])
                self.stageValues[stage_key]['updatetime'] = time.monotonic()
            else:
                pass
    def updateStagePosition(self, stage_key):
        #time.sleep(0.1)
        self.stageValues[stage_key]['position'] = self.motionController.get_absolute_position(stage_key = stage_key, index = self.stageValues[stage_key]['index'])
        self.stageValues[stage_key]['updatetime'] = time.monotonic()
    def getStagePosition(self, stage_key):
        return self.stageValues[stage_key]['position']

    def setHomePosition(self, stage_key, position):
        self.stageValues[stage_key]['home'] = position
    def getHomePosition(self, stage_key):
        return self.stageValues[stage_key]['home']

    def moveStageStep(self, stage_key, pn = 1):
        self.motionController.move_step(stage_key = stage_key, index = self.stageValues[stage_key]['index'], step_size = pn*self.stageValues[stage_key]['stepsize']*self.stageValues[stage_key]['multiplier'])
        for child_key in self.stageValues[stage_key]['children']:
            self.motionController.move_step(stage_key = child_key, index = self.stageValues[child_key]['index'], step_size = pn*self.stageValues[stage_key]['stepsize']*self.stageValues[child_key]['multiplier'])

    def moveStageHome(self, stage_key):
        self.motionController.move_absolute(stage_key = stage_key, index = self.stageValues[stage_key]['index'], position = self.stageValues[stage_key]['home'])
        for child_key in self.stageValues[stage_key]['children']:
            self.motionController.move_absolute(stage_key = child_key, index = self.stageValues[child_key]['index'], position = self.stageValues[child_key]['home'])

    def moveStageAbsolute(self, stage_key, position):
        self.motionController.move_absolute(stage_key = stage_key, index = self.stageValues[stage_key]['index'], position = position)

    def moving(self, stage_key):
        self.motionController.moving(stage_key = stage_key, index = self.stageValues[stage_key]['index'])

    def keys(self):
        return self.stageValues.keys()
    
    def getStageValues(self, stage_key):
        return self.stageValues[stage_key].copy()

class motionController():
    def __init__(self, deviceDict, unitMultiplier):
        self.stages = deviceDict
        self.unitMultiplier = unitMultiplier

    def move_absolute(self, stage_key, index, position):
        self.stages[stage_key].move_absolute(axis_number = index, position = position)

    def move_step(self, stage_key, index, step_size):
        self.stages[stage_key].move_step(axis_number = index, step_size = step_size*self.unitMultiplier[stage_key])

    def get_absolute_position(self, stage_key, index):
        return self.stages[stage_key].get_absolute_position(axis_number = index)

    def moving(self, stage_key, index):
        return self.stages[stage_key].moving(axis_number = index)
    
class savePlotWindow(QtWidgets.QWidget):
    def __init__(self, parent, whoami = 'savePlot'):
        QtWidgets.QWidget.__init__(self)
        self.ui = uic.loadUi('savePlot.ui',self)
        self.resize(700, 100)
        self.me = whoami
        self.parent = parent

        self.PB_browse.clicked.connect(self._browse)
        self.PB_save.clicked.connect(self._save)

    def _browse(self):
        fname = QtWidgets.QFileDialog.getSaveFileName(self, ' Select File ', os.path.expanduser('~/Documents'), 'Text Files (*.txt)')
        self.LE_path.setText(fname[0])

    def _save(self):
        plotVals, units = self.parent.getPlotValues()
        if type(plotVals) == np.ndarray:
            try:
                np.savetxt(str(self.LE_path.text()), plotVals.T, fmt = '%.7f', header = ' '.join(units))
                self.hide()
            except Exception as e:
                print(e)
        else:
            print('no save, empty plotVals')
