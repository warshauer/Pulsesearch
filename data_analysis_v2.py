#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import numpy as np
import matplotlib.pyplot as plt
import os
import glob
from scipy.fft import fft, fftfreq
import pandas as pd
import random
import matplotlib.colors as mcolors
random.seed(4)
import shutil

def grod(delays,domain, helpme=False):
    if helpme==True:
        print('takes: delays(["0",".5","1","10"]),domain([.2,2]), returns list of those between start and end [".5","1"]')
    tzst1=delays;tz1=[];tzst=[]
    for thing in tzst1:
        tz1.append(float(thing))
    tz = [ x for x in tz1 if domain[0] <= x <= domain[1] ]
    for oi in tz:
        tzst.append(("%.2f" % oi).rstrip('0').rstrip('.').replace('0.','.'))
    return [tzst, tz]

def rounder(ok, fac):
    ok2=[]
    for j in range(fac):
        ok2.append(ok[j])
    for i in range(fac,len(ok)-fac):
        ok2.append(sum(ok[i-fac:i+fac+1])/(fac*2+1))
    for j in range(fac):
        ok2.append(ok[len(ok)-fac+j])
    return ok2

def get_equil_R_t(equilibriumDF, frequencies, fac=0):
    eVRs=[]
    eVts=[]
    for gV in frequencies:
        a_list = equilibriumDF.copy()
        difference_function = lambda list_value : abs(gV - list_value)
        lofdif=difference_function(a_list['freq'])
        i1 = lofdif.argmin()
        lofdif.drop(i1)
        i2 = lofdif.argmin()
        if i2==i1:
            i2=i1+1
        else:
            i1=i2
            i2=i1+1
        sLR=(a_list['R'][i2]-a_list['R'][i1])/(a_list['freq'][i2]-a_list['freq'][i1])
        bLR=(a_list['R'][i2])-sLR*(a_list['freq'][i2])
        sLt=(a_list['theta'][i2]-a_list['theta'][i1])/(a_list['freq'][i2]-a_list['freq'][i1])
        bLt=(a_list['theta'][i2])-sLt*(a_list['freq'][i2])
        eVR=sLR*gV+bLR
        eVt=sLt*gV+bLt
        eVRs.append(eVR)
        eVts.append(eVt)
    itdic={}
    itdic['freq']=frequencies
    itdic['R']=rounder(eVRs,fac)
    itdic['theta']=rounder(eVts,fac)
    dframe = pd.DataFrame(itdic)
    return dframe

def unit_conversion(time=False, freq=False, angularfreq=False, length=False, energy=False, cm=False):
    c=299.792
    hc=1239.841
    if time!=False:
        freq=1/time
        angularfreq=2*np.pi*freq
        length=c*time
        energy=hc/length
        cm=1/time/c*10000
    if freq!=False:
        time=1/freq
        angularfreq=2*np.pi*freq
        length=c*time
        energy=hc/length
        cm=1/time/c*10000
    if angularfreq!=False:
        freq=angularfreq/2/np.pi
        time=1/freq
        length=c*time
        energy=hc/length
        cm=1/time/c*10000
    if length!=False:
        time=length/c
        freq=1/time
        angularfreq=2*np.pi*freq
        energy=hc/length
        cm=1/time/c*10000
    if energy!=False:
        length=hc/energy
        time=length/c
        freq=1/time
        angularfreq=2*np.pi*freq
        cm=1/time/c*10000
    if cm!=False:
        time=1/c/cm*10000
        length=c*time
        freq=1/time
        angularfreq=2*np.pi*freq
        energy=hc/length
    #print('time (ps): ', time, ';    length (um): ', length)
    #print('freq (THz): ', freq, ';   angularfreq (rad/ps): ', angularfreq, ';   cm (cm^-1): ', cm)
    #print('energy (meV): ', energy)
    unitdict={}
    unitdict['time']=time
    unitdict['length']=length
    unitdict['freq']=freq
    unitdict['angularfreq']=angularfreq
    unitdict['energy']=energy
    unitdict['cm']=cm
    unitdict['units']=['ps','um','THz','rad/ps','meV','cm^-1']
    return unitdict

