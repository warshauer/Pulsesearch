import numpy as np

class stageController():
    def __init__(self, whoami, stage_limits = [-100,100], memory_file = None):
        self.me = whoami
        self._stage_limits = stage_limits
        if memory_file == None:
            self._positions = {0:0.0, 1:0.0, 2:0.0}
            self._mem = False
        else:
            self._positions = {}
            with open(memory_file) as f:
                for line in f:
                    self._positions[int(line.split(';')[0])] = float(line.split(';')[1])
            self._mem = True
            self._memory_file = memory_file
        self.me = whoami

    def position(self, stage):
        # return whatever reads a position lmao()
        return self._positions[stage]

    def move_to_position(self, stage, position):
        # whatever moves to a position lmao()
        if position < self._stage_limits[1] and position > self._stage_limits[0]:
            pass
        elif position > self._stage_limits[1]:
            position = self._stage_limits[1]
        elif position < self._stage_limits[0]:
            position = self._stage_limits[0]
        self._positions[stage] = position
        if self._mem:
            self._write_to_memory()

    def move_step(self, stage, step):
        # whatever moves to a position lmao()
        position = self._positions[stage] + step*.001
        if position < self._stage_limits[1] and position > self._stage_limits[0]:
            pass
        elif position > self._stage_limits[1]:
            position = self._stage_limits[1]
        elif position < self._stage_limits[0]:
            position = self._stage_limits[0]
        self._positions[stage] = position
        #print(type(self._positions),self._positions)
        if self._mem:
            self._write_to_memory()

    def _write_to_memory(self):
        f = open(self._memory_file, 'w')
        for key in self._positions:
            f.write(str(key)+';'+str(self._positions[key])+'\n')
        f.close()

    def positions(self):
        return tuple([self._positions[0], self._positions[1], self._positions[2]])

    def moving(self):
        return False



class lockinAmplifier():
    def __init__(self, whoami, relevant_stage_controller, memory_file = None, chopped_beam = 'THz'): # for spoofing, should pass it the stageController instance
        self.me = whoami
        self._chopped_beam = chopped_beam
        self._SC = relevant_stage_controller
        if memory_file == None:
            self._queriables = {'sensitivity':'2mV', 'time constant':'30ms', 'chopping frequency':501}
        else:
            self._queriables = {}
            with open(memory_file) as f:
                for line in f:
                    self._queriables[line.split(';')[0]] = float(line.split(';')[1])
        self.TT = np.loadtxt('TT.txt').T
        self.PP = np.loadtxt('PP.txt').T
        self._pfac = .001
        self._tfac = 1

    def query(self, query):
        # we ask for query here
        return self._queriables[query]

    def get_output(self):
        dtdt = self._noisemaker( self._resample( self.TT[0], self.TT[1], np.array([self._SC.position(1) - self._SC.position(0)]) )[0], a = .01, b = .01)*self._tfac
        dpdp = self._noisemaker( self._resample( self.PP[0], self.PP[1], np.array([self._SC.position(0)]) )[0], a = .01, b = .01)*self._pfac
        dpump = dpdp*dtdt
        dthz = dtdt*(1 + dpdp)
        if self._chopped_beam == 'THz':
            return dthz
        else:
            return dpump

    def autophase(self):
        pass

    def change_setting(self, setting, value):
        self._queriables[query] = value

    def _noisemaker(self, val, a = .01, b = .01):
        return (val+np.random.normal(0, a))*np.random.normal(1, b)

    def _resample(self, x0, y0, x):
        y = np.zeros(x.shape, dtype = np.float64)
        for i in range(len(x)):
            ld = np.abs(x[i] - x0)
            i1 = np.argpartition(ld, 1-1)[1-1]
            i2 = np.argpartition(ld, 2-1)[2-1]
            s = (y0[i2]-y0[i1]) / (x0[i2]-x0[i1])
            yi = y0[i1] - s*x0[i1]
            y[i] = s*x[i] + yi
        return y