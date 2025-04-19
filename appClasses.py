
from __future__ import annotations
from typing import *
import sys
import os
from matplotlib.backends.qt_compat import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvas
import matplotlib as mpl
import matplotlib.figure as mpl_fig
import matplotlib.animation as anim
import numpy as np
#from PyQt5.QtCore import Qt
from PyQt5 import QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime
import matplotlib.animation as anim
import time

# general live plot
# general logfileManager
# general instrument spoof
# variables/widget manager
# multiple instrument managing class

class instrumentSpoof():
    def __init__(self, *args, **kwargs):
        self.me = 'spoof'
        self.me_time = time.time()
        self.value = 150
        self.valT = 150
        self.valH = 50

    def query(self, *args, **kwargs):
        if len(args)<1:
            args = ['']
        if args[0][:5] == 'KRDG?':
            self.valT = self.valT - (np.random.random(1)[0] - .5)
            return self.valT
        elif args[0][:5] == 'HTR? ':
            self.valH = self.valH - (np.random.random(1)[0] - .5)
            return self.valH
        else:
            self.value = self.value - (np.random.random(1)[0] - .5)
            return self.value

class logfileManager():
    def __init__(self, parent, path = None, overwrite = False, downsample = 4):
        self.parent = parent
        self.path = path
        self.overwrite = overwrite
        self.safety_count = 0
        self.ds_count = 0
        self.downsample = downsample
        if self.path != None:
            self.open_logfile()

    def log_data(self, newdata):
        try:
            if self.ds_count > self.downsample:
                self.ds_count = 0
                line = ''
                for item in newdata:
                    line = line + str(item)[:10] + ' '
                line = line + '\n'
                self.logfile.write(line)
                self.safety_count += 1
                if self.safety_count > 10:
                    self.filerefresh()
                    self.safety_count = 0
            else:
                self.ds_count += 1
        except Exception as e:
            print(e)

    def open_logfile(self):
        self.safety_count = 0
        if os.path.exists(self.path) == True and self.overwrite == False:
            self.logfile = open(self.path, 'a')
        else: 
            self.logfile = open(self.path, 'w')
        self.logfile.write(str(datetime.now())+' start \n')
        self.logfile.write('time channelAtemp channelBtemp channelCtemp channelDtemp \n')
        print('log file opened')

    def close_logfile(self):
        try:
            close(self.logfile)
        except Exception as e:
            print(e)

    def filerefresh(self):
        self.logfile.close()
        self.logfile = open(self.path, 'a')