def FFTabs(dataT,dataE):
    N = len(dataT)
    T= dataT[2]-dataT[1]
    yf = fft(dataE)
    xf = fftfreq(N, T)[:N//2]
    d={'freq': xf, 'E': 2.0/N * np.abs(yf[0:N//2])}
    return pd.DataFrame(data=d)

def FFT(dataT,dataE):
    N = len(dataT)
    T= dataT[2]-dataT[1]
    yf = fft(dataE)
    xf = fftfreq(N, T)[:N//2]
    d={'freq': xf, 'E': 2.0/N * yf[0:N//2]}
    return pd.DataFrame(data=d)

def FFTnorm(dataT,datadE,dataE):
    N = len(dataT)
    T= dataT[2]-dataT[1]
    yfE = fft(dataE)
    yfdE = fft(datadE)
    yf = yfdE/yfE
    xf = fftfreq(N, T)[:N//2]
    d={'freq': xf, 'E': 2.0/N * np.abs(yf[0:N//2])}
    return pd.DataFrame(data=d)

def trnb(df):
    work=df.copy()
    kw1=list(work.filter(regex='rt_',axis=1).columns)
    indyfolk=0
    for kw in kw1:
        work['trn_'+str(indyfolk)]=(1-work[kw]).divide(1+work[kw])
        df['trn_'+str(indyfolk)]=work['trn_'+str(indyfolk)].copy()
        df['trnR_'+str(indyfolk)]=work['trn_'+str(indyfolk)].copy().apply(np.real).copy()
        df['trnI_'+str(indyfolk)]=work['trn_'+str(indyfolk)].copy().apply(np.real).copy()
        indyfolk=indyfolk+1
    work['trnm']= work.filter(like='trn_').mean(axis=1)
    df['trnm']=work['trnm'].copy()
    df['trnRm']=np.real(work.trnm).copy()
    df['trnIm']=np.imag(work.trnm).copy()
    return df
def trnbfit(df):
    work=df.copy()
    kw1=list(work.filter(regex='rtfit_',axis=1).columns)
    indyfolk=0
    for kw in kw1:
        work['trnfit_'+str(indyfolk)]=(1-work[kw]).divide(1+work[kw])
        df['trnfit_'+str(indyfolk)]=work['trnfit_'+str(indyfolk)].copy()
        df['trnRfit_'+str(indyfolk)]=work['trnfit_'+str(indyfolk)].copy().apply(np.real).copy()
        df['trnIfit_'+str(indyfolk)]=work['trnfit_'+str(indyfolk)].copy().apply(np.real).copy()
        indyfolk=indyfolk+1
    work['trnfitm']= work.filter(like='trnfit_').mean(axis=1)
    df['trnfitm']=work['trnfitm'].copy()
    df['trnRfitm']=np.real(work.trnfitm).copy()
    df['trnIfitm']=np.imag(work.trnfitm).copy()
    return df

def rounder(ok, fac):
    ok2=[]
    for j in range(fac):
        ok2.append(ok[j])
    for i in range(fac,len(ok)-fac):
        ok2.append(sum(ok[i-fac:i+fac+1])/(fac*2+1))
    for j in range(fac):
        ok2.append(ok[len(ok)-fac+j])
    return ok2

def rounder_df(df,key, fac):
    work=df.copy()
    ok=work[key].values.tolist()
    ok2=[]
    for j in range(fac):
        ok2.append(ok[j])
    for i in range(fac,len(ok)-fac):
        #ok2.append(sum(ok[i-fac:i+fac+1])/(fac*2+1))
        #ok2.append((sum(ok[i-fac:i+fac+1])+ok[i])/(fac*2+2))
        ok2.append((sum(ok[i-fac:i+fac+1])+fac*ok[i])/(fac*2+1+fac))
    for j in range(fac):
        ok2.append(ok[len(ok)-fac+j])
    work[key]=ok2
    df=work.copy()
    return df

def dSigb(df, epsinf):
    work=df.copy()
    kw1=list(work.filter(regex='trn_',axis=1).columns)
    indyfolk=0
    for kw in kw1:
        work['dSigb_'+str(indyfolk)]=((work['freq']).multiply((((work[kw]+work['cn']).multiply(work[kw]+work['cn']))-epsinf)).divide(1.8j))-work['Sig']
        df['dSigb_'+str(indyfolk)]=work['dSigb_'+str(indyfolk)].copy()
        df['dSig1b_'+str(indyfolk)]=work['dSigb_'+str(indyfolk)].copy().apply(np.real).copy()
        df['dSig2b_'+str(indyfolk)]=work['dSigb_'+str(indyfolk)].copy().apply(np.imag).copy()
        indyfolk=indyfolk+1
    work['dSigbm']= work.filter(like='dSigb_').mean(axis=1)
    df['dSigbm']=work['dSigbm'].copy()
    df['dSig1bm']=np.real(work.dSigbm).copy()
    df['dSig2bm']=np.imag(work.dSigbm).copy()
    return df

def dSigbfit(df, epsinf):
    work=df.copy()
    kw1=list(work.filter(regex='trn_',axis=1).columns)
    indyfolk=0
    for kw in kw1:
        work['dSigbfit_'+str(indyfolk)]=((work['freq']).multiply((((work[kw]+work['cnfit']).multiply(work[kw]+work['cnfit']))-epsinf)).divide(1.8j))-work['Sigfit']
        df['dSigbfit_'+str(indyfolk)]=work['dSigbfit_'+str(indyfolk)].copy()
        df['dSig1bfit_'+str(indyfolk)]=work['dSigbfit_'+str(indyfolk)].copy().apply(np.real).copy()
        df['dSig2bfit_'+str(indyfolk)]=work['dSigbfit_'+str(indyfolk)].copy().apply(np.imag).copy()
        indyfolk=indyfolk+1
    work['dSigbfitm']= work.filter(like='dSigbfit_').mean(axis=1)
    df['dSigbfitm']=work['dSigbfitm'].copy()
    df['dSig1bfitm']=np.real(work.dSigbfitm).copy()
    df['dSig2bfitm']=np.imag(work.dSigbfitm).copy()
    return df

def add0line(df):
    work=df.copy()
    work['zero']=work['freq'].multiply(0).copy()
    df['zero']=work['zero'].copy()
    return df

def dlfitfunct3(df,wpi,taui,w0i,divfac):
    work=df.copy()
    dlsigfit=[]
    freqmeV=[]
    freqcm=[]
    for fthz in work['freq']:
        w=unit_conversion(freq=fthz)['cm']
        val=(wpi[0]*wpi[0]*(taui[0]))/(4*3.1415*(1-1j*w*taui[0]))
        for hm in range(1,len(wpi)):
            val=val+(wpi[hm]*wpi[hm]*(w))/(4*3.1415*(w/taui[hm]+1j*(w0i[hm]*w0i[hm]-w*w)))
        dlsigfit.append(val/divfac)
        freqcm.append(w)
        freqmeV.append(unit_conversion(freq=fthz)['energy'])
    work['Sigfit']=dlsigfit
    df['Sigfit']=(work['Sigfit']).copy()
    df['Sig1fit']=np.real(work['Sigfit']).copy()
    df['Sig2fit']=np.imag(work['Sigfit']).copy()
    df['freqmeV']=freqmeV
    df['freqcm']=freqcm
    return df

def sigfit2cnfit(df,epsinf,helpme=False):
    if helpme==True:
        print("takes df with Sigfit, freq, and also epsinf, returns cnfit, cnRfit, cnIfit, rfit, rRfit, rIfit")
    work=df.copy()
    work['cnfit']=((work['Sigfit'].divide(work['freq'])).multiply(1.8j) + epsinf).apply(np.sqrt)
    work['rfit']=(work['cnfit']-1).divide(work['cnfit']+1)
    df['cnfit']=work['cnfit'].copy()
    df['rfit']=work['rfit'].copy()
    df['cnRfit']=np.real(work['cnfit']).copy()
    df['cnIfit']=np.imag(work['cnfit']).copy()
    df['rRfit']=np.real(work['rfit']).copy()
    df['rIfit']=np.imag(work['rfit']).copy()
    return df

def statpad(dfs,fac):
    SP_dfs={}
    keyso=[]
    for key in dfs:
        keyso.append(key)
        SP_dfs[key]=dfs[key].copy()
    #print(len(keyso))
    SP_dffs={}
    oi=0
    for key in SP_dfs:
        sl=len(SP_dfs[key]['time'])
        dt=SP_dfs[key]['time'][2]-SP_dfs[key]['time'][1]
        newtime=np.linspace(0,SP_dfs[key]['time'][sl-1]*fac,sl*fac-1)
        el=len(newtime)
        mCols=list(SP_dfs[key].columns)
        SP_dfs[key]=actualadd(SP_dfs[key],mCols,el,sl)
        SP_dfs[key]['time']=newtime
        
        keywords=list(SP_dfs[key].filter(regex='aE_',axis=1).columns)
        j=0
        for keyo in keywords:
            if j==0:
                spdff=FFT(SP_dfs[key]['time'].to_numpy(),SP_dfs[key][keyo].to_numpy()).rename(columns={"E": "aEf_"+str(j)})
                spdff_stack=spdff
                j=j+1
            else:
                spdff=FFT(SP_dfs[key]['time'].to_numpy(),SP_dfs[key][keyo].to_numpy()).rename(columns={"E": "aEf_"+str(j)})
                spdff_stack=spdff_stack.join(spdff[["aEf_"+str(j)]])
                j=j+1
        keywords=list(SP_dfs[key].filter(regex='dE_',axis=1).columns)
        j=0
        for keyo in keywords:
            spdff=FFT(SP_dfs[key]['time'].to_numpy(),SP_dfs[key][keyo].to_numpy()).rename(columns={"E": "dEf_"+str(j)})
            spdff_stack=spdff_stack.join(spdff[["dEf_"+str(j)]])
            j=j+1
            
        SP_dffs[key]=spdff_stack
        SP_dffs[key]['aEfmean'] = SP_dffs[key].filter(like='aEf_').mean(axis=1)
        SP_dffs[key]['dEfmean'] = SP_dffs[key].filter(like='dEf_').mean(axis=1)
        SP_dffs[key]['dEfm_over_aEfm'] = SP_dffs[key]['dEfmean']/SP_dffs[key]['aEfmean']
        keywords2=list(SP_dffs[key].filter(regex='aEf_',axis=1).columns)
        keywords1=list(SP_dffs[key].filter(regex='dEf_',axis=1).columns)
        j=0
        for index in range(len(keywords1)):
            SP_dffs[key]['dEfoveraEf_'+str(j)]=SP_dffs[key][keywords1[j]]/SP_dffs[key][keywords2[j]]
            j=j+1
        oi=oi+1
        loadingbar(oi,len(keyso), key)
    return SP_dfs,SP_dffs

def actualadd(sp,mCols,el,sl):
    for i in range(el-sl):
        sp.loc[-1] = np.zeros(len(mCols))  # adding a row
        sp.index = sp.index + 1  # shifting index
        sp = sp.sort_index()  # sorting by index
    return sp

def plot(tf,data,datas=False,tfs=False,leg=range(100),title=False,xlims=False,ylims=False,log=False,xlabel='time delay (ps)',ylabel='E (mV)',alf=[1,1,1,1,1,1,1,1,1,1,1],col=False):
    fig, axs = plt.subplots(figsize=(12,8))
    if tfs==False:
        if datas==False:
            axs.plot(tf, data)
        if datas!=False:
            for i in range(len(datas)):
                axs.plot(tf, data[i], leg[i])
    if tfs==True:
        if datas==False:
            axs.plot(tf, data)
        if datas!=False:
            for i in range(len(data)):
                axs.plot(tf[i], data[i], leg[i])
    axs.set_ylabel(ylabel,fontsize=16)
    axs.set_title(title,fontsize=16)
    axs.set_xlabel(xlabel,fontsize=16)
    axs.legend(loc="best",fontsize=10)
    axs.tick_params(axis='both', which='major', labelsize=14)
    if log==True:
        axs.set_yscale("log")
    if ylims==False:
        print('y nolimits')
    else:
        axs.set_ylim(ylims[0],ylims[1])
    if xlims==False:
        print('x nolimits')
    else:
        axs.set_xlim(xlims[0],xlims[1])
    #axs.set_ylim(bot,top)
    plt.show()

def simpleplot(tf,dfs,title=False,xlims=False,ylims=False,leg=False,normalize=False,log=False,xlabel='time delay (ps)',ylabel='E (mV)',alf=[1,1,1,1,1,1,1,1,1,1,1],col=False,linesty=['solid','solid','solid','solid','solid','solid','solid','solid','solid','solid','solid','solid','solid'],colors=False):
    fig, axs = plt.subplots(figsize=(12,8))
    plotlim=120
    if colors==False:
        if normalize==False:
            norma=np.ones(len(dfs))
        else:
            norma=normalize
        for i in range(len(dfs)):
            try:
                keywords=list(dfs[i].columns)
                for key in keywords:
                    axs.plot(tf[i][key][:plotlim], dfs[i][key][:plotlim]/norma[i][key],alpha=alf[i],linestyle=linesty[i])
            except:
                if leg[i]==False:
                    axs.plot(tf[i][:plotlim], dfs[i][:plotlim]/norma[i],alpha=alf[i],linestyle=linesty[i])
                else:
                    axs.plot(tf[i][:plotlim], dfs[i][:plotlim]/norma[i],alpha=alf[i],label=leg[i],linestyle=linesty[i])
                    
    else:
        if normalize==False:
            norma=np.ones(len(dfs))
        else:
            norma=normalize
        for i in range(len(dfs)):
            try:
                keywords=list(dfs[i].columns)
                for key in keywords:
                    axs.plot(tf, dfs[i][key][:plotlim]/norma[i][key],alpha=alf[i],linestyle=linesty[i],c=colors[i])
            except:
                if leg[i]==False:
                    axs.plot(tf, dfs[i][:plotlim]/norma[i],alpha=alf[i],linestyle=linesty[i],c=colors[i])
                else:
                    axs.plot(tf, dfs[i][:plotlim]/norma[i],alpha=alf[i],label=leg[i],linestyle=linesty[i],c=colors[i])
    axs.set_ylabel(ylabel,fontsize=16)
    axs.set_title(title,fontsize=16)
    axs.set_xlabel(xlabel,fontsize=16)
    axs.legend(loc="best",fontsize=10)
    axs.tick_params(axis='both', which='major', labelsize=14)
    if log==True:
        axs.set_yscale("log")
    if ylims==False:
        print('y nolimits')
    else:
        axs.set_ylim(ylims[0],ylims[1])
    if xlims==False:
        print('x nolimits')
    else:
        axs.set_xlim(xlims[0],xlims[1])
    #axs.set_ylim(bot,top)
    plt.show()

def upload_scan_to_array_txt(path):
    data={}
    for filename in glob.glob(os.path.join(path, '*.txt')):
        data[filename[32:]] = np.loadtxt(filename, dtype=float)
    keys=[]
    lengths=[]
    for key in data:
        keys.append(key)
        lengths.append(len(data[key][:,0]))
    numScans=len(keys)
    data_avg=np.zeros((min(lengths),len(data[key][0,:])))
    i=0
    for key in keys:
        data_avg+=data[key][:min(lengths)]
        i+=1
    data_avg/=i
    data['avg']=data_avg
    for key in data:
        keys.append(key)
    return data, keys, lengths, numScans

def upload_scan_to_array_dat(path):
    data={}
    count=1
    for filename in glob.glob(os.path.join(path, '*.dat')):
        data[str(count)] = np.transpose(np.loadtxt(filename, dtype=float))
        count+=1
    keys=[]
    lengths=[]
    for key in data:
        keys.append(key)
        lengths.append(len(data[key][0,:]))
    numScans=len(keys)
    #print(len(data[key][:,0]))
    data_avg=np.zeros((len(data[key][:,2]),min(lengths)))
    #print(data_avg)
    i=0
    for k in keys:
        data_avg+=data[k][:min(lengths)]
        i+=1
    data_avg/=i
    data['avg']=data_avg
    for key in data:
        keys.append(key)
    return data, keys, lengths, numScans

def plot_calib(dataDL, dataSLon, dataSLoff, calibval, title):
    fig, axs = plt.subplots(1,2,figsize=(16,5))
    axs[0].plot(dataDL[0,:],dataDL[1,:],alpha=.75,label='DL')
    axs[0].plot(dataSLon[0,:],dataSLon[1,:],alpha=.75,label='SL on')
    axs[0].plot(dataSLoff[0,:],dataSLoff[1,:],alpha=.75,label='SL off')
    axs[1].plot(dataDL[0,:],calibval*dataDL[2,:],alpha=.75,label='DL')
    axs[1].plot(dataSLon[0,:],dataSLon[1,:]-dataSLoff[1,:],alpha=.75,label='SL')
    axs[0].set_ylabel("E (mV)",fontsize=16)
    axs[0].set_title(title + ' E THz waveform',fontsize=16)
    axs[1].set_ylabel("E on-off (mV)",fontsize=16)
    axs[1].set_title(title + ' Ediff pumpon-pumoff cv=' + str(calibval),fontsize=16)
    axs[0].set_xlabel("time delay (ps)",fontsize=16)
    axs[1].set_xlabel("time delay (ps)",fontsize=16)
    axs[0].legend(loc="upper right",fontsize=10)
    axs[1].legend(loc="upper right",fontsize=10)
    axs[0].tick_params(axis='both', which='major', labelsize=14)
    axs[1].tick_params(axis='both', which='major', labelsize=14)
    axs[0].set_ylim(12/10*np.amin(dataDL[5:,1]),12/10*np.amax(dataDL[5:,1]))
    #axs[0].set_xlim(0,6.4)
    axs[1].set_ylim(14/10*np.amin(calibval*dataDL[:,2]),14/10*np.amax(calibval*dataDL[:,2]))
    #axs[1].set_xlim(0,6.4)
    plt.show()

def loadingbar(tasknum,numtasks, text):
    space=" |"
    for i in range(numtasks):
        if i<tasknum:
            space=space+chr(9619)
        else:
            space=space+' '
    space=space+"| "+str(tasknum)+'/'+str(numtasks)+'  '
    print(space+text+'    ', end='\r')

def sorter(folderpath, material, delaylist, numPerRound):
    path_sorted=folderpath+'\\'+material+'_sorted'
    path_unsorted=folderpath+'\\'+material
    existingDirBool=os.path.isdir(path_sorted)
    seendelays=[]
    if existingDirBool==True:
        print('sorted folder existent, did not resort')
    if existingDirBool==False:
        os.mkdir(path_sorted)
        for delayer in delaylist:
            os.mkdir(path_sorted+'\\'+delayer)
        for filepath in glob.glob(os.path.join(path_unsorted, '*.dat')):
            #print(filepath)
            breakpath=filepath.split('\\')
            filename=breakpath[len(breakpath)-1]
            breakScan=filepath.split('_')
            scannum=int(breakScan[len(breakScan)-1].split('.')[0])
            if (scannum-1)%numPerRound==0:
                sendback=True
            else:
                sendback=False
            breakDelay = filepath.replace(' ','').split('Delay')
            delay = breakDelay[1].split('ps')[0].replace('p','.').replace('m','-')
            if delay not in seendelays:
                seendelays.append(delay)
            indy500 = delaylist.index(delay)
            if sendback==True:
                shutil.copyfile(filepath, path_sorted+'\\'+delaylist[indy500-1]+'\\'+filename)
            else:
                shutil.copyfile(filepath, path_sorted+'\\'+delaylist[indy500]+'\\'+filename)
        print('congrats')
        for d in delaylist:
            if d not in seendelays:
                print(d+' problem')

def megaload_DL(folder,material,cv,SP=2,OoMadj=1):
    first_dfs={}
    first_dffs={}
    filelabel={}
    helperouter=[]
    oivey=0
    delays=os.listdir(folder+'\\'+material+'_sorted')
    tot=len(delays)
    #print('items='+str(tot))
    for de in delays:
        oivey=oivey+1
        i=0
        path_folder = folder+'\\'+material+'_sorted'+'\\'+de
        helperouter.append(de)
        loadingbar(oivey,tot, de)
        for filename in glob.glob(os.path.join(path_folder, '*.dat')):
            if i==0:
                df=pd.read_csv(filename, delimiter=' ',usecols=['#Time','Intensity_1st','lock-in']).rename(columns={"#Time": "time", "Intensity_1st": "aE_"+str(i),"lock-in": "dE_"+str(i)})
                df_stack=df
                filelabel[de+'_'+str(i)]=filename
                i=i+1
            else:
                df=pd.read_csv(filename, delimiter=' ',usecols=['#Time','Intensity_1st','lock-in']).rename(columns={"#Time": "time", "Intensity_1st": "aE_"+str(i),"lock-in": "dE_"+str(i)})
                df_stack=df_stack.join(df[["aE_"+str(i),"dE_"+str(i)]])
                filelabel[de+'_'+str(i)]=filename
                i=i+1
        first_dfs[de]=df_stack
        keywords=list(first_dfs[de].filter(regex='aE_',axis=1).columns)
        for key in keywords:
            first_dfs[de][key] = first_dfs[de][key].multiply(OoMadj)
        first_dfs[de]['aEmean'] = first_dfs[de].filter(like='aE_').mean(axis=1)
            
        keywords=list(first_dfs[de].filter(regex='dE_',axis=1).columns)
        for key in keywords:
            first_dfs[de][key] = first_dfs[de][key].multiply(cv).multiply(OoMadj)
        first_dfs[de]['dEmean'] = first_dfs[de].filter(like='dE_').mean(axis=1)
            
        keywords=list(first_dfs[de].filter(regex='aE_',axis=1).columns)
        j=0
        for key in keywords:
            if j==0:
                dff=FFT(first_dfs[de]['time'].to_numpy(),first_dfs[de][key].to_numpy()).rename(columns={"E": "aEf_"+str(j)})
                dff_stack=dff
                j=j+1
            else:
                dff=FFT(first_dfs[de]['time'].to_numpy(),first_dfs[de][key].to_numpy()).rename(columns={"E": "aEf_"+str(j)})
                dff_stack=dff_stack.join(dff[["aEf_"+str(j)]])
                j=j+1
        keywords=list(first_dfs[de].filter(regex='dE_',axis=1).columns)
        j=0
        for key in keywords:
            dff=FFT(first_dfs[de]['time'].to_numpy(),first_dfs[de][key].to_numpy()).rename(columns={"E": "dEf_"+str(j)})
            dff_stack=dff_stack.join(dff[["dEf_"+str(j)]])
            j=j+1
            
        first_dffs[de]=dff_stack
        first_dffs[de]['aEfmean'] = first_dffs[de].filter(like='aEf_').mean(axis=1)
        first_dffs[de]['dEfmean'] = first_dffs[de].filter(like='dEf_').mean(axis=1)
        first_dffs[de]['dEfm_over_aEfm'] = first_dffs[de]['dEfmean']/first_dffs[de]['aEfmean']
            
        keywords2=list(first_dffs[de].filter(regex='aEf_',axis=1).columns)
        keywords1=list(first_dffs[de].filter(regex='dEf_',axis=1).columns)
        j=0
        for index in range(len(keywords1)):
            first_dffs[de]['dEfoveraEf_'+str(j)]=first_dffs[de][keywords1[j]]/first_dffs[de][keywords2[j]]
            j=j+1
    print()
    first_dfs_SP2,first_dffs_SP2=statpad(first_dfs,SP)
    print()
    return first_dfs, first_dffs, filelabel, first_dfs_SP2, first_dffs_SP2

def uploadstored(storepath):
    infodict={};infolist=[]
    keydf=pd.read_pickle(storepath+'\\'+'key_store.pkl')
    deetaT={};deetaF={}
    for key in keydf['keys']:
        deetaT[key]=pd.read_pickle(storepath+'\\'+key+'_storeT.pkl')
        deetaF[key]=pd.read_pickle(storepath+'\\'+key+'_storeF.pkl')
    infodict['keys']=keydf
    infodict['delays']=pd.read_pickle(storepath+'\\'+'delays_store.pkl')['delays']
    with open(storepath+'\\'+'info.txt') as f:
        for line in f:
            infolist.append(line.strip())
    infodict['date']=infolist[0]
    infodict['temp']=infolist[1]
    infodict['fluence']=infolist[2]
    infodict['tag']=infolist[3]
    infodict['info']=infolist[5]
    return deetaT, deetaF, infodict

def uploadstoredequilibrium(storepath):
    edf={}
    keydf=pd.read_pickle(storepath+'\\'+'key_store.pkl')
    for key in keydf['keys']:
        edf[key]=pd.read_pickle(storepath+'\\'+key+'_storeEquilibrium.pkl')
    edf['keys']=keydf
    with open(storepath+'\\'+'equilibriuminfo.txt') as f:
        for line in f:
            edf['info']=line.strip()
    return edf

def equilibrium_load(folder,material, helpme=False):
    if helpme==True:
        print('takes: folder, material; give folder as path, material as material folder name. returns df dictionary of all data in folder.')
    equil_dfs={}
    temperatures=os.listdir(folder+'\\'+material)
    print(temperatures)
    for ti in temperatures:
        path_folder = folder+'\\'+material+'\\'+ti
        for filename in glob.glob(os.path.join(path_folder, '*.dat')):
            dfE=pd.read_csv(filename, delimiter='\t',usecols=['Freq','Refl','Phase']).rename(columns={"Freq": "freq", "Refl": "R","Phase": "theta"})
            dfE_stack=dfE
            equil_dfs[ti]=dfE_stack
            equil_dfs[ti]['freq'] = equil_dfs[ti]['freq'].multiply(0.0299792)
    return equil_dfs

def plotdict_creation(dataDFs,denotes,temps,delays,linestyles,ywhich,xwhich,alphas=False,colors_wtd=False,labeler=True,helpme=False):
    if helpme==True:
        print('inputs: dataDFs,denotes,temps,delays,linestyles,ywhich,xwhich,alphas=False,colors_wtd=False,labeler=True,; give as [,];[,];[[],[]];[[],[]];[,];[[],[]];str;[,];[[[],[]],[[],[]]];[False,True,...], returns: {"xdata":[],"ydata":[],"keys":[],"labels":[],"linestyles":[],"alphas":[],"colors":[]}')
    plotdict={'xdata':[],'ydata':[],'keys':[],'labels':[],'linestyles':[],'alphas':[],'colors':[]}
    if labeler==True:
        labeler=[]
        for bongo in range(len(dataDFs)):
            labeler.append(True)
    if colors_wtd==False:
        colors_wtd=[]
        for bongo in range(len(dataDFs)):
            colors_wtd.append(False)
    for w in range(len(dataDFs)):
        for w2 in range(len(ywhich[w])):
            for alternative_rock in range(len(temps[w])):
                t=temps[w][alternative_rock]
                for folk_music in range(len(delays[w])):
                    d=delays[w][folk_music]
                    plotdict['xdata'].append(dataDFs[w][t+'_'+d][xwhich])
                    plotdict['ydata'].append(dataDFs[w][t+'_'+d][ywhich[w][w2]])
                    plotdict['keys'].append(t+'_'+d)
                    if labeler[w]==True:
                        plotdict['labels'].append(t+'_'+d+' '+denotes[w])
                    else:
                        plotdict['labels'].append(False)
                    plotdict['linestyles'].append(linestyles[w])
                    if alphas==False:
                        plotdict['alphas'].append(.75)
                    else:
                        plotdict['alphas'].append(alphas[w])
                    if colors_wtd[w]==False:
                        plotdict['colors'].append((random.random(), random.random(), random.random()))
                    else:
                        plotdict['colors'].append(colors_wtd[w][alternative_rock][folk_music])
    return plotdict

def spooky_plot(tfs,dfs,title=False,xlimits=False,ylimits=False,labels=False,log=False,xlabel='time delay (ps)',ylabel='E (mV)', alphas=False, colors=False, linestyles=False, scatter=False, helpme=False):
    if helpme==True:
        print('tfs,dfs,title=False,xlimits=False,ylimits=False,labels=False,log=False,xlabel="time delay (ps)",ylabel="E (mV)",alphas=False,colors=False,linestyles=False')
    fig, axs = plt.subplots(figsize=(12,8))
    if scatter==True:
        for i in range(len(dfs)):
            if labels[i]!=False:
                axs.scatter(tfs[i], dfs[i], alpha=alphas[i], color=colors[i], label=labels[i])
            else:
                axs.scatter(tfs[i], dfs[i], alpha=alphas[i], color=colors[i])
    else:
        for i in range(len(dfs)):
            if labels[i]!=False:
                axs.plot(tfs[i], dfs[i], alpha=alphas[i], linestyle=linestyles[i], color=colors[i], label=labels[i])
            else:
                axs.plot(tfs[i], dfs[i], alpha=alphas[i], linestyle=linestyles[i], color=colors[i])
    axs.set_ylabel(ylabel,fontsize=16)
    axs.set_title(title,fontsize=16)
    axs.set_xlabel(xlabel,fontsize=16)
    if len(labels)<150:
        axs.legend(loc="best",fontsize=10)
    axs.tick_params(axis='both', which='major', labelsize=14)
    if log==True:
        axs.set_yscale("log")
    if ylimits==False:
        print('y nolimits')
    else:
        axs.set_ylim(ylimits[0],ylimits[1])
    if xlimits==False:
        print('x nolimits')
    else:
        axs.set_xlim(xlimits[0],xlimits[1])
    #axs.set_ylim(bot,top)
    plt.show()

def EZplot(xlistform,ylistform,title=False,xlimits=False,ylimits=False,labels=False,log=False,xlabel='time delay (ps)',ylabel='E (mV)', alphas=False, colors=False, linestyles=False, scatter=False, helpme=False, fontsizeZ=[20,16,16,14,14],nolegend=False,linewidth=1,scale=1,fs=[12,8]):
    if helpme==True:
        print('tfs,dfs,title=False,xlimits=False,ylimits=False,labels=False,log=False,xlabel="time delay (ps)",ylabel="E (mV)",alphas=False,colors=False,linestyles=False')
    fig, axs = plt.subplots(figsize=(fs[0],fs[1]))
    if alphas==False:
        alphas=[]
        for teto in range(len(ylistform)):
            alphas.append(1)
    if colors==False:
        colors=lonc()
    if linestyles==False:
        linestyles=[]
        for teto in range(len(ylistform)):
            linestyles.append('solid')
    if scatter==True:
        for i in range(len(ylistform)):
            if labels[i]!=False:
                axs.scatter(xlistform[i], [x * scale for x in ylistform[i]], alpha=alphas[i], color=colors[i], label=labels[i],linewidth=linewidth)
            else:
                axs.scatter(xlistform[i], [x * scale for x in ylistform[i]], alpha=alphas[i], color=colors[i],linewidth=linewidth)
    else:
        for i in range(len(ylistform)):
            if labels[i]!=False:
                axs.plot(xlistform[i], [x * scale for x in ylistform[i]], alpha=alphas[i], linestyle=linestyles[i], color=colors[i], label=labels[i],linewidth=linewidth)
            else:
                axs.plot(xlistform[i], [x * scale for x in ylistform[i]], alpha=alphas[i], linestyle=linestyles[i], color=colors[i],linewidth=linewidth)
    axs.set_ylabel(ylabel,fontsize=fontsizeZ[2])
    axs.set_title(title,fontsize=fontsizeZ[0])
    axs.set_xlabel(xlabel,fontsize=fontsizeZ[1])
    if nolegend==False:
        if len(labels)<150:
            axs.legend(loc="best",fontsize=fontsizeZ[3])
    axs.tick_params(axis='both', which='major', labelsize=fontsizeZ[4])
    if log==True:
        axs.set_yscale("log")
    if ylimits==False:
        print('y nolimits')
    else:
        axs.set_ylim(ylimits[0],ylimits[1])
    if xlimits==False:
        print('x nolimits')
    else:
        axs.set_xlim(xlimits[0],xlimits[1])
    #axs.set_ylim(bot,top)
    plt.show()
    
def lonc():
    random.seed(4)
    CSScols=[]
    for key in mcolors.CSS4_COLORS:
        CSScols.append(key)
    random.shuffle(CSScols)
    og=['tab:blue', 'darkorange', 'tab:green', 'tab:red', 'tab:purple', 'tab:brown', 'tab:pink', 'tab:gray', 'tab:olive', 'b', 'g', 'r', 'c', 'm', 'k', ]
    random.seed()
    return og+CSScols

def plotomatic(*args, xlimits = None, ylimits = None, log = False, xlabel = '', ylabel = '', 
              scatter = False, title = '', fontsizes = [20,20,20,20,20], legend = True, scale=1, figsize=[12,8], printme = False, legendPos = [1, .5]):
    fig, axs = plt.subplots(figsize=(figsize[0],figsize[1]))
    for arg in args:
        if xlimits != None:
            try:
                i0 = list(arg['x'] - xlimits[0]).index(max((arg['x'] - xlimits[0])[(arg['x'] - xlimits[0])<=0]))
            except:
                i0 = 0
            try:
                i1 = list(arg['x'] - xlimits[1]).index(min((arg['x'] - xlimits[1])[(arg['x'] - xlimits[1])>=0]))+1
            except:
                i1 = len(arg['x'] - 1)
        else:
            i0 = 0
            i1 = len(arg['x'] - 1)
        axs.plot(arg['x'][i0:i1], scale*arg['y'][i0:i1], **{key:val for key, val in arg.items() if key not in ['x','y']})
        if printme:
            print(arg['x'][i0:i1], scale*arg['y'][i0:i1])
    axs.set_ylabel(ylabel, fontsize = fontsizes[2])
    axs.set_title(title, fontsize = fontsizes[0])
    axs.set_xlabel(xlabel, fontsize = fontsizes[1])
    if legend:
            axs.legend(loc="center left",fontsize = fontsizes[3], bbox_to_anchor=(legendPos[0], legendPos[1]))
    axs.tick_params(axis='both', which='major', labelsize = fontsizes[4])
    if log:
        axs.set_yscale("log")
    if ylimits != None:
        axs.set_ylim(ylimits[0], ylimits[1])
    if xlimits != None:
        axs.set_xlim(xlimits[0], xlimits[1])
    plt.show()