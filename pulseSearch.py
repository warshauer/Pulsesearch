import os
import sys
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.qt_compat import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvas
import matplotlib as mpl
import numpy as np
from PyQt5 import QtCore, QtWidgets
from PyQt5 import uic
import appClasses as dd
from instrumentControl import esp301_GPIB, sr830, CONEX
import time
from scipy.fft import fft, fftfreq
from scanProgV4p0 import DLscanWindow

class pulsesearchWindow(QtWidgets.QMainWindow):
    """
    Main window for the Pulse Search application.

    This class handles the GUI, instrument connections, and data processing for the pulse search application.
    It integrates with PyQt5 for the GUI and matplotlib for plotting.

    Attributes:
        me (str): Identifier for the application.
        stageBoss (stageBoss): Manages stage controllers and their configurations.
        instrumentsConnected (bool): Indicates if instruments are connected.
        threadpool (QThreadPool): Thread pool for managing background tasks.
        settings (QSettings): Stores application settings.
        plot (PulsesearchCanvasXY): Custom canvas for plotting data.
        motionAllowed (bool): Indicates if motion is allowed for stages.
        addNext (bool): Indicates if the next command should be added to the queue.
        stageJustMoved (bool): Indicates if a stage has just moved.
        timeStageEnd (float): Timestamp of the last stage movement.
        timeConstants (list): List of time constants for lock-in amplifiers.
        quickFFT (quickFFTWindow): Window for quick FFT analysis.
        scanWindow (DLscanWindow): Window for scan operations.
        savePlotWindow (savePlotWindow): Window for saving plots.
        commandQueue (list): Queue of commands to execute.
        _sample_interval (int): Interval for the main runtime timer in milliseconds.
        _timer (QTimer): Timer for the main runtime loop.
    """

    def __init__(self, whoami = 'pulseSearch', version = 'v4.0', ESP_port = 1, lockin1_port = 8, lockin2_port = 7):
        """
        Initializes the Pulse Search main window.

        Args:
            whoami (str): Identifier for the application.
            version (str): Version of the application.
            ESP_port (int): Port number for the ESP stage controller.
            lockin1_port (int): Port number for the first lock-in amplifier.
            lockin2_port (int): Port number for the second lock-in amplifier.
        """
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

        self.plot = PulsesearchCanvasXY(self, xlabel = 'time (ps)', ylabel1 = 'lock-in 1', ylabel2 = 'lock-in 2', xlimits = [-1, 1])
        self.ui.GL_plot.addWidget(self.plot,0,0,1,1)

        self._move = False
        self._cmi = 0
        self._cmpn = 1
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
        
        # This section initializes various widgets, connects signals to slots, and sets up the GUI for the Pulse Search application.
        # It includes the following key functionalities:

        # 1. **Initialization of Scan and Plot Windows**:
        #    - `self.scanWindow` and `self.savePlotWindow` are initialized as instances of `DLscanWindow` and `savePlotWindow`, respectively.
        #    - These windows are used for scanning and saving plots.

        # 2. **Button Click Connections**:
        #    - Buttons such as `PB_quickFFT`, `PB_savePlot`, `PB_scans`, and `PB_connect` are connected to their respective functions.
        #    - For example, `PB_quickFFT` opens the Quick FFT window, and `PB_connect` connects to the instruments.

        # 3. **Widget Dictionaries for Lock-in Amplifiers**:
        #    - `self.mWidgets` is a dictionary that organizes widgets for two lock-in amplifiers (1 and 2).
        #    - Each lock-in amplifier has associated widgets for parameters like sensitivity, time constant, input configuration, and plotting options.
        #    - Signals from these widgets (e.g., state changes, value changes) are connected to corresponding methods for handling changes.


        # 5. **Unit Conversion and Inversion**:
        #    - `self.unitMod` is used to convert units (e.g., ps, mm, um) based on the selected option in `CB_xUnits`.
        #    - `self.invert` is a list that determines whether to invert the X-axis for lock-in amplifiers 1 and 2.

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

        # 4. **Widget Dictionaries for Stages**:
        #    - `self.sWidgets` is a dictionary that organizes widgets for controlling stages (e.g., ESP1, ESP2, ESP3).
        #    - Each stage has widgets for movement, linking, setting home positions, and updating frequencies.
        #    - These widgets are connected to methods for controlling stage behavior.

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

        # 6. **Timer for Runtime Function**:
        #    - `self._timer` is a `QTimer` that periodically calls the `runtime_functionV2` method.
        #    - This function handles the main runtime operations, such as updating data and executing queued commands.

        # 7. **Command Queue**:
        #    - `self.commandQueue` is a list that stores commands to be executed sequentially.
        #    - The `PB_clearQueue` button clears the command queue.

        # 8. **Plot Limits and Adjustments**:
        #    - Spin boxes (`SB_xlim0`, `SB_xlim1`, `SB_ylim01`, etc.) allow users to adjust the X and Y limits of the plot.
        #    - These spin boxes are connected to methods that update the plot limits dynamically.

        # 9. **Runtime Variables**:
        #    - Variables like `self.rtTime0`, `self.rtList0`, etc., are used to track runtime performance and speed checks.

        # 10. **Signal Connections**:
        #    - Various signals (e.g., `stateChanged`, `currentIndexChanged`, `valueChanged`) are connected to methods that handle changes in widget states or values.

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
        """
        Initializes the stage controller and assigns it to the stage boss.
        """
        # swap out the following line for whichever class connects to the stage controller:
        self.esp301 = esp301_GPIB(stagePort)
        # self.conex = CONEX(port = 3)
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
        """
        Initializes the stage interface by connecting buttons and setting up widgets for each stage.
        """
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

    def _connectInstruments(self):
        """
        Connects to the stage controller and lock-in amplifiers based on user input in the GUI.
        """
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
        """
        Clears the command queue (useful for when we get frustrated and click a button more times than we want).
        """
        self.commandQueue = []

    def _sensitivityChange(self, index, value):
        """
        Changes the sensitivity of the lock-in amplifier based on the selected value from the GUI.
        """
        self.lockins[index].set_sensitivity(value)
        self.mWidgets[index]['ylim0'].setValue(-self._sensitivityList[value])
        self.mWidgets[index]['ylim1'].setValue(self._sensitivityList[value])
        self.ylimit_change( index, 0, -self._sensitivityList[value])
        self.ylimit_change( index, 1, self._sensitivityList[value])

    def _timeconstantChange(self, index, value):
        """
        Changes the time constant of the lock-in amplifier based on the selected value from the GUI.
        """
        print(index, value)
        self.lockins[index].set_time_constant(value)
        self.timeConstants[index-1] = self._timeConstantList[value]

    def _inputconfigChange(self, index, value):
        """
        Changes the input configuration of the lock-in amplifier based on the selected value from the GUI.
        """
        self.lockins[index].set_input_config(value)

    def _xUnitChange(self):
        """
        Changes the unit of measurement for the X-axis based on the selected value from the GUI.
        """
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
        """
        Sets the link for the stage based on the selected value from the GUI.
        """
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
        """
        Returns the stage to its home position.
        Sets the plot 0 position as the home position of the leading stage if it is selected for homing.
        """
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
        """
        Appends the current measurements from the lock-in amplifiers and stage positions to the data arrays.
        """
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
        """
        Refreshes the data from the lock-in amplifiers in the GUI and updates the plot last data point marker.
        """
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
        """
        Updates the plot with the current data from the lock-in amplifiers and stage positions.
        """
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
        """
        Returns the values plotted at the moment, useful for quick saving of optimization data for adjusting and comparing FFTs for optimization.
        """
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
        """
        Main runtime function that is called periodically by the timer.
        It handles the execution of queued commands, updates measurement values, and refreshes data.
        This is the meat and potatoes of the program.
        """
        if self.instrumentsConnected:
            self._updateQueueLen() # hi, i'm warsh
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
        """
        Executes the first command in the command queue.
        If the queue is empty, it does nothing.
        """
        if len(self.commandQueue) < 1:
            pass
        else:
            funky = self.commandQueue.pop(0)
            funky()

    def _updateQueueLen(self):
        """
        Updates the length of the command queue displayed in the GUI.
        Just nice to know what we mightn be waiting for.
        """
        self.LE_queue.setText(str(len(self.commandQueue)))

    def _addFunctionToQueue(self, func, *args, **kwargs):
        """
        Adds a function to the command queue.
        This function is used to queue up commands for execution in the main runtime loop.
        This will pass the given function into the lambda factory to be executed when it is its turn in the queue.
        """
        self.commandQueue.append(self._lambMill(func, *args, **kwargs))
        print('add to queue: ', func)

    def _safetyCheckpoint(self, *stage_keys):
        """
        Probably the most important function in the program.
        This function makes sure that the stages are done moving, and that we have waiting longer than the time constant of the lock-in amplifiers before we append any data.
        This is used to manage all of our data acquisition and plotting.
        """
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

    def _lambMill(self, func, *args, **kwargs):
        """
        A lambda factory that creates a lambda function to execute the given function with the provided arguments and keyword arguments.
        This is used to create a callable function that can be added to the command queue."""
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

    def _storeSettings(self):
        """
        Stores the current settings of the application, including stage positions, lock-in amplifier settings, and other configurations.
        """
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
        """
        Recalls the settings stored in the application, including stage positions, lock-in amplifier settings, and other configurations.
        """
        try:
            self.SB_xlim0.setValue(float(self.settings.value('xlim0')))
            self.SB_xlim1.setValue(float(self.settings.value('xlim1')))
            stageSets = self.settings.value('stageSets')
            self.stageValueInit = {}
            for stage_key in list(stageSets.keys()):
                self.stageValueInit[stage_key] = stageSets[stage_key]['stageValues'].copy()
                self.sWidgets[stage_key]['home'].setText(format(stageSets[stage_key]['homeMem'], '.4f'))
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
        """
        Create a worker class that will run the function in a separate thread. 
        This helps the GUI remain responsive while the function is running.
        Pretty much just used to pawn off the plot update to a different thread.
        """
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
        """
        Start the scan process by locking the widgets and stopping the timer. 
        Allows the scans to run at maximum speed without interference from the GUI.
        """
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
        """
        End the scan process by unlocking the widgets and resuming the timer.
        Allows the GUI to be used again after the scan is complete.
        """
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
