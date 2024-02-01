import data_analysis_v2 as da
import numpy as np
import os
import glob
from numpy.core.numerictypes import find_common_type
from scipy.fft import fft, fftfreq
import pandas as pd
import random
import matplotlib.colors as mcolors
from scipy.optimize import root
import pickle
import shutil
import json

# -------------------------------------------------------------------------------------------------------------
# QoL functions

def loadingbar(tasknum,numtasks, text):
    space=" |"
    for i in range(numtasks):
        if i<tasknum:
            space=space+chr(9619)
        else:
            space=space+' '
    space=space+"| "+str(tasknum)+'/'+str(numtasks)+'  '
    print(space+text+'    ', end='\r')

def convert(data, convert_from, convert_to = None):
    c=299.792
    hc=1239.841
    if convert_from == 'ps':
        ps = data
    elif convert_from == 'THz':
        ps = 1/data
    elif convert_from == 'meV':
        ps = hc/data/c
    elif convert_from == '1/cm':
        ps = 1/c/data*10000
    elif convert_from == 'um':
        ps = data/c
    else:
        print('unknown unit')
        ps = 1
    converted = {}
    converted['ps'] = ps
    converted['THz'] = 1 / ps
    converted['um'] = c * ps
    converted['meV'] = hc / (c * ps)
    converted['1/cm'] = 1 / ps / c * 10000
    if convert_to == None:
        return converted
    else:
        return converted[convert_to]

def correlated_sort(list1, list2):
    list1, list2 = zip(*sorted(zip(list1, list2), key=lambda x: x[1]))
    return list(list1), list(list2)

def load_DL(directory, cheapo = False):
    print(directory)
    delays_str = os.listdir(directory)
    print(delays_str)
    delays_flt = []
    for d in delays_str:
        print(d)
        print(type(d))
        print(float(d))
        delays_flt.append(float(d))
    delays_str, delays_flt = correlated_sort(delays_str, delays_flt)
    d = len(delays_str)
    filelabels = {}
    first_file = True
    heck = True
    ok = 0
    for delay in delays_str:
        path_folder = directory+'\\'+delay
        first_file_in_folder = True
        i = 0
        for filename in glob.glob(os.path.join(path_folder, '*.dat')):
            loadarray = np.loadtxt(filename, dtype=float)
            if first_file_in_folder:
                data_E_nt = np.array([loadarray[:,1]])
                data_dE_nt = np.array([loadarray[:,2]])
                if first_file:
                    time = loadarray[:,0]
                    first_file = False
                first_file_in_folder = False
            else:
                data_E_nt = np.concatenate((data_E_nt, np.array([loadarray[:,1]])), axis=0)
                data_dE_nt = np.concatenate((data_dE_nt, np.array([loadarray[:,2]])), axis=0)
            filelabels[delay+'_'+str(i)]=filename
            i+=1
        if heck:
            data_E_dnt = np.array([data_E_nt])
            data_dE_dnt = np.array([data_dE_nt])
            print('number of scans: ',len(data_E_dnt[0,:,:]))
            heck=False
        else:
            if len(data_E_dnt[0,:,0]) < len(data_E_nt[:,0]):
                data_E_dnt = np.concatenate((data_E_dnt, np.array([data_E_nt[:len(data_E_dnt[0,:,0]),:]])), axis = 0)
                data_dE_dnt = np.concatenate((data_dE_dnt, np.array([data_dE_nt[:len(data_E_dnt[0,:,0]),:]])), axis = 0)
                #print('add less')
            else:
                while len(data_E_dnt[0,:,0]) > len(data_E_nt[:,0]):
                    data_E_dnt = np.delete(data_E_dnt, -1, axis = 1)
                    data_dE_dnt = np.delete(data_dE_dnt, -1, axis = 1)
                    #print('trim that bad boy')
                data_E_dnt = np.concatenate((data_E_dnt, np.array([data_E_nt])), axis = 0)
                data_dE_dnt = np.concatenate((data_dE_dnt, np.array([data_dE_nt])), axis = 0)
    return time, delays_flt, data_E_dnt, data_dE_dnt

def loadNewDL(directory, cheapo = False):
    print(directory)
    delays_str = os.listdir(directory)
    print(delays_str)
    delays_flt = []
    for d in delays_str:
        delays_flt.append(float(d))
    delays_str, delays_flt = correlated_sort(delays_str, delays_flt)
    d = len(delays_str)
    filelabels = {}
    first_file = True
    heck = True
    dataPlaceE = []
    dataPlacedE = []
    dataPlaceNames = []
    ok = 0
    for delay in delays_str:
        path_folder = directory+'\\'+delay
        print( delay, len(os.listdir(path_folder)) )
        first_file_in_folder = True
        i = 0
        filenames = []
        for filename in glob.glob(os.path.join(path_folder, '*.dat')):
            loadarray = np.loadtxt(filename, dtype=float)
            #print(loadarray.shape)
            if loadarray.shape[1] < 3:
                loadarray = np.concatenate((loadarray, np.zeros((loadarray.shape[0], 1))), axis = 1)
                print('fixed')
            if first_file_in_folder:
                print(loadarray.shape)
                data_E_nt = np.array([loadarray[:,1]])
                data_dE_nt = np.array([loadarray[:,2]])
                if first_file:
                    time = loadarray[:,0]
                    first_file = False
                first_file_in_folder = False
                filenames.append(filename)
                filelabels[delay+'_'+str(i)]=filename
                i+=1
            else:
                try:
                    if len(loadarray[:,1]) == len(data_E_nt[0]):
                        data_E_nt = np.concatenate((data_E_nt, np.array([loadarray[:,1]])), axis=0)
                        data_dE_nt = np.concatenate((data_dE_nt, np.array([loadarray[:,2]])), axis=0)
                        filenames.append(filename)
                        filelabels[delay+'_'+str(i)]=filename
                        i+=1
                    else:
                        pass
                except:
                    print(filename)
        dataPlaceNames.append(filenames)
        if cheapo:
            dataPlaceE.append(data_E_nt)
            dataPlacedE.append(data_dE_nt)
        else:
            if heck:
                data_E_dnt = np.array([data_E_nt])
                data_dE_dnt = np.array([data_dE_nt])
                print('number of scans: ',len(data_E_dnt[0,:,:]))
                heck=False
            else:
                if len(data_E_dnt[0,:,0]) < len(data_E_nt[:,0]):
                    data_E_dnt = np.concatenate((data_E_dnt, np.array([data_E_nt[:len(data_E_dnt[0,:,0]),:]])), axis = 0)
                    data_dE_dnt = np.concatenate((data_dE_dnt, np.array([data_dE_nt[:len(data_E_dnt[0,:,0]),:]])), axis = 0)
                    #print('add less')
                else:
                    while len(data_E_dnt[0,:,0]) > len(data_E_nt[:,0]):
                        data_E_dnt = np.delete(data_E_dnt, -1, axis = 1)
                        data_dE_dnt = np.delete(data_dE_dnt, -1, axis = 1)
                        #print('trim that bad boy')
                    data_E_dnt = np.concatenate((data_E_dnt, np.array([data_E_nt])), axis = 0)
                    data_dE_dnt = np.concatenate((data_dE_dnt, np.array([data_dE_nt])), axis = 0)
    # find most scans at a delay
    # for each delay, randomly select scans to duplicate until sane number of scans as most
    if cheapo:
        most = 0
        for item in dataPlaceE:
            if len(item[:,0]) > most:
                most = len(item[:,0])
        for i in range(len(dataPlaceE)):
            while len(dataPlaceE[i][:,0]) < most:
                j = np.random.randint(0, len(dataPlaceE[i][:,0]))
                dataPlaceE[i] = np.concatenate((dataPlaceE[i], np.array([dataPlaceE[i][j,:]])), axis=0)
                dataPlacedE[i] = np.concatenate((dataPlacedE[i], np.array([dataPlacedE[i][j,:]])), axis=0)
                filenames = dataPlaceNames[i]
                filenames.append(dataPlaceNames[i][j])
                dataPlaceNames[i].append(filenames)
        data_E_dnt = np.array([dataPlaceE[0]])
        data_dE_dnt = np.array([dataPlacedE[0]])
        print('number of scans: ',len(data_E_dnt[0,:,:]))
        for i in range(1, len(dataPlaceE)):
            data_E_dnt = np.concatenate((data_E_dnt, np.array([dataPlaceE[i]])), axis = 0)
            data_dE_dnt = np.concatenate((data_dE_dnt, np.array([dataPlacedE[i]])), axis = 0)
    return time, delays_flt, data_E_dnt, data_dE_dnt, dataPlaceNames