class plotCanvas(FigureCanvas):
    def __init__(self, parent, xlabel = '', ylabel = '', autolim = True , xlimits = [0, 20], ylimits = [0, 100], windowlength = 0, plot_dict = None, line_dict = None, last_point = False, log = False):
        super().__init__(mpl.figure.Figure())
        # plot_dict = {ax_key:{'ylabel':'', 'ylimits':[,]}, }
        # line_dict = {ax_key:{line_key:{kwargs for line}}}
        self.parent = parent
        self.autolim = autolim
        #self.patch.set_facecolor((255,255,255))

        self._axes = {}
        if plot_dict != None:
            self._ak = list(plot_dict.keys())
        elif line_dict != None:
            self._ak = list(line_dict.keys())
        else:
            self._ak = [0]
        if plot_dict == None:
            self._pd = {}
            for k in self._ak:
                self._pd[k] = {}
                self._pd[k]['ylabel'] = ylabel
                self._pd[k]['ylimits'] = ylimits
        else:
            self._pd = plot_dict
        if line_dict == None:
            self._ld = {}
            for k in self._ak:
                self._pd[k]['lk'] = [0]
                self._ld[k] = {}
                self._ld[k][0] = {}
        else:
            self._ld = line_dict
        self._last_point = last_point
        
        self._axes[self._ak[0]] = self.figure.subplots()
        self._axes[self._ak[0]].set_ylabel(self._pd[self._ak[0]]['ylabel'], fontsize=20)
        self._axes[self._ak[0]].set_xlabel(xlabel, fontsize=20)
        #self._axes[self._ak[0]].tick_params(axis='y', colors='tab:orange')
        self._axes[self._ak[0]].minorticks_on()
        self._axes[self._ak[0]].grid(which = 'major', color = 'yellow', linestyle = '--', linewidth = 0.5)
        self._axes[self._ak[0]].grid(which = 'minor', color = 'yellow', linestyle = '--', linewidth = 0.25, alpha = .5)
        self._axes[self._ak[0]].set_facecolor((0,0,0))
        if log == True:
                self._axes[self._ak[0]].set_yscale('log')
        self._xlimits = xlimits
        for i in range(1,len(self._ak)):
            self._axes[self._ak[i]] = self._axes[self._ak[0]].twinx()
            self._axes[self._ak[i]].spines.right.set_position(("axes", 1+.07*(i-1)))
            self._axes[self._ak[i]].tick_params(axis='y', labelsize = 7)
            self._axes[self._ak[i]].set_ylabel(self._pd[self._ak[i]]['ylabel'], fontsize=16)
            if log == True:
                self._axes[self._ak[i]].set_yscale('log')

        self._lines = {}
        self._lp = {}
        self._staticlines = {}
        for k in self._ak:
            self._lp[k] = {}
            self._lines[k] = {}
            self._staticlines[k] = {}
            for key in self._ld[k]:
                self._lines[k][key], = self._axes[k].plot([], [], **self._ld[k][key])
                if self._last_point:
                    self._lp[k][key], = self._axes[k].plot([], [], ms = 7, color = 'cyan',marker = 'D',ls = '')

        self._window_length = windowlength # maximum actually shown on the window, this we can add the ability to adjust to look further bag etc
        return
    
    def clear(self):
        for key in self._staticlines[1]:
            self._staticlines[1][key].set_data( [], [] )
        self._staticlines[1] = {}

    def update_plot(self, x, y):
        if type(y) == dict:
            # x is a list, y = {ax_key0:{line_key0:ydata, line_key1:ydata}, ...}
            self._update_canvas(x, y)
        else:
            y = {self._ak[0]:{list(self._lines[self.ax[0]].keys())[0]:y}}
            self._update_canvas(x, y)

    def add_static_line(self, x, y, name = 0, ax = None, **kwargs):
        # x is list, y is list, name is key for the line, ax is axis key, all kwargs go into .plot()
        # to delete a static line, just write over its name with x = [], y = []
        if ax == None:
            ax = self._ak[0]
        self._staticlines[ax][name], = self._axes[ax].plot(x, y, **kwargs)

    def set_ylimit(self, index, value, axis = None):
        if axis == None:
            self._pd[self._ak[0]]['ylimits'][index] = value
        else:
            self._pd[axis]['ylimits'][index] = value

    def set_xlimit(self, index, value):
        self._xlimits[index] = value

    def set_window_length(self, window_length):
        self._window_length = window_length

    def _limiter(self):
        if self.autolim:
            for ax in self._axes.keys():
                self._axes[ax].relim()
                self._axes[ax].autoscale_view()
        else:
            for ax in self._axes.keys():
                self._axes[ax].set_xlim(self._xlimits[0], self._xlimits[1])
                self._axes[ax].set_ylim(self._pd[ax]['ylimits'][0], self._pd[ax]['ylimits'][1])

    def _update_canvas(self, x, y):
        # x is a list, y = {ax_key0:{line_key0:ydata, line_key1:ydata}, ...}
        for ax in self._ak:
            for li in self._lines[ax].keys():
                if li in y[ax].keys():
                    self._lines[ax][li].set_data( x[-self._window_length:], y[ax][li][-self._window_length:] )
                    if self._last_point:
                        self._lp[ax][li].set_data( x[-1], y[ax][li][-1] )
                else:
                    self._lines[ax][li].set_data( [], [] )
                    if self._last_point:
                        self._lp[ax][li].set_data( [], [] )

        self._limiter()
        self.draw()
        return
    
    def _updateLastPoint(self, x, y):
        for ax in self._ak:
            for li in self._lines[ax].keys():
                if li in y[ax].keys():
                    if self._last_point:
                        self._lp[ax][li].set_data( x[-1], y[ax][li][-1] )

    def updateLastPoint(self, x, y):
        if type(y) == dict:
            # x is a list, y = {ax_key0:{line_key0:ydata, line_key1:ydata}, ...}
            self._updateLastPoint(x, y)
        else:
            y = {self._ak[0]:{list(self._lines[self.ax[0]].keys())[0]:y}}
            self._updateLastPoint(x, y)

class fastCanvas(FigureCanvas):
    def __init__(self, parent, xlabel = '', ylabel = '', autolim = True , xlimits = [0, 150], ylimits = [0, 300], windowlength = 0, plot_dict = None, line_dict = None, last_point = False):
        super().__init__(mpl.figure.Figure())
        self.parent = parent
        self.autolim = autolim

        self._axes = {}
        self._axes[1] = self.figure.subplots()
        self._axes[1].set_ylabel('lock-in 1', fontsize=20)
        self._axes[1].set_xlabel('time (ps)', fontsize=20)
        self._axes[1].minorticks_on()
        self._axes[1].grid(which = 'major', color = 'yellow', linestyle = '--', linewidth = 0.5)
        self._axes[1].grid(which = 'minor', color = 'yellow', linestyle = '--', linewidth = 0.25, alpha = .5)
        self._axes[1].set_facecolor((0,0,0))

        self._xlimits = xlimits
        self._ylimits = {1:plot_dict[1]['ylimits'], 2:plot_dict[2]['ylimits']}

        self._axes[2] = self._axes[1].twinx()
        self._axes[2].spines.right.set_position(("axes", 1+.07*(0-1)))
        self._axes[2].tick_params(axis='y', labelsize = 7)
        self._axes[2].set_ylabel('lock-in 2', fontsize=16)

        self._lines = {}
        self._lp = {}
        self._lines[1], = self._axes[1].plot([], [], **line_dict[1])
        self._lines[2], = self._axes[2].plot([], [], **line_dict[2])
        self._lp[1], = self._axes[1].plot([], [], ms = 7, color = 'c',marker = 'D',ls = '')
        self._lp[2], = self._axes[2].plot([], [], ms = 7, color = 'm',marker = 'D',ls = '')

        self._window_length = windowlength # maximum actually shown on the window, this we can add the ability to adjust to look further bag etc
        return

    def update_plot(self, x1, x2, y1, y2):
        self._update_canvas(x1, x2, y1, y2)

    def set_ylimit(self, index, value, axis = None):
        self._ylimits[axis][index] = value

    def set_xlimit(self, index, value):
        self._xlimits[index] = value

    def set_window_length(self, window_length):
        self._window_length = window_length

    def _limiter(self):
        if self.autolim:
            self._axes[1].relim()
            self._axes[1].autoscale_view()
            self._axes[2].relim()
            self._axes[2].autoscale_view()
        else:
            self._axes[1].set_xlim(self._xlimits[0], self._xlimits[1])
            self._axes[1].set_ylim(self._ylimits[1][0], self._ylimits[1][1])
            self._axes[2].set_xlim(self._xlimits[0], self._xlimits[1])
            self._axes[2].set_ylim(self._ylimits[2][0], self._ylimits[2][1])

    def _update_canvas(self, x1, x2, y1, y2):
        self._lines[1].set_data( x1[-self._window_length:], y1[-self._window_length:] )
        self._lines[2].set_data( x2[-self._window_length:], y2[-self._window_length:] )
        self._limiter()
        return
    
    def _updateLastPoint(self, x1 = [], x2 = [], y1 = [], y2 = []):
        self._lp[1].set_data( x1, y1 )
        self._lp[2].set_data( x2, y2 )
        self._limiter()
        self.draw()
        return

    def updateLastPoint(self, x1 = [], x2 = [], y1 = [], y2 = []):
        self._updateLastPoint(x1, x2, y1, y2)

class PulsesearchCanvas(FigureCanvas):
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

        self.line0, = self.ax0.plot([], [], color = 'w', linewidth = 1)
        self.line1, = self.ax1.plot([], [], color = 'tab:red', linewidth = 1)
        self.dot0, = self.ax0.plot([], [], ms = 7, color = 'c',marker = 'D',ls = '')
        self.dot1, = self.ax1.plot([], [], ms = 7, color = 'm',marker = 'D',ls = '')
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
        self.line0.set_data( x0, y0 )
        self.line1.set_data( x1, y1 )
        self.draw()
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

class plotCanvasDL(FigureCanvas):
    def __init__(self, parent, xlabel = '', ylabel = '', autolim = True , xlimits = [0, 150], ylimits = [0, 300], windowlength = 0, plot_dict = None, line_dict = None, last_point = False):
        super().__init__(mpl.figure.Figure())
        # plot_dict = {ax_key:{'ylabel':'', 'ylimits':[,]}, }
        # line_dict = {ax_key:{line_key:{kwargs for line}}}
        self.parent = parent
        self.autolim = autolim
        print('hm?')
        #self.patch.set_facecolor((255,255,255))

        self._axes = {}
        if plot_dict != None:
            self._ak = list(plot_dict.keys())
        elif line_dict != None:
            self._ak = list(line_dict.keys())
        else:
            self._ak = [0]
        if plot_dict == None:
            self._pd = {}
            for k in self._ak:
                self._pd[k] = {}
                self._pd[k]['ylabel'] = ylabel
                self._pd[k]['ylimits'] = ylimits
        else:
            self._pd = plot_dict
        if line_dict == None:
            self._ld = {}
            for k in self._ak:
                self._pd[k]['lk'] = [0]
                self._ld[k] = {}
                self._ld[k][0] = {}
        else:
            self._ld = line_dict
        self._last_point = last_point
        
        self._axes[self._ak[0]] = self.figure.subplots()
        self._axes[self._ak[0]].set_ylabel(self._pd[self._ak[0]]['ylabel'], fontsize=20)
        self._axes[self._ak[0]].set_xlabel(xlabel, fontsize=20)
        #self._axes[self._ak[0]].tick_params(axis='y', colors='tab:orange')
        self._axes[self._ak[0]].grid()
        self._axes[self._ak[0]].set_facecolor((0,0,0))
        self._xlimits = xlimits
        for i in range(1,len(self._ak)):
            self._axes[self._ak[i]] = self._axes[self._ak[0]].twinx()
            self._axes[self._ak[i]].spines.right.set_position(("axes", 1+.07*(i-1)))
            self._axes[self._ak[i]].tick_params(axis='y', labelsize = 7)
            self._axes[self._ak[i]].set_ylabel(self._pd[self._ak[i]]['ylabel'], fontsize=16)

        self._lines = {}
        self._lp = {}
        self._staticlines = {}
        for k in self._ak:
            self._lp[k] = {}
            self._lines[k] = {}
            self._staticlines[k] = {}
            for key in self._ld[k]:
                self._lines[k][key], = self._axes[k].plot([], [], **self._ld[k][key])
                if self._last_point:
                    self._lp[k][key], = self._axes[k].plot([], [], ms = 5,color = 'cyan',marker = 'D',ls = '')

        self._window_length = windowlength # maximum actually shown on the window, this we can add the ability to adjust to look further bag etc
        return
    
    def update_plot(self, x, y):
        if type(y) == dict:
            # x is a list, y = {ax_key0:{line_key0:ydata, line_key1:ydata}, ...}
            self._update_canvas(x, y)
        else:
            y = {self._ak[0]:{list(self._lines[self.ax[0]].keys())[0]:y}}
            self._update_canvas(x, y)

    def add_static_line(self, x, y, name = 0, ax = None, **kwargs):
        # x is list, y is list, name is key for the line, ax is axis key, all kwargs go into .plot()
        # to delete a static line, just write over its name with x = [], y = []
        if ax == None:
            ax = self._ak[0]
        self._staticlines[ax][name], = self._axes[ax].plot(x, y, **kwargs)

    def set_ylimit(self, index, value, axis = None):
        if axis == None:
            self._pd[self._ak[0]]['ylimits'][index] = value
        else:
            self._pd[axis]['ylimits'][index] = value

    def set_xlimit(self, index, value):
        self._xlimits[index] = value

    def set_window_length(self, window_length):
        self._window_length = window_length

    def _limiter(self):
        if self.autolim:
            for ax in self._axes.keys():
                self._axes[ax].relim()
                self._axes[ax].autoscale_view()
        else:
            for ax in self._axes.keys():
                self._axes[ax].set_xlim(self._xlimits[0], self._xlimits[1])
                self._axes[ax].set_ylim(self._pd[ax]['ylimits'][0], self._pd[ax]['ylimits'][1])

    def _update_canvas(self, x, y):
        # x is a list, y = {ax_key0:{line_key0:ydata, line_key1:ydata}, ...}
        for ax in self._ak:
            for li in self._lines[ax].keys():
                if li in y[ax].keys():
                    self._lines[ax][li].set_data( x[-self._window_length:], y[ax][li][-self._window_length:] )
                    if self._last_point:
                        self._lp[ax][li].set_data( x[-1], y[ax][li][-1] )
                else:
                    self._lines[ax][li].set_data( [], [] )
                    if self._last_point:
                        self._lp[ax][li].set_data( [], [] )

        self._limiter()
        self.draw()
        return

    def _updateCanvas(self, x, y):
        # x is a list, y = {ax_key0:{line_key0:ydata, line_key1:ydata}, ...}
        for ax in self._ak:
            for li in self._lines[ax].keys():
                if li in y[ax].keys():
                    self._lines[ax][li].set_data( x[-self._window_length:], y[ax][li][-self._window_length:] )
                    if self._last_point:
                        self._lp[ax][li].set_data( x[-1], y[ax][li][-1] )
                else:
                    self._lines[ax][li].set_data( [], [] )
                    if self._last_point:
                        self._lp[ax][li].set_data( [], [] )
        self._limiter()
        return
    
    def updateCanvas(self, x, y):
        if type(y) == dict:
            # x is a list, y = {ax_key0:{line_key0:ydata, line_key1:ydata}, ...}
            self._updateCanvas(x, y)
        else:
            y = {self._ak[0]:{list(self._lines[self.ax[0]].keys())[0]:y}}
            self._updateCanvas(x, y)

    def _drawPlot(self):
        self.draw()