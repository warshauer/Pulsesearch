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
from warsh_comms import smsClient
#from flowControllerClasses import Flowmeter
from instrumentControl import esp301_GPIB, sr830
import time
from scipy.fft import fft, fftfreq
from scanProg import DLscanWindow

class pulsesearchWindow(QtWidgets.QMainWindow):
    def __init__(self, whoami = 'pulseSearch', version = 'v1.3', ESP_port = 1, lockin1_port = 8, lockin2_port = 7):
        QtWidgets.QMainWindow.__init__(self)
        self.ui = uic.loadUi('pulsesearch.ui',self) # swap this to pyui5 instead, then we may export it out to a class to make generic, contain and sort widgets and variables
        self.resize(1700, 1000)
        self.me = whoami

        self.instrumentsConnected = False

        self.threadpool = QtCore.QThreadPool()	
        self.threadpool.setMaxThreadCount(1)

        self.settings = QtCore.QSettings(self.me, version)

        self._timeConstantList = [.00001, .00003, .0001, .0003, .001, .003, .01, .03, .1, .3, 1, 3, 10, 30, 100, 300, 1000, 3000, 10000, 30000]
        self._sensitivityList = [2, 5, 10, 20, 50, 100, 200, 500, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1]

        #self.plot = dd.fastCanvas(self, line_dict = line_dict, xlabel = 'time (ps)', plot_dict = plot_dict, autolim = False, xlimits = [-1, 1], last_point = True)
        self.plot = PulsesearchCanvas(self, xlabel = 'time (ps)', ylabel1 = 'lock-in 1', ylabel2 = 'lock-in 2', xlimits = [-1, 1])
        self.ui.GL_plot.addWidget(self.plot,0,0,1,1)

        self._move = False
        self.sms = smsClient()
        self._cmi = 0
        self._cmpn = 1
        self._toggles = {'1_op':True, '2_op':False}
        self.avgCounter = 0
        self.counter0 = 0
        self.counter1 = 0
        self.TCsafety = True
        self._onPlot_ = {1:True, 2:False}

        self.motionAllowed = True
        self.addNext = False
        self.stageJustMoved = False
        self.timeStageEnd = time.monotonic()
        self.loot = time.monotonic()
        self.timeConstants = [0,0]

        self.quickFFT = quickFFTWindow(self)
        self.scanWindow = DLscanWindow(self)

        self.PB_quickFFT.clicked.connect(lambda : self._openWindow(self.quickFFT))
        self.PB_scans.clicked.connect(self._openScans)
        self.PB_connect.clicked.connect(self._connectInstruments)
        self.invert = [1,1]
        self.CB_invert1.stateChanged.connect(lambda : self._invertChange(0, self.CB_invert1.isChecked()))
        self.CB_invert2.stateChanged.connect(lambda : self._invertChange(1, self.CB_invert2.isChecked()))

        if True:
            self.yVals = {1:[0,0,0,0,0,0,0,0,0,0], 2:[0,0,0,0,0,0,0,0,0,0]}
            self.mWidgets = {}
            self.mWidgets[1] = {'E':self.LE_E1, 'freq':self.LE_freq1, 'onplot':self.CB_onplot1, 'sensitivity':self.CB_sens1, 'timeconstant':self.CB_tc1, 'inputconfig':self.CB_ic1, 'ylim0':self.SB_ylim01, 'ylim1':self.SB_ylim11, 'autophase':self.PB_autophase1, 'displayE':self.CB_dispE1, 'ras':self.SP_ras1}
            self.mWidgets[2] = {'E':self.LE_E2, 'freq':self.LE_freq2, 'onplot':self.CB_onplot2, 'sensitivity':self.CB_sens2, 'timeconstant':self.CB_tc2, 'inputconfig':self.CB_ic2, 'ylim0':self.SB_ylim02, 'ylim1':self.SB_ylim12, 'autophase':self.PB_autophase2, 'displayE':self.CB_dispE2, 'ras':self.SP_ras2}


            self.mWidgets[1]['onplot'].stateChanged.connect(lambda:self._onPlotPlot(1, self.mWidgets[1]['onplot'].isChecked()))
            self.mWidgets[2]['onplot'].stateChanged.connect(lambda:self._onPlotPlot(2, self.mWidgets[2]['onplot'].isChecked()))

            self.mWidgets[1]['sensitivity'].currentIndexChanged.connect(lambda : self._sensitivityChange(1, self.mWidgets[1]['sensitivity'].currentIndex()))
            self.mWidgets[1]['timeconstant'].currentIndexChanged.connect(lambda : self._timeconstantChange(1, self.mWidgets[1]['timeconstant'].currentIndex()))
            self.mWidgets[1]['inputconfig'].currentIndexChanged.connect(lambda : self._inputconfigChange(1, self.mWidgets[1]['inputconfig'].currentIndex()))

            self.mWidgets[2]['sensitivity'].currentIndexChanged.connect(lambda : self._sensitivityChange(2, self.mWidgets[2]['sensitivity'].currentIndex()))
            self.mWidgets[2]['timeconstant'].currentIndexChanged.connect(lambda : self._timeconstantChange(2, self.mWidgets[2]['timeconstant'].currentIndex()))
            self.mWidgets[2]['inputconfig'].currentIndexChanged.connect(lambda : self._inputconfigChange(2, self.mWidgets[2]['inputconfig'].currentIndex()))

        if True:
            self.sVals = {}
            for stage in range(1,5):
                self.sVals[stage] = {'home':0.00, 'pos':0, 'linked':False, 'linkedstage':0, 'linkeddir':1, 'children':[]}

            self.sWidgets = {}
            self.sWidgets[1] = {'sn':self.PB_sn0, 'sp':self.PB_sp0, 'sethome':self.PB_sethome0, 'returnhome':self.PB_returnhome0, 'mn':self.PB_mn0, 'mp':self.PB_mp0, 'linkedstage':self.CB_linkedstage0, 
                                'linkeddir':self.CB_linkeddir0, 'ss':self.SB_ss0, 'si':self.SB_si0, 'multiplier':self.SB_multiplier0, 'pmm':self.LE_pmm0, 'pps':self.LE_pps0, 'home':self.LE_home0, 'stop':self.PB_stop0}
            self.sWidgets[2] = {'sn':self.PB_sn1, 'sp':self.PB_sp1, 'sethome':self.PB_sethome1, 'returnhome':self.PB_returnhome1, 'mn':self.PB_mn1, 'mp':self.PB_mp1, 'linkedstage':self.CB_linkedstage1, 
                                'linkeddir':self.CB_linkeddir1, 'ss':self.SB_ss1, 'si':self.SB_si1, 'multiplier':self.SB_multiplier1, 'pmm':self.LE_pmm1, 'pps':self.LE_pps1, 'home':self.LE_home1, 'stop':self.PB_stop1}
            self.sWidgets[3] = {'sn':self.PB_sn2, 'sp':self.PB_sp2, 'sethome':self.PB_sethome2, 'returnhome':self.PB_returnhome2, 'mn':self.PB_mn2, 'mp':self.PB_mp2, 'linkedstage':self.CB_linkedstage2, 
                                'linkeddir':self.CB_linkeddir2, 'ss':self.SB_ss2, 'si':self.SB_si2, 'multiplier':self.SB_multiplier2, 'pmm':self.LE_pmm2, 'pps':self.LE_pps2, 'home':self.LE_home2, 'stop':self.PB_stop2}
            self.sWidgets[4] = {'sn':self.PB_sn3, 'sp':self.PB_sp3, 'sethome':self.PB_sethome3, 'returnhome':self.PB_returnhome3, 'mn':self.PB_mn3, 'mp':self.PB_mp3, 'linkedstage':self.CB_linkedstage3, 
                                'linkeddir':self.CB_linkeddir3, 'ss':self.SB_ss3, 'si':self.SB_si3, 'multiplier':self.SB_multiplier3, 'pmm':self.LE_pmm3, 'pps':self.LE_pps3, 'home':self.LE_home3, 'stop':self.PB_stop3}
            
            # why didn't this work in a for loop :(
            self.sWidgets[3]['sn'].clicked.connect(lambda : self._move_stage_step(3, -1))
            self.sWidgets[3]['sp'].clicked.connect(lambda : self._move_stage_step(3, 1))
            self.sWidgets[3]['mn'].clicked.connect(lambda : self._move_stage_continuous(3, -1))
            self.sWidgets[3]['mp'].clicked.connect(lambda : self._move_stage_continuous(3, 1))
            self.sWidgets[3]['stop'].clicked.connect(self._stop_stage_continuous)
            self.sWidgets[3]['sethome'].clicked.connect(lambda : self._set_home(3, float(self.sVals[3]['pos'] ))) # finish
            self.sWidgets[3]['returnhome'].clicked.connect(lambda : self._return_to_home(3)) # finish
            self.sWidgets[3]['linkedstage'].currentIndexChanged.connect(lambda : self._set_stage_link( 3, self.sWidgets[3]['linkedstage'].currentIndex()))

            self.sWidgets[1]['sn'].clicked.connect(lambda : self._move_stage_step(1, -1))
            self.sWidgets[1]['sp'].clicked.connect(lambda : self._move_stage_step(1, 1))
            self.sWidgets[1]['mn'].clicked.connect(lambda : self._move_stage_continuous(1, -1))
            self.sWidgets[1]['mp'].clicked.connect(lambda : self._move_stage_continuous(1, 1))
            self.sWidgets[1]['stop'].clicked.connect(self._stop_stage_continuous)
            self.sWidgets[1]['sethome'].clicked.connect(lambda : self._set_home(1, float(self.sVals[1]['pos'] ))) # finish
            self.sWidgets[1]['returnhome'].clicked.connect(lambda : self._return_to_home(1)) # finish
            self.sWidgets[1]['linkedstage'].currentIndexChanged.connect(lambda : self._set_stage_link( 1, self.sWidgets[1]['linkedstage'].currentIndex()))

            self.sWidgets[2]['sn'].clicked.connect(lambda : self._move_stage_step(2, -1))
            self.sWidgets[2]['sp'].clicked.connect(lambda : self._move_stage_step(2, 1))
            self.sWidgets[2]['mn'].clicked.connect(lambda : self._move_stage_continuous(2, -1))
            self.sWidgets[2]['mp'].clicked.connect(lambda : self._move_stage_continuous(2, 1))
            self.sWidgets[2]['stop'].clicked.connect(self._stop_stage_continuous)
            self.sWidgets[2]['sethome'].clicked.connect(lambda : self._set_home(2, float(self.sVals[2]['pos'] ))) # finish
            self.sWidgets[2]['returnhome'].clicked.connect(lambda : self._return_to_home(2)) # finish
            self.sWidgets[2]['linkedstage'].currentIndexChanged.connect(lambda : self._set_stage_link( 2, self.sWidgets[2]['linkedstage'].currentIndex()))

            self.sWidgets[4]['sn'].clicked.connect(lambda : self._move_stage_step(4, -1))
            self.sWidgets[4]['sp'].clicked.connect(lambda : self._move_stage_step(4, 1))
            self.sWidgets[4]['mn'].clicked.connect(lambda : self._move_stage_continuous(4, -1))
            self.sWidgets[4]['mp'].clicked.connect(lambda : self._move_stage_continuous(4, 1))
            self.sWidgets[4]['stop'].clicked.connect(self._stop_stage_continuous)
            self.sWidgets[4]['sethome'].clicked.connect(lambda : self._set_home(4, float(self.sVals[4]['pos'] ))) # finish
            self.sWidgets[4]['returnhome'].clicked.connect(lambda : self._return_to_home(4)) # finish
            self.sWidgets[4]['linkedstage'].currentIndexChanged.connect(lambda : self._set_stage_link( 4, self.sWidgets[4]['linkedstage'].currentIndex()))

            self.sWidgets[1]['si'].setEnabled(False)
            self.sWidgets[2]['si'].setEnabled(False)
            self.sWidgets[3]['si'].setEnabled(False)
            self.sWidgets[4]['si'].setEnabled(False)




            self.SB_xlim0.valueChanged.connect( lambda : self.xlimit_change( 0, self.SB_xlim0.value() ) )
            self.SB_xlim1.valueChanged.connect( lambda : self.xlimit_change( 1, self.SB_xlim1.value() ) )
            self.SB_ylim01.valueChanged.connect( lambda : self.ylimit_change( 1, 0, self.SB_ylim01.value()) )
            self.SB_ylim11.valueChanged.connect( lambda : self.ylimit_change( 1, 1, self.SB_ylim11.value()) )
            self.SB_ylim02.valueChanged.connect( lambda : self.ylimit_change( 2, 0, self.SB_ylim02.value()) )
            self.SB_ylim12.valueChanged.connect( lambda : self.ylimit_change( 2, 1, self.SB_ylim12.value()) )

        self._sample_interval = 50
        self._timer = QtCore.QTimer()
        self._timer.setInterval(self._sample_interval) #msec
        self._timer.timeout.connect(self.runtime_function)
        self._timer.start()

        #self.sVals[1]['pos'], self.sVals[2]['pos'], self.sVals[3]['pos'] = self.esp.positions()
        #self._update_ref_freq()
        #for i in range(3):
        #    self._set_home(i+1, self.sVals[i+1]['pos'])
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
        self.stageController = esp301_GPIB(stagePort)
        # update how many stages are active:
        self.activeStages = [1, 2, 3]#, 4]
        for stage in range(1,5):
            if stage not in self.activeStages:
                self.sVals.pop(stage)
                self._link_enable(stage, False)
                self.sWidgets[stage]['sethome'].setEnabled(False)
                self.sWidgets[stage]['linkedstage'].setEnabled(False)
                print(self.sVals.keys())

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
        for key in self.sVals:
            self.sVals[key]['pos'] = self.stageController.get_absolute_position(self.sWidgets[key]['si'].value())
            self._update_stage_values(key, self.sVals[key]['pos'])
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
        self.y[1] = np.array([])
        self.y[2] = np.array([])
        for key in self.lockins:
            self.y[key] = np.append(self.y[key], [self._get_measurement(self.lockins[key])])
            self._sensitivityChange(key, self.lockins[key].get_sensitivity())
            self.timeConstants[key-1] = self._timeConstantList[self.lockins[key].get_time_constant()]
            self.mWidgets[key]['autophase'].clicked.connect(self.lockins[key].auto_phase)
            self.mWidgets[key]['sensitivity'].setCurrentIndex(self.lockins[key].get_sensitivity())
            self.mWidgets[key]['timeconstant'].setCurrentIndex(self.lockins[key].get_time_constant())
            self.mWidgets[key]['inputconfig'].setCurrentIndex(self.lockins[key].get_input_config())
        self.x = np.append(self.x, [0])
        self.instrumentsConnected = True

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

    def _set_home(self, index, value):
        try:
            #self.sVals[index]['home'] = value
            self.sWidgets[index]['home'].setText(format(value, '.4f'))
        except Exception as e:
            print(e)

    def _set_stage_link(self, index, link):
        if link == 0:
            self.sVals[index]['linked'] = False
            for key in self.sVals:
                try:
                    self.sVals[key]['children'] = [ x for x in self.sVals[key]['children'] if x is not index ]
                except:
                    pass
            self._link_enable(index, True)
        else:
            if link >= index:
                link = link +1
            self.sVals[index]['linkedstage'] = link
            self.sVals[index]['linked'] = True
            if index not in self.sVals[link]['children']:
                self.sVals[link]['children'].append(index)
            if self.sWidgets[index]['linkeddir'].currentIndex() == 0:
                self.sVals[index]['linkeddir'] = 1
            else:
                self.sVals[index]['linkeddir'] = -1
            self._link_enable(index, False)

    def _link_enable(self, index, boo):
        for widg in ['mn', 'sn', 'sp', 'mp', 'returnhome', 'stop', 'ss', 'linkeddir', 'multiplier']:
            self.sWidgets[index][widg].setEnabled(boo)

    def _return_to_home(self, index):
        homeph = self.sVals[index]['home']
        try:
            self.sVals[index]['home'] = float(self.sWidgets[index]['home'].text())
        except Exception as e:
            self.sVals[index]['home'] = homeph
            print(e)
        self.stageController.move_to_position(index, self.sVals[index]['home'])
        for child in self.sVals[index]['children']:
            homeph = self.sVals[child]['home']
            try:
                self.sVals[child]['home'] = float(self.sWidgets[child]['home'].text())
            except Exception as e:
                self.sVals[child]['home'] = homeph
                print(e)
            self.stageController.move_to_position(child, self.sVals[child]['home'])

        self.x = np.array([0])
        self.y = {}
        self.y[1] = np.array([0])
        self.y[2] = np.array([0])
        while self.stageController.moving():
            time.sleep(.01)
        time.sleep(max(self.timeConstants))
        self.appendData()
        self.addNext = True
        self.motionAllowed = False
        self.stageJustMoved = True

    def _move_stage_step(self, index, pn):
        if self.motionAllowed:
            step = pn*self.sWidgets[index]['ss'].value()*.001
            self.stageController.move_step(self.sWidgets[index]['si'].value(), step*self.sWidgets[index]['multiplier'].value())
            for child in self.sVals[index]['children']:
                self.stageController.move_step(self.sWidgets[child]['si'].value(), self.sVals[child]['linkeddir']*step*self.sWidgets[child]['multiplier'].value())
            if index == self.CB_xleading.currentIndex()+1:
                self.addNext = True
            self.motionAllowed = False
            self.stageJustMoved = True
            self.TCsafety = False

    def _update_stage_positions(self):
        try:
            for key in self.sVals:
                self.sVals[key]['pos'] = self.stageController.get_absolute_position(self.sWidgets[key]['si'].value())
                self._update_stage_values(key, self.sVals[key]['pos'])
        except Exception as e:
            print(e)

    def appendData(self):
        for key in self.lockins:
            self.y[key][-1] = self._get_measurement(self.lockins[key])
            self.y[key] = np.append(self.y[key], [self._get_measurement(self.lockins[key])])
            #self.y[key].append(self._get_measurement(self.lockins[key]))
        self._update_measurement_values()
        self._update_stage_positions()
        pos = self.sVals[self.CB_xleading.currentIndex()+1]['pos'] - self.sVals[self.CB_xleading.currentIndex()+1]['home']
        self.x[-1] = pos
        self.x = np.append(self.x, [pos])
        #print('fin: ', time.monotonic() - self.loot)
        self.loot = time.monotonic()
        #self.x.append(self.sVals[self.CB_xleading.currentIndex()+1]['pos'] - self.sVals[self.CB_xleading.currentIndex()+1]['home'])

    def _move_stage_continuous(self, index, pn):
        self._move = True
        self._cmi = index
        self._cmpn = pn

    def _stop_stage_continuous(self):
        self._move = False

    def _change_sample_interval(self, value):
        self._sample_interval = value
        self._timer.setInterval(self._sample_interval)

    def _get_measurement(self, lockin):
        return lockin.get_output()
        
    def refreshData(self):
        for key in self.lockins:
            if self.mWidgets[key]['displayE'].currentIndex() == 3:
                if self.TCsafety:
                    y = self._get_measurement(self.lockins[key])
                    self.yVals[key].append(y)
                    self.yVals[key] = self.yVals[key][1:]
                    self.y[key][-1] = y
                else:
                    pass
            else:
                y = self._get_measurement(self.lockins[key])
                self.yVals[key].append(y)
                self.yVals[key] = self.yVals[key][1:]
                self.y[key][-1] = y

    def plotUpdate(self):
        if self.workerFinished0:
            self.workerFinished0 = False
            if self._onPlot_[1]:
                x1LI = self.x * self.invert[0]
                y1LI = self.y[1]
            else:
                x1LI = np.array([])
                y1LI = np.array([])
            if self._onPlot_[2]:
                x2LI = self.x * self.invert[1]
                y2LI = self.y[2]
            else:
                x2LI = np.array([])
                y2LI = np.array([])
            if len(x1LI) == len(y1LI) and len(x2LI) == len(y2LI):
                self.plot.update_plot(x1LI/.15, x2LI/.15, y1LI, y2LI)
            self.workerFinished0 = True

    # HERE IS THE RUNTIME
    def runtime_function(self):
        # check whether to append data:
        if self.instrumentsConnected:
            if self.stageController.moving() == False:
                if self.stageJustMoved == True:
                    self.timeStageEnd = time.monotonic()
                    self.stageJustMoved = False
                else:
                    if time.monotonic() - self.timeStageEnd > 2.0*max(self.timeConstants):
                        if self.addNext:
                            self.appendData()
                            self.addNext = False
                        self.TCsafety = True
                        self.motionAllowed = True
            # get lockin readings
            self.refreshData()
            self._update_measurement_values()
            self._update_stage_positions()
            if self._move:
                self._move_stage_step(self._cmi, self._cmpn)
            self._threadWork(self.plotUpdate)
            if self.counter1 > 1000:
                self.counter1 = 0
                self._update_ref_freq()
            else:
                self.counter1 += 1

    def _onPlotPlot(self, index, bool):
        self._onPlot_[index] = bool
    
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
                    self.mWidgets[key]['E'].setText(format(self.y[key][-2], '.3f'))
                except:
                    self.mWidgets[key]['E'].setText(format(self.y[key][-1], '.3f'))
                    print('small list huh')
            else:
                self.mWidgets[key]['E'].setText(format(self.yVals[key][-1], '.3f'))

    def _update_ref_freq(self):
        try:
            for key in self.lockins:
                self.mWidgets[key]['freq'].setText(format(float(self.lockins[key].get_reference_freq()), '.1f'))
        except Exception as e:
            print(e)

    def _update_stage_values(self, index, pos):
        self.sWidgets[index]['pmm'].setText(format(pos, '.4f'))
        self.sWidgets[index]['pps'].setText(format((pos - self.sVals[index]['home'])/.15, '.4f'))

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
        self.sms.send(stringer, self.LE_phonenumber.text())

    def _storeSettings(self):
        stageSets = {}
        for i in range(1,5):
            stageSets[i] = {}
            if i in list(self.sVals.keys()):
                stageSets[i]['homeMem'] = self.sVals[i]['home']
                print('save '+str(i))
            else:
                stageSets[i]['homeMem'] = 0.00
                print('hmmm '+str(i))
            stageSets[i]['home'] = self.sWidgets[i]['home'].text()
            stageSets[i]['linkeddir'] = self.sWidgets[i]['linkeddir'].currentIndex()
            stageSets[i]['ss'] = self.sWidgets[i]['ss'].value()
            stageSets[i]['si'] = self.sWidgets[i]['si'].value()
            stageSets[i]['multiplier'] = self.sWidgets[i]['multiplier'].value()
        try:
            self.settings.setValue('stageSets', stageSets)
            self.settings.setValue('xlim0', self.SB_xlim0.value())
            self.settings.setValue('xlim1', self.SB_xlim1.value())
            self.settings.setValue('xleading', self.CB_xleading.currentIndex())
            self.settings.setValue('connect1', self.CB_connect1.isChecked())
            self.settings.setValue('address1', self.SP_address1.value())
            self.settings.setValue('connect2', self.CB_connect2.isChecked())
            self.settings.setValue('address2', self.SP_address2.value())
            self.settings.setValue('ESPaddress', self.SP_ESPaddress.value())
        except Exception as e:
            print(e)

    def _recallSettings(self):
        try:
            self.SB_xlim0.setValue(float(self.settings.value('xlim0')))
            self.SB_xlim1.setValue(float(self.settings.value('xlim1')))
            stageSets = self.settings.value('stageSets')
            for i in range(1,5):
                self.sVals[i]['home'] = stageSets[i]['homeMem']
                self.sWidgets[i]['home'].setText(format(stageSets[i]['homeMem'], '.4f'))
                self.sWidgets[i]['linkeddir'].setCurrentIndex(stageSets[i]['linkeddir'])
                self.sWidgets[i]['ss'].setValue(stageSets[i]['ss'])
                self.sWidgets[i]['si'].setValue(stageSets[i]['si'])
                self.sWidgets[i]['multiplier'].setValue(stageSets[i]['multiplier'])
            self.CB_xleading.setCurrentIndex(self.settings.value('xleading'))
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
        self.CB_xleading.setEnabled(False)
        self.PB_scans.setEnabled(False)
        self.SB_xlim0.setEnabled(False)
        self.SB_xlim1.setEnabled(False)
        self._timer.stop()

    def scanEnd(self):
        # resume timer, unlock all widgets
        self._timer.start()
        for key1 in self.sWidgets.keys():
            for key2 in self.sWidgets[key1].keys():
                if key2 != 'si':
                    self.sWidgets[key1][key2].setEnabled(True)
        for key1 in self.mWidgets.keys():
            for key2 in self.mWidgets[key1].keys():
                
                self.mWidgets[key1][key2].setEnabled(True)
        for stage in range(1,5):
            if stage not in self.activeStages:
                self._link_enable(stage, False)
                self.sWidgets[stage]['sethome'].setEnabled(False)
                self.sWidgets[stage]['linkedstage'].setEnabled(False)
        self.PB_quickFFT.setEnabled(True)
        self.CB_invert1.setEnabled(True)
        self.CB_invert2.setEnabled(True)
        self.CB_xleading.setEnabled(True)
        self.PB_scans.setEnabled(True)
        self.SB_xlim0.setEnabled(True)
        self.SB_xlim1.setEnabled(True)

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
            y = self.parent.y[1][:-1]
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