# missing: def load_SL
# missing: def load_CalibrationScans/calc this stuff idk how we want to feed this in tbh
# missing: special rounder

# -------------------------------------------------------------------------------------------------------------
# simple calculation functions, put in the requested, get out what you expect <3

def FFT(x, y):
    N = len(x)
    T = x[2] - x[1]
    yf = np.conj(fft(y))
    xf = fftfreq(N, T)[:N//2]
    return xf, 2.0/N * yf[0:N//2]

def n_from_R(Refl, phase):
    R = Refl
    Ph = phase
    n = (1 - R)/(1 + R - 2*np.sqrt(R)*np.cos(Ph))
    k = (2*np.sqrt(R)*np.sin(Ph))/(1 + R - 2*np.sqrt(R)*np.cos(Ph))
    complex_N = n + k*1j
    return complex_N

def n_from_r(r, n1 = 1.0, pol = 'p'):
    # only for normal incidence, lets add for not normal incidence later
    if pol == 's':
        n = n1*((1 - r)/(1 + r))
    else:
        n = n1*((-1 - r)/(-1 + r))
    return n

def n_from_sig(freq, sig, epsinf):
    n = np.sqrt((sig/freq)*1.8j + epsinf)
    return n

def reflectivity(n2, n1 = 1.0, dEoE = 0, pol = 'p'):
    # only for normal incidence, lets add for not normal incidence later
    if pol == 's':
        requ = (n1 - n2)/(n1 + n2)
    else:
        requ = -(n1 - n2)/(n1 + n2)
    return (dEoE + 1)*requ

def sig(freq, n, epsinf):
    return freq*(n*n - epsinf)/1.8j

def dsig_TFA(dEoE, freq, n_equ, d, z0):
    dsig_TFA = (1/(z0*d))*( (dEoE*(n_equ*n_equ - 1)) / (dEoE*(1 - np.sqrt(n_equ*n_equ)) + 2) )
    return dsig_TFA

def n_SEL(r_measured, freq, n_equ, d):
    def single_excited_layer_r(n2, r, freq, n3, d, n1 = 1.0, pol = 'p' ):
        # only for normal incidence, lets add for not normal incidence later
        # currently set up for freq in THz and d in cm
        if pol == 's':
            pm = 1
        else:
            pm = -1
        leftside = r
        lildelta = 2*np.pi*d*n2*freq/.0299
        exp_portion = np.exp(2*1j*lildelta)
        nominator = pm*((n1 - n2)/(n1 + n2)) + pm*((n2 - n3)/(n2 + n3))*exp_portion
        denominator = 1 + pm*((n1 - n2)/(n1 + n2))*pm*((n2 - n3)/(n2 + n3))*exp_portion
        rightside = nominator/denominator
        return rightside - leftside
    def NSolve(function, initial_guess):
        return root(ns_calc, x0=[np.real(initial_guess), np.imag(initial_guess)], args=(function))
    def ns_calc(xs, function):
        x = complex(*xs)
        err = function(x)
        return [err.real, err.imag]
    def function_to_solve(function, **kwargs):
        return lambda n:function(n, **kwargs)
    f2s = map(lambda r, freq, n3:function_to_solve(single_excited_layer_r, r = r, freq = freq, n3 = n3, d = d), r_measured, freq, n_equ)
    solx = np.array(list(map(lambda function, initial_guess: complex(*NSolve(function, initial_guess)['x']), f2s, n_equ )))
    return solx

def roundMan(self, ok, fac, ooooh):
        if fac>0:
            ok2=[]
            ok2.append((ok[0]*ooooh+ok[0+1])/(ooooh+1))
            for i in range(fac,len(ok)-fac):
                ok2.append((sum(ok[i-fac:i+fac+1])+(ooooh-1)*ok[i])/(ooooh+2))
                #print(ok[i-fac:i+fac+1])
            ok2.append((ok[len(ok)-1]*ooooh+ok[len(ok)-2])/(ooooh+1))
        else:
            ok2=[]
            ok2=ok
        return np.array(ok2)

def convolverV1(array, i0 = 0, i1 = 1, j0 = 0, j1 = 1, k0 = 0, k1 = 1, mode = [0,1,2]):
    kernels = []
    ki = np.concatenate((np.power(np.arange(i0 + 1), i1), np.flip(np.power(np.arange(i0 + 1), i1))[1:]), axis = 0) + (2/(1 + i1))
    kernels.append(ki/sum(ki))
    kj = np.concatenate((np.power(np.arange(j0 + 1), j1), np.flip(np.power(np.arange(j0 + 1), j1))[1:]), axis = 0) + (2/(1 + j1))
    kernels.append(kj/sum(kj))
    kk = np.concatenate((np.power(np.arange(k0 + 1), k1), np.flip(np.power(np.arange(k0 + 1), k1))[1:]), axis = 0) + (2/(1 + k1))
    kernels.append(kk/sum(kk))
    for axis in mode:
        array = np.swapaxes(array, 2, axis)
        for i in range(array.shape[0]):
            for j in range(array.shape[1]):
                array[i,j] = np.convolve(array[i,j], kernels[axis], mode = 'same')
        array = np.swapaxes(array, 2, axis)
    return array

def convolver(array, i0 = 0, i1 = 1, j0 = 0, j1 = 1, k0 = 0, k1 = 1, mode = [0,1,2]):
    i0 = int(i0); i1 = int(i1); j0 = int(j0); j1 = int(j1); k0 = int(k0); k1 = int(k1)
    kernels = []
    ki = np.concatenate((np.power(np.arange(i0 + 1), i1), np.flip(np.power(np.arange(i0 + 1), i1))[1:]), axis = 0) + (2/(1 + i1))
    kernels.append(ki/sum(ki))
    kj = np.concatenate((np.power(np.arange(j0 + 1), j1), np.flip(np.power(np.arange(j0 + 1), j1))[1:]), axis = 0) + (2/(1 + j1))
    kernels.append(kj/sum(kj))
    kk = np.concatenate((np.power(np.arange(k0 + 1), k1), np.flip(np.power(np.arange(k0 + 1), k1))[1:]), axis = 0) + (2/(1 + k1))
    kernels.append(kk/sum(kk))
    if i0 == 0 :
        iRet = slice(0, None)
    else:
        array = np.swapaxes(array, 0, 0)
        array = np.concatenate(( np.full(array[slice(0, i0),:,:].shape, np.average(array[slice(0, i0+1),:,:], axis = 0)), array, 
                                np.full(array[slice(-i0, None),:,:].shape, np.average(array[slice(-i0-1, None),:,:], axis = 0)) ), axis = 0)
        array = np.swapaxes(array, 0, 0)
        iRet = slice(i0, -i0)
    if j0 == 0 :
        jRet = slice(0, None)
    else:
        array = np.swapaxes(array, 0, 1)
        array = np.concatenate(( np.full(array[slice(0, j0),:,:].shape, np.average(array[slice(0, j0+1),:,:], axis = 0)), array, 
                                np.full(array[slice(-j0, None),:,:].shape, np.average(array[slice(-j0-1, None),:,:], axis = 0)) ), axis = 0)
        array = np.swapaxes(array, 0, 1)
        jRet = slice(j0, -j0)
    if k0 == 0 :
        kRet = slice(0, None)
    else:
        array = np.swapaxes(array, 0, 2)
        array = np.concatenate(( np.full(array[slice(0, k0),:,:].shape, np.average(array[slice(0, k0+1),:,:], axis = 0)), array, 
                                np.full(array[slice(-k0, None),:,:].shape, np.average(array[slice(-k0-1, None),:,:], axis = 0)) ), axis = 0)
        array = np.swapaxes(array, 0, 2)
        kRet = slice(k0, -k0)
    for ax in mode:
        array = np.apply_along_axis(lambda a : np.convolve(a, kernels[ax], mode = 'same'), axis = ax, arr = array)
    array = array[iRet, jRet, kRet]
    return array

def grabo(array, i = None, j = None, k = None, component = None, avgAxes = None, convolve = False, convolveBefore = True, convolveKwargs = None):
    # avgAxes given as list
    # convolve = True/False, convolveBefore = True/False, convolveKwargs = {i0':i0, 'i1':i1, 'j0':... 'k1':k1, 'mode':[0,1,2] (order axes convolve)}
    ret = array.copy()
    while len(ret.shape) < 3:
        ret = np.expand_dims(ret, axis = 0)
    if len(ret.shape) > 1:
        if i == None:
            i = slice(0, None)
        elif type(i) == int:
            if i >= ret.shape[0]:
                i = ret.shape[0] - 1
            i = slice(i, i+1)
        if j == None:
            j = slice(0, None)
        elif type(j) == int:
            if j >= ret.shape[1]:
                j = ret.shape[1] - 1
            j = slice(j, j+1)
        if k == None:
            k = slice(0, None)
        elif type(k) == int:
            if k >= ret.shape[2]:
                k = ret.shape[2] - 1
            i = slice(k, k+1)
        slices = [i,j,k]
        if avgAxes != None:
            avgAxes = list(avgAxes)
            for avgAxis in avgAxes:
                ret = np.swapaxes(ret, 0, avgAxis)
                ret = np.array([np.average(ret[slices[avgAxis]], axis = 0)])
                ret = np.swapaxes(ret, 0, avgAxis)
                slices[avgAxis] = slice(0,1)
        if component == 'abs':
            ret =  np.abs(ret)
        elif component == 'real':
            ret =  np.real(ret)
        elif component == 'imag':
            ret =  np.imag(ret)
        if convolve == True and convolveKwargs != None:
            if convolveBefore:
                ret = convolver(ret, **convolveKwargs)[tuple(slices)]
            else:
                ret = convolver(ret[tuple(slices)], **convolveKwargs)
        else:
            ret = ret[tuple(slices)]
    return ret
# -------------------------------------------------------------------------------------------------------------
# dataContainer - calculating and accessing data sets from measurements, equContainer - calculating and generating equilibrium spectra for sampling

# data
class dataContainer():
    # (self, edc = None, temp = 295, whoami = 'dc_1', raw_directory = None, pickle_path = None, cv = 1, unitadj = 1, sp = 0, penetration_depth = 5.3*(10**(-6)), nearest = 0, fit = True, autocalc = True):
    def __init__(self, edc = None, temp = 295, whoami = None, raw_directory = None, pickle_path = None, cv = 1, unitadj = 1, sp = 0, penetration_depth = 5.3*(10**(-6)), nearest = 0, fit = 'fit', z0 = 377, epsinf = 4.5, autocalc = True, split = 0, cheapo = False, date = None, detection = None, material = None, notes = None, updateThis = None, **kwargs):
        if pickle_path != None and os.path.exists(pickle_path) == True:
            self.load_pickle(pickle_path)
            if whoami != None:
                self.me = whoami
        else:
            if whoami != None:
                self.me = whoami
            else:
                self.me = 'dc'
            self.td = self.qts(self, 'timedomain')
            self.fd = self.qts(self, 'freqdomain')
            self.rawtime = self.qts(self, 'rawtime')
            # for load
            self.cheapo = cheapo
            self._calcVals = {}
            self._calcVals['sp'] = sp
            self._calcVals['cv'] = cv
            self._calcVals['unitadj'] = unitadj
            # for calculation
            self._calcVals['penetration_depth'] = penetration_depth
            self._calcVals['z0'] = z0
            self._calcVals['epsinf'] = epsinf
            # for sampling edc
            self._calcVals['edc'] = edc
            self._calcVals['nearest'] = nearest
            self._calcVals['fit'] = fit
            self._calcVals['split'] = split
            self._calcVals['temp'] = temp
            
            self.waw = 100
            self.comments = {'date':date, 'detection':detection, 'material':material, 'notes':notes}

            self.pickle_path = pickle_path
            self.raw_directory = raw_directory
            self.load_raw() # load raw data; print('raw load')
            self.sample_equ() # sample edc
            if autocalc:
                self.calculate_bulk()
                self.calculate_TF()
                self.calculate_SEL(updateThis = updateThis)
    
    class qts():
        def __init__(self, parent, whoami = 'me'):
            self.me = whoami
            self.parent = parent
            self.info = {}
            self.data = {}
            self.help = 'on initialize: take parent (dataContainer), whoami (keyindicator), has attributes me, parent, into, data, help. Treating as dictionary gives the qts in numpy form from the dictionary, example: instance["E"] is the same as instance.data["E"], info is another dict with info for each qt. functions are add_qt(whoami, array, info, **kwargs), array is the dnt array for qt, info and kwargs go into info, whoami becomes the keyword'

        # get item will give values on r,c = delay,time with each element the average over all scans, returnning 2D array
        def __getitem__(self, name):
            ret = self.data[name].copy()
            while len(ret.shape) < 3:
                ret = np.expand_dims(ret, axis = 0)
            return ret
        
        # calling item will give values on delay,scannum,time, returning 3D array
        def __call__(self, name, **kwargs):
            return self.grab(name, **kwargs)

        def grab(self, name, d = None, n = None, x = None, **kwargs):
            # avgAxes given as list
            # convolve = True/False, convolveBefore = True/False, convolveKwargs = {i0':i0, 'i1':i1, 'j0':... 'k1':k1, 'mode':[0,1,2] (order axes convolve)}
            i = d
            j = n
            k = x
            array = self.data[name].copy()
            return grabo(array, i = i, j = j, k = k, **kwargs)

        def set_x(self, x):
            self.x = x

        def add_qt(self, whoami, array, info, **kwargs):
            self.data[whoami] = array
            self.info[whoami] = {**{'me':whoami}, **info, **kwargs}

    # missing: recalculate with different part
    # missing: probably a lot of other operations idk yet

    # - - methods to calculate off the rip - -

    def sample_equ(self):
        arr, ctct = self._calcVals['edc'](temp = self._calcVals['temp'], freq = np.squeeze(self.fd['freq_THz']), qt = 'n_equ', fit = self._calcVals['fit'], nearest = self._calcVals['nearest'], info = True, epsinf = self._calcVals['epsinf'], split = self._calcVals['split'])
        print(self.me+';   calculating with '+str(ctct)+'K edc.')
        self.fd.add_qt(array = arr, whoami = 'n_equ', info = {'parent':self,'equ':self._calcVals['fit']})
        self.fd.add_qt(array = self._calcVals['edc'](temp = self._calcVals['temp'], freq = np.squeeze(self.fd['freq_THz']), qt = 'r_equ', fit = self._calcVals['fit'], nearest = self._calcVals['nearest'], epsinf = self._calcVals['epsinf'], split = self._calcVals['split']), whoami = 'r_equ', info = {'parent':self,'equ':self._calcVals['fit']})
        self.fd.add_qt(array = self._calcVals['edc'](temp = self._calcVals['temp'], freq = np.squeeze(self.fd['freq_THz']), qt = 'sig_equ', fit = self._calcVals['fit'], nearest = self._calcVals['nearest'], epsinf = self._calcVals['epsinf'], split = self._calcVals['split']), whoami = 'sig_equ', info = {'parent':self,'equ':self._calcVals['fit']})

    def runcalc(self, function, dnt_dict, axis, *args, **kwargs):
        for key in dnt_dict:
            dnt_dict[key] = dnt_dict[key].swapaxes(-1,axis)
        shape = dnt_dict[key].shape
        ret_dnt = np.zeros(shape, dtype = complex)
        for i in range(shape[0]):
            for j in range(shape[1]):
                dpass = {}
                for key in dnt_dict:
                    dpass[key] = dnt_dict[key][i,j,:]
                ret_dnt[i,j] = function(*args, **{**kwargs, **dpass})
        return ret_dnt

    def statpad(self, time, data_E_dtn, data_dE_dtn, sp):
        data_E_dtn = data_E_dtn.swapaxes(1,2)
        data_dE_dtn = data_dE_dtn.swapaxes(1,2)
        dt = time[1] - time[0]
        n_ir = int(sp/dt)
        time = np.concatenate((np.linspace(-dt*n_ir, -dt, n_ir), time), axis = 0)
        d, t, n = data_E_dtn.shape
        zeropad = np.zeros((d, n_ir, n))
        data_E_dtn = np.concatenate((zeropad, data_E_dtn), axis = 1)
        data_dE_dtn = np.concatenate((zeropad, data_dE_dtn), axis = 1)
        data_E_dtn = data_E_dtn.swapaxes(1,2)
        data_dE_dtn = data_dE_dtn.swapaxes(1,2)
        return time, data_E_dtn, data_dE_dtn 

    def rawdata_basic_calcs(self, time_ps, data_Et_dnt, data_dEt_dnt, cv = 1, unitadj = 1, sp = 0):
        data_Et_dnt = data_Et_dnt*unitadj
        data_dEt_dnt = data_dEt_dnt*unitadj*cv
        time_ps, data_Et_dnt, data_dEt_dnt = self.statpad(time_ps, data_Et_dnt, data_dEt_dnt, sp)
        N_d, N_n, N_t = data_Et_dnt.shape
        data_Ef_dnt = np.zeros((N_d, N_n, int(N_t/2)), dtype = complex)
        data_dEf_dnt = np.zeros((N_d, N_n, int(N_t/2)), dtype = complex)
        for i in range(N_d):
            for j in range(N_n):
                freq_THz, data_Ef_dnt[i,j,:] = FFT(time_ps, data_Et_dnt[i,j,:])
                freq_THz, data_dEf_dnt[i,j,:] = FFT(time_ps, data_dEt_dnt[i,j,:])
        return time_ps, data_Et_dnt, data_dEt_dnt, freq_THz, data_Ef_dnt, data_dEf_dnt

    def calculate_bulk(self):
        self.fd.add_qt(array = self.runcalc(reflectivity, dnt_dict = {'dEoE':self.fd['dE/E']}, axis = 2, n2 = np.squeeze(self.fd['n_equ'])), whoami = 'r_bulk', info = {'parent':self})
        self.fd.add_qt(array = self.runcalc(n_from_r, dnt_dict = {'r':self.fd['r_bulk']}, axis = 2), whoami = 'n_bulk', info = {'parent':self})
        self.fd.add_qt(array = self.runcalc(sig, dnt_dict = {'n':self.fd['n_bulk']}, axis = 2, freq = self.fd['freq_THz'], epsinf = self._calcVals['epsinf']), whoami = 'sig_bulk', info = {'parent':self})
        self.fd.add_qt(array = self.runcalc(lambda sig_bulk, sig_equ : sig_bulk - sig_equ, dnt_dict = {'sig_bulk':self.fd['sig_bulk']}, axis = 2, sig_equ = np.squeeze(self.fd['sig_equ'])), whoami = 'dsig_bulk', info = {'parent':self}); print('bulk calc')

    def calculate_TF(self):
        self.fd.add_qt(array = self.runcalc(dsig_TFA, dnt_dict = {'dEoE':self.fd['dE/E']}, axis = 2, freq = np.squeeze(self.fd['freq_THz']), n_equ = np.squeeze(self.fd['n_equ']), d = self._calcVals['penetration_depth'], z0 = self._calcVals['z0']), whoami = 'dsig_TFA', info = {'parent':self})
        self.fd.add_qt(array = self.runcalc(lambda dsig_TFA, sig_equ : dsig_TFA + sig_equ, dnt_dict = {'dsig_TFA':self.fd['dsig_TFA']}, axis = 2, sig_equ = np.squeeze(self.fd['sig_equ'])), whoami = 'sig_TFA', info = {'parent':self})
        self.fd.add_qt(array = self.runcalc(n_from_sig, dnt_dict = {'sig':self.fd['sig_TFA']}, axis = 2, freq = np.squeeze(self.fd['freq_THz']), epsinf = self._calcVals['epsinf']), whoami = 'n_TFA', info = {'parent':self}); print('TF calc')
        
    def calculate_SEL(self, updateThis = None):
        try:
            arr = np.zeros(self.fd['r_bulk'].shape, dtype = complex)
        except:
            self.calculate_bulk()
            arr = np.zeros(self.fd['r_bulk'].shape, dtype = complex)
        tots = len(arr[:,0,0])*len(arr[0,:,0]); count = 0; lplp = 0
        print('SEL calculation [%d%%]\r'%lplp, end="")
        for i in range(len(arr[:,0,0])):
            ph = n_SEL(r_measured = np.squeeze(np.average(self.fd['r_bulk'][i,:,:], axis = 0)), freq = np.squeeze(self.fd['freq_THz']), n_equ = np.squeeze(self.fd['n_equ']), d = self._calcVals['penetration_depth'])
            for j in range(len(arr[0,:,0])):
                arr[i,j] = ph
                count += 1; lplp = int(count*100 / tots)
                print('SEL calculation [%d%%]\r'%lplp, end="")
                if updateThis != None:
                    try:
                        updateThis(lplp)
                    except Exception as e:
                        print(e)
        self.fd.add_qt(array = arr, whoami = 'n_SEL', info = {'parent':self})
        self.fd.add_qt(array = self.runcalc(sig, dnt_dict = {'n':self.fd['n_SEL']}, axis = 2, freq = np.squeeze(self.fd['freq_THz']), epsinf = self._calcVals['epsinf']), whoami = 'sig_SEL', info = {'parent':self})
        self.fd.add_qt(array = self.runcalc(lambda sig_SEL, sig_equ : sig_SEL - sig_equ, dnt_dict = {'sig_SEL':self.fd['sig_SEL']}, axis = 2, sig_equ = np.squeeze(self.fd['sig_equ'])), whoami = 'dsig_SEL', info = {'parent':self}); print('SEL calc')

    # - - methods to change data after initializing calculations - -

    def recalculate(self, updateThis = None):
        self.waw = 0
        self.calculate_basics() # recalculate basics
        self.waw = 10
        self.sample_equ() # sample edc
        self.waw = 20
        self.calculate_bulk()
        self.waw = 30
        self.calculate_TF()
        self.waw = 55
        self.calculate_SEL(updateThis = updateThis)
        self.waw = 100
        print('recalculate complete')
        
    def recalculate_equilibrium(self):
        self.sample_equ() # sample edc
        self.calculate_TF()
        self.calculate_bulk()
        self.calculate_SEL()
        
    def recalculate_transients(self):
        self.calculate_TF()
        self.calculate_bulk()
        self.calculate_SEL()

    def change_freq_units(self, unit = 'THz'):
        if type(unit) == str:
            self.fd.set_x(convert(self.fd['freq_THz'], convert_from = 'THz', convert_to = unit))
        else:
            self.fd.set_x(self.fd.x*unit)

    # - - methods for loading and saving the class - -

    def load_raw(self, sorted_type = 'DL'):
        if sorted_type == 'DL':
            time, delays_flt, data_Et_dnt, data_dEt_dnt, filenames_dn = loadNewDL(self.raw_directory, cheapo = self.cheapo)
        else:
            print('for fucks sake warsh, write the function before you try to use it')
        self.filenames = filenames_dn
        self.delays = delays_flt
        self.rawtime.set_x(time)
        self.rawtime.add_qt(array = time, whoami = 'time', info = {'parent':self})
        self.rawtime.add_qt(array = data_Et_dnt, whoami = 'E', info = {'parent':self})
        self.rawtime.add_qt(array = data_dEt_dnt, whoami = 'dE', info = {'parent':self})
        self.calculate_basics()

    def calculate_basics(self):
        time, data_Et_dnt, data_dEt_dnt, freq, data_Ef_dnt, data_dEf_dnt = self.rawdata_basic_calcs(np.squeeze(self.rawtime['time']), self.rawtime['E'], self.rawtime['dE'], self._calcVals['cv'], self._calcVals['unitadj'], self._calcVals['sp'])
        self.td.set_x(time)
        self.td.add_qt(array = time, whoami = 'time_ps', info = {'unit':'ps','parent':self})
        self.td.add_qt(array = data_Et_dnt, whoami = 'E', info = {'unit':'mV','parent':self})
        self.td.add_qt(array = data_dEt_dnt, whoami = 'dE', info = {'unit':'mV','parent':self})
        self.fd.set_x(freq)
        self.fd.add_qt(array = freq, whoami = 'freq_THz', info = {'unit':'THz','parent':self})
        self.fd.add_qt(array = data_Ef_dnt, whoami = 'E', info = {'parent':self})
        self.fd.add_qt(array = data_dEf_dnt, whoami = 'dE', info = {'parent':self})
        self.fd.add_qt(array = data_dEf_dnt/data_Ef_dnt, whoami = 'dE/E', info = {'parent':self})

    def load_pickle(self, pickle_path):
        with open(pickle_path, 'rb') as pkl_file:
            self.__dict__ = pickle.load(pkl_file)
    
    def save(self, pickle_path, overwrite = False):
        proc_bool = not(os.path.exists(pickle_path))
        if overwrite:
            proc_bool = True
        if proc_bool:
            with open(pickle_path, 'wb') as pkl_file:
                pickle.dump(self.__dict__, pkl_file, protocol=pickle.HIGHEST_PROTOCOL)
            self.pickle_path = pickle_path
        else:
            print('could not proceed, invalid pickle_path or file already exists')

    def get_usable_freq_range(self, nd_index = 0, factor = .1):
        normm5ps = np.abs(self.fd['E'][nd_index])/np.sum(np.abs(self.fd['E'][nd_index]))
        subfactor = normm5ps - factor*normm5ps.max()
        usablefreq = []
        for i in range(len(subfactor)):
            if subfactor[i]>0:
                usablefreq.append(self.fd['freq_THz'][i])
        return usablefreq

    def change_values_for_calculation(self, updateThis = None, **kwargs):
        for key in kwargs:
            self._calcVals[key] = kwargs[key]
        self.recalculate(updateThis = updateThis)

# equ
class equContainer():
    def __init__(self, material, whoami = 'ec_1', directory = None):
        self.me = whoami
        self.material = material
        if directory != None:
            self.load(directory)
            
    def __call__(self, temp, freq, qt = 'n_equ', fit = 'fit', nearest = 0, info = False, epsinf = 4.5, split = 0):
        # qt n_equ, R_equ, theta_equ, r_equ, sig_equ
        # takes temp as integer in Kelvin, freq as THz, qt = 'n_equ', fit = True by default, nearest = 0 by default
        # nearest = 0, takes nearest equilibrium temp set, nearest = -1 takes nearest set below given temp, 
        # nearest = 1 takes nearest set above given temp.
        # returns n_equ (complex) sampled at those frequencies as np.array
        if fit == 'fit':
            if nearest == 0:
                comtemp = self.temps_fit[np.abs(self.temps_fit - temp).argmin()]
            elif nearest > 0:
                comtemp = self.temps_fit[self.temps_fit > temp].min()
            else:
                comtemp = self.temps_fit[self.temps_fit < temp].max()
            if info:
                return self.calc_from_fit(comtemp, freq, qt, epsinf), comtemp
            else:
                return self.calc_from_fit(comtemp, freq, qt, epsinf)
        elif fit == 'raw':
            rawbits = self.equcalc_raw(epsinf = epsinf)
            if nearest == 0:
                comtemp = self.temps_raw[np.abs(self.temps_raw - temp).argmin()]
            elif nearest > 0:
                comtemp = self.temps_raw[self.temps_raw > temp].min()
            else:
                comtemp = self.temps_raw[self.temps_raw < temp].max()
            if info:
                return self.resample(rawbits[comtemp]['freq'], rawbits[comtemp][qt], freq), comtemp
            else:
                return self.resample(rawbits[comtemp]['freq'], rawbits[comtemp][qt], freq)
        else:
            if nearest == 0:
                comtempF = self.temps_fit[np.abs(self.temps_fit - temp).argmin()]
            elif nearest > 0:
                comtempF = self.temps_fit[self.temps_fit > temp].min()
            else:
                comtempF = self.temps_fit[self.temps_fit < temp].max()
            rawbits = self.equcalc_raw(epsinf = epsinf)
            if nearest == 0:
                comtempR = self.temps_raw[np.abs(self.temps_raw - temp).argmin()]
            elif nearest > 0:
                comtempR = self.temps_raw[self.temps_raw > temp].min()
            else:
                comtempR = self.temps_raw[self.temps_raw < temp].max()
            rfit = self.resample(rawbits[comtempF]['freq'], rawbits[comtempF][qt], freq)
            efit = self.calc_from_fit(comtempR, freq, qt, epsinf)
            if info:
                return np.concatenate((efit[:np.abs(freq - split).argmin()+1], rfit[np.abs(freq - split).argmin()+1:])), (comtempF+comtempR)/2
            else:
                return np.concatenate((efit[:np.abs(freq - split).argmin()+1],rfit[np.abs(freq - split).argmin()+1:]))

    def calc_from_fit(self, temp, freq, qt, epsinf):
        if qt == 'sig_equ':
            return self.sig_equ_dlfit(freq = freq, DLa = self.dldict[temp])
        elif qt == 'n_equ':
            return n_from_sig(freq = freq, sig = self.sig_equ_dlfit(freq = freq, DLa = self.dldict[temp]), epsinf = epsinf)
        elif qt == 'r_equ':
            return reflectivity(n2 = n_from_sig(freq = freq, sig = self.sig_equ_dlfit(freq = freq, DLa = self.dldict[temp]), epsinf = epsinf))
        else:
            return freq
        
    def equcalc_raw(self, epsinf):
        df = self.raw
        valdict = {}
        for key in df:
            valdict[key] = {}
            valdict[key]['freq'] = np.array(df[key]['freq'])
            valdict[key]['R_equ'] = np.array(df[key]['R'])
            valdict[key]['theta_equ'] = np.array(df[key]['theta'])
            valdict[key]['n_equ'] = n_from_R(valdict[key]['R_equ'], valdict[key]['theta_equ'])
            valdict[key]['r_equ'] = reflectivity(n2 = valdict[key]['n_equ'])
            valdict[key]['sig_equ'] = sig(freq = valdict[key]['freq'], n = valdict[key]['n_equ'], epsinf = epsinf)
        return valdict
    
    def load(self, directory):
        equil_dfs={}
        temperatures=os.listdir(directory)
        if os.path.exists(directory +'\\dl.json'):
            self.load_json(directory +'\\dl.json')
            temperatures.remove('dl.json')
        for ti in temperatures:
            tt = int(ti.replace('K',''))
            path_folder = directory+'\\'+ti
            for filename in glob.glob(os.path.join(path_folder, '*.dat')):
                dfE=pd.read_csv(filename, delimiter='\t',usecols=['Freq','Refl','Phase']).rename(columns={"Freq": "freq", "Refl": "R","Phase": "theta"})
                dfE_stack=dfE
                equil_dfs[tt]=dfE_stack
                equil_dfs[tt]['freq'] = equil_dfs[tt]['freq'].multiply(0.0299792)
        self.raw = equil_dfs
        self.temps_raw = []
        for key in self.raw:
            self.temps_raw.append(key)
        self.temps_raw = np.array(self.temps_raw)

    def resample(self, x0, y0, x):
        y = np.zeros(x.shape, dtype = complex)
        for i in range(len(x)):
            ld = np.abs(x[i] - x0)
            i1 = np.argpartition(ld, 1-1)[1-1]
            i2 = np.argpartition(ld, 2-1)[2-1]
            s = (y0[i2]-y0[i1]) / (x0[i2]-x0[i1])
            yi = y0[i1] - s*x0[i1]
            y[i] = s*x[i] + yi
        return y

    def sig_equ_dlfit(self, freq, DLa, randy = 4.75):
        freqcm = freq/0.0299792
        sig = ( DLa[0,1]*DLa[0,1]*DLa[0,2] ) / ( 4*3.1415*( 1 - 1j*freqcm*DLa[0,2] ) )
        for i in range(1,len(DLa[:,0])):
            sig = sig + ( DLa[i,1]*DLa[i,1]*freqcm ) / ( 4*3.1415*( freqcm/DLa[i,2] + 1j*( DLa[i,0]*DLa[i,0] - freqcm*freqcm ) ) )
        sig = sig/randy
        return sig

    def load_json(self, path):
        with open(path, 'rb') as json_file:
            ddict = json.load(json_file)
        self.temps_fit = []
        self.dldict = {}
        for key in ddict:
            self.temps_fit.append(float(key))
            self.dldict[float(key)] = np.array(ddict[key])
        self.temps_fit = np.array(self.temps_fit)
        #print(self.dldict)

def sort_DL_scans(path, destination, delayAndNum, overwrite = False):
    if type(delayAndNum) == list:
        listcompare = True
        givenDict = {}
        givenDelays = []
        for i in range(len(delayAndNum)):
            item = delayAndNum[i]
            givenDelays.append(item.split('_')[0])
            givenDict[item.split('_')[0]] = {'num':int(item.split('_')[1]),'before':delayAndNum[i-1].split('_')[0]}
        print(givenDict)
    else:
        num = int(delayAndNum)
        listcompare = False
    existingDirBool=os.path.isdir(destination+'\\0')
    seenDelays = []
    seenDn = []
    dic = {}
    if existingDirBool==True:
        print('full directory')
    if existingDirBool==False or overwrite == True:
        for filepath in glob.glob(os.path.join(path, '*.dat')):
            breakpath=filepath.split('\\')
            filename=breakpath[len(breakpath)-1]
            breakScan=filename.split('_')
            dn = int(breakScan[0].lstrip('0'))
            sn = int(breakScan[len(breakScan)-1].split('.')[0])
            breakDelay = filepath.replace(' ','').split('Delay')
            d = breakDelay[1].split('ps')[0].replace('p','.').replace('m','-')
            if d not in seenDelays:
                seenDelays.append(d)
                seenDn.append(dn)
                dic[d] = {}
                dic[d]['dn'] = dn
                dic[d]['SPORTMODE'] = {}
            dic[d]['SPORTMODE'][sn] = {'path':filepath,'name':filename}
        print(seenDelays,seenDn)
        d_ordered, dn_ordered = zip(*sorted(zip(seenDelays,seenDn), key=lambda x: x[1]))
        if listcompare == True:
            if 'PLEASE' == 'PLEASE':
                save1 = True
                for delay in d_ordered:
                    os.mkdir(destination+'\\'+delay)
                for i in range(len(d_ordered)):
                    delay = d_ordered[i]
                    for key in dic[delay]['SPORTMODE']:
                        if save1 == True:
                            shutil.copyfile(dic[delay]['SPORTMODE'][key]['path'], destination+'\\'+delay+'\\'+dic[delay]['SPORTMODE'][key]['name'])
                            save1 = False
                        if (key-1)%givenDict[delay]['num'] == 0:
                            shutil.copyfile(dic[delay]['SPORTMODE'][key]['path'], destination+'\\'+d_ordered[i-1]+'\\'+dic[delay]['SPORTMODE'][key]['name'])
                        else:
                            shutil.copyfile(dic[delay]['SPORTMODE'][key]['path'], destination+'\\'+delay+'\\'+dic[delay]['SPORTMODE'][key]['name'])
        else:
            print('oh jeez')
            save1 = True
            for delay in d_ordered:
                os.mkdir(destination+'\\'+delay)
            for i in range(len(d_ordered)):
                delay = d_ordered[i]
                for key in dic[delay]['SPORTMODE']:
                    if save1 == True:
                        shutil.copyfile(dic[delay]['SPORTMODE'][key]['path'], destination+'\\'+delay+'\\'+dic[delay]['SPORTMODE'][key]['name'])
                        save1 = False
                    if (key-1)%num == 0:
                        shutil.copyfile(dic[delay]['SPORTMODE'][key]['path'], destination+'\\'+d_ordered[i-1]+'\\'+dic[delay]['SPORTMODE'][key]['name'])
                    else:
                        shutil.copyfile(dic[delay]['SPORTMODE'][key]['path'], destination+'\\'+delay+'\\'+dic[delay]['SPORTMODE'][key]['name'])
        print('set sorted')

def sortNewScansV1(path, destination, overwrite = False, updateThis = None):
    existingDirBool = os.path.isdir(destination+'\\0')
    seenDelays = []
    if existingDirBool == True:
        print('full directory')
    if existingDirBool == False or overwrite == True:
        for filepath in glob.glob(os.path.join(path, '*.dat')):
            breakpath = filepath.split('\\')
            filename = breakpath[len(breakpath)-1]
            breakScan = filename.split('_(')[-1]
            breakScan = breakScan.split(')_')[0]
            breakScan = breakScan.split('_')
            delayString = breakScan[0]
            delayFloat = float(delayString)
            delayIndex = int(breakScan[1])
            scanNum = int(breakScan[3])
            roundNum = int(breakScan[2])
            if delayString not in seenDelays:
                seenDelays.append(delayString)
                os.mkdir(destination + '\\' + delayString)
            shutil.copyfile(filepath, destination + '\\' + delayString + '\\' + filename)
        print('set sorted')
        if updateThis != None:
            try:
                updateThis('sorted: ' + ' '.join(seenDelays))
            except Exception as e:
                print(e)
                
def sortNewScans(path, destination, overwrite = False, updateThis = None):
    proc = False
    if os.path.isdir(destination) == True:
        if len(os.listdir(destination)) > 0:
            if overwrite:
                os.rmdir(destination)
                if updateThis != None:
                    try:
                        updateThis('sortNewScans destination overwrite')
                    except Exception as e:
                        print(e)
                print('sortNewScans destination overwrite')
                os.mkdir(destination)
                proc = True
            else:
                if updateThis != None:
                    try:
                        updateThis('sortNewScans destination exists')
                    except Exception as e:
                        print(e)
                print('sortNewScans destination exists')
                proc = False
        else:
            proc = True
    else:
        os.mkdir(destination)
        proc = True
    if proc:
        seenDelays = []
        for filepath in glob.glob(os.path.join(path, '*.dat')):
            breakpath = filepath.split('\\')
            filename = breakpath[len(breakpath)-1]
            breakScan = filename.split('_(')[-1]
            breakScan = breakScan.split(')_')[0]
            breakScan = breakScan.split('_')
            delayString = breakScan[0]
            delayFloat = float(delayString)
            delayIndex = int(breakScan[1])
            scanNum = int(breakScan[3])
            roundNum = int(breakScan[2])
            if delayString not in seenDelays:
                seenDelays.append(delayString)
                os.mkdir(destination + '\\' + delayString)
            shutil.copyfile(filepath, destination + '\\' + delayString + '\\' + filename)
        print('set sorted')
        if updateThis != None:
            try:
                updateThis('sorted: ' + ' '.join(seenDelays))
            except Exception as e:
                print(e)
    else:
        print('did not proceed with sort')
        if updateThis != None:
            try:
                updateThis('did not proceed with sort')
            except Exception as e:
                print(e)
        
def fixThoseOnes(path, destination, overwrite = False):
    existingDirBool = os.path.isdir(destination+'\\0')
    if existingDirBool == True:
        print('full directory')
    if existingDirBool == False or overwrite == True:
        for filepath in glob.glob(os.path.join(path, '*.dat')):
            breakpath = filepath.split('\\')
            filename = breakpath[len(breakpath)-1]
            fnboyo = filename.split('_(')[0]
            breakScan = filename.split('_(')[-1]
            breakScan = breakScan.split(')_')[0]
            breakScan = breakScan.split('_')
            delayString = breakScan[0]
            if '-' in delayString:
                delayString = delayString.strip('-')
            elif delayString == '0.0':
                delayString = delayString
            else:
                delayString = '-' + delayString
            delayIndex = str(breakScan[1])
            scanNum = str(breakScan[3])
            roundNum = str(breakScan[2])
            shutil.copyfile(filepath, destination + '\\' + fnboyo + '_(' + delayString + '_' + delayIndex + '_' + roundNum + '_' + scanNum + ')_.dat')
        print('set sorted')

def noiseRemover(path, destination, th, hm, overwrite = False, updateThis = None):
    dodged = 0
    proc = False
    if os.path.isdir(destination) == True:
        if len(os.listdir(destination)) > 0:
            if overwrite:
                os.rmdir(destination)
                if updateThis != None:
                    try:
                        updateThis('noiseRemover destination overwrite')
                    except Exception as e:
                        print(e)
                print('noiseRemover destination overwrite')
                os.mkdir(destination)
                proc = True
            else:
                if updateThis != None:
                    try:
                        updateThis('noiseRemover destination exists')
                    except Exception as e:
                        print(e)
                print('noiseRemover destination exists')
                proc = False
        else:
            proc = True
    else:
        os.mkdir(destination)
        proc = True
    if proc:
        for filepath in glob.glob(os.path.join(path, '*.dat')):
            howmany = 0
            breakpath = filepath.split('\\')
            filename = breakpath[len(breakpath)-1]
            try:
                loadarray = np.loadtxt(filepath, dtype=float)
                dE = loadarray[:,2]
                for val in list(dE):
                    if abs(val) > th:
                        howmany += 1
                if howmany >= hm:
                    dodged += 1
                else:
                    shutil.copyfile(filepath, destination + '\\' + filename)
            except:
                print('skipped: ',filename)
                if updateThis != None:
                    try:
                        updateThis('skipped: ' + filename)
                    except Exception as e:
                        print(e)
        print(dodged)
        if updateThis != None:
            try:
                updateThis('dodged: '+str(dodged))
            except Exception as e:
                print(e)
    else:
        print('did not proceed with noise remove')
        if updateThis != None:
            try:
                updateThis('did not proceed with noise remove')
            except Exception as e:
                print(e)

def windowShortener(path, destination, xSlice):
    for filepath in glob.glob(os.path.join(path, '*.dat')):
        breakpath = filepath.split('\\')
        filename = breakpath[len(breakpath)-1]
        try:
            loadarray = np.loadtxt(filepath, dtype=float)
            newArray = loadarray[xSlice]
            with open(destination + '\\' + filename, 'wb') as newFile:
                for i in range(len(newArray)):
                    newFile.write('{t:.4f} {E:.4f} {dE:.4f}'.format(t = newArray[i,0], E = newArray[i,1], dE = newArray[i,2]))
                newFile.close()
        except Exception as e:
            print(e)
            print('skipped: ',filename)
            
def exportPlotData(path, x, xHeader, fmt='%.4e', delimiter=' ', newline='\n', comments = None, **y):
    line0 = xHeader + ' ' + ' '.join(list(y.keys()))
    x = np.array([x])
    for key in y:
        x = np.concatenate(( x, np.array([y[key]]) ), axis = 0)
    x = x.T
    kwa = {'header':line0}
    if comments != None and type(comments) == str:
        kwa['comments'] = '# ' + comments + '\n'
        kwa['header'] = '# ' + line0
    np.savetxt(path, x, fmt = fmt, delimiter = delimiter, newline = newline, **kwa)