import pyvisa
import serial
import time
#To check port, run 'ls /dev/tty*' in terminal, find device's name

class motionController():
    def __init__(self, parent, deviceDict):
        self.parent = parent
        self.stages = deviceDict

    def move_absolute(self, device, position):
        self.stages[device].move_absolute(axis_number = device, position = position)

    def move_step(self, stage_key, index, step_size):
        self.stages[stage_key].move_step(axis_number = index, step_size = step_size)

    def get_absolute_position(self, stage_key, index):
        return self.stages[stage_key].get_absolute_position(axis_number = index)

    def moving(self, stage_key, index):
        return self.stages[stage_key].moving(axis_number = index)


class esp301_GPIB():
    def __init__(self, port, baud_rate = 19200, timeout = 5000): #baud rate is unused, I just kept it for consistency with the usb class, but it can be removed
        self.rm = pyvisa.ResourceManager()
        print(self.rm.list_resources())
        self.port = port
        self.timeout = timeout
        self._configure_instrument('GPIB::' + str(self.port) + '::INSTR')

    def _configure_instrument(self, instrument_port):
        self.instrument = self.rm.open_resource(instrument_port)
        self.instrument.read_termination = '\r'
        self.instrument.write_termination = '\r'
        self.instrument.timeout = self.timeout
        print('def')

    def write_command(self, ascii_cmd, param1 = '', param2 = []):
        try:
            self.instrument.write(str(param1) + ascii_cmd + ','.join(list(map(lambda x: str(x), param2))) )
        except:
            time.sleep(2)
            self.instrument.clear()
            self.instrument.close()
            self._configure_instrument('GPIB::' + str(self.port) + '::INSTR')
            print('com:', ascii_cmd)
            self.instrument.write(str(param1) + ascii_cmd + ','.join(list(map(lambda x: str(x), param2))) )

    def query_command(self, ascii_cmd, param1 = '', param2 = []):
        try:
            return self.instrument.query(str(param1) + ascii_cmd + '?' + ','.join(list(map(lambda x: str(x), param2))) )
        except:
            time.sleep(2)
            self.instrument.clear()
            self.instrument.close()
            self._configure_instrument('GPIB::' + str(self.port) + '::INSTR')
            print('com:', ascii_cmd)
            return self.instrument.query(str(param1) + ascii_cmd + '?' + ','.join(list(map(lambda x: str(x), param2))) )

    #Initializing functions
    def move_absolute(self, axis_number, position, **kwargs):
        self.write_command('PA', axis_number, [position])

    def enable_axis_motor(self, axis_number):
        self.write_command('MO', axis_number)

    def set_home(self, axis_number, position):
        self.write_command('DH', axis_number, [position])

    #Runtime functions
    def check_if_moving(self, axis_number):
        return self.query_command('MD', axis_number) #0 is motion not done, 1 is motion done

    def move_step(self, axis_number, step_size, **kwargs):
        self.write_command('PR', axis_number, [step_size])

    def get_absolute_position(self, axis_number, **kwargs):
        return float(self.query_command('TP', axis_number))

    def moving(self, **kwargs):
        motion = self.query_command('MD', 0)
        if motion == '1':
            return False
        else:
            return True

    def positions(self):
        return tuple(eval('['+self.query_command('TP', 0)+']'))

    def close_connection(self):
        self.instrument.clear()
        self.instrument.close()

#To check port, run 'ls /dev/tty*' in terminal, find device's name

class esp301_USB():
    def __init__(self, port_name, baud_rate, timeout = 1):
        self.port_name = port_name
        self.initialize_serial(self.port_name, baud_rate, timeout)

    def initialize_serial(self, port_name, baud_rate, timeout):
        self.ser = serial.Serial(port_name, baud_rate, timeout=timeout)
        self.ser.reset_input_buffer()

    def read_serial(self):
        return self.ser.readline().decode('utf-8').rstrip()

    def write_command(self, ascii_cmd, param1 = '', param2 = []):
        self.ser.write(str(param1) + ascii_cmd + ','.join(list(map(lambda x: str(x), param2))) + '\r')

    def query_command(self, ascii_cmd, param1 = '', param2 = []):
        self.ser.write(str(param1) + ascii_cmd + '?' + ','.join(list(map(lambda x: str(x), param2))) + '\r')
        return self.read_serial()

    #Initializing functions
    def set_stage_position(self, axis_number, position):
        self.write_command('PA', axis_number, [position])

    def enable_axis_motor(self, axis_number):
        self.write_command('MO', axis_number)

    def set_home(self, axis_number, position):
        self.write_command('DH', axis_number, [position])

    #Runtime functions
    def check_if_moving(self, axis_number):
        return self.query_command('MD', axis_number) #0 is motion not done, 1 is motion done

    def move_step(self, axis_number, step_size):
        self.write_command('PR', axis_number, [step_size])

    def get_absolute_position(self, axis_number):
        self.query_command('TP', axis_number)

class sr830():
    def __init__(self, port, output_interface_index = 1): #Default output interface to 1 for GPIB
        self.rm = pyvisa.ResourceManager()
        print(self.rm.list_resources())
        self._configure_instrument('GPIB::' + str(port) + '::INSTR')

        self._initialize_output_interface(output_interface_index)
        
    def _configure_instrument(self,instrument_port):
        self.instrument = self.rm.open_resource(instrument_port)

    def _initialize_output_interface(self, i): #i = 0 is RS232, i = 1 is GPIB
        self.write_command('OUTX', [i])

    def write_command(self, cmd, params = []):
        full_cmd = cmd + ' ' + ','.join(list(map(lambda x: str(x), params)))
        self.instrument.write(full_cmd)

    def query_command(self, cmd, params = []):
        val = self.instrument.query(cmd + '?' + ','.join(list(map(lambda x: str(x), params))))
        return val
    
    #Runtime functions
    def get_output(self, num_data_points = 1):
        data = []
        for i in range(num_data_points):
            v = self.query_command('OUTP', [1]) 
            try:
                v = float(v.strip('\n')) * self.get_input_config_scaling_factor() * self.get_sensitivity_scaling_factor()
            except:
                pass
            if (type(v) == float):
                data.append(v)
        if (len(data) > 0):
            return sum(data)/len(data)
        elif data == []:
            return 0.0
        else:
            return data[0]
        
    def get_specific_output(self, output, num_data_points = 1):
        if output == 'Y':
            ask = 2
        elif output == 'R':
            ask = 3
        elif output == 'theta':
            ask = 4
        else:
            ask = 1
        data = []
        for i in range(num_data_points):
            v = self.query_command('OUTP', [ask]) 
            try:
                v = float(v.strip('\n')) * self.get_input_config_scaling_factor() * self.get_sensitivity_scaling_factor()
            except:
                pass
            if (type(v) == float):
                data.append(v)
        if (len(data) > 0):
            return sum(data)/len(data)
        elif data == []:
            return 0.0
        else:
            return data[0]

    def auto_phase(self):
        self.write_command('APHS')

    #Initialization functions
    def set_input_config(self, mode_number):
        self.input_config = mode_number
        self.write_command('ISRC', [mode_number])

    def set_sensitivity(self, mode_number):
        self.sensitivity = mode_number
        self.write_command('SENS', [mode_number])

    def set_time_constant(self, mode_number):
        self.write_command('OFLT', [mode_number])

    def get_reference_freq(self):
        return self.query_command('FREQ')

    def get_sensitivity_scaling_factor(self):
        a = [9, 9, 9, 9, 9, 9, 9, 9, 6, 6, 6, 6, 6, 6, 6, 6, 6, 3, 3, 3, 3, 3, 3, 3, 3, 3, 0]
        return pow(10, a[self.sensitivity])

    def get_input_config_scaling_factor(self):
        a = [0, 0, 6, 6]
        return pow(10, a[self.input_config])

    def get_sensitivity(self):
        return int(self.query_command('SENS'))

    def get_input_config(self):
        return int(self.query_command('ISRC'))

    def get_time_constant(self):
        return int(self.query_command('OFLT'))

    def close_connection(self):
        self.instrument.clear()
        self.instrument.close()

class esp301_GPIB2():
    def __init__(self, port, baud_rate = 19200, timeout = 2000): #baud rate is unused, I just kept it for consistency with the usb class, but it can be removed
        self.rm = pyvisa.ResourceManager()
        print(self.rm.list_resources())
        self.port = port
        self.timeout = timeout
        self._configure_instrument('GPIB::' + str(self.port) + '::INSTR')

    def _configure_instrument(self, instrument_port):
        self.instrument = self.rm.open_resource(instrument_port)
        self.instrument.read_termination = '\r'
        self.instrument.write_termination = '\r'
        self.instrument.timeout = self.timeout
        print('def')

    def write_command(self, ascii_cmd, param1 = '', param2 = []):
        try:
            self.instrument.write(str(param1) + ascii_cmd + ','.join(list(map(lambda x: str(x), param2))) )
        except:
            self.instrument.clear()
            self.instrument.close()
            self._configure_instrument('GPIB::' + str(self.port) + '::INSTR')
            time.sleep(.5)
            self.instrument.write(str(param1) + ascii_cmd + ','.join(list(map(lambda x: str(x), param2))) )

    def query_command(self, ascii_cmd, param1 = '', param2 = []):
        try:
            return self.instrument.query(str(param1) + ascii_cmd + '?' + ','.join(list(map(lambda x: str(x), param2))) )
        except:
            self.instrument.clear()
            self.instrument.close()
            self._configure_instrument('GPIB::' + str(self.port) + '::INSTR')
            time.sleep(1)
            return self.instrument.query(str(param1) + ascii_cmd + '?' + ','.join(list(map(lambda x: str(x), param2))) )

    #Initializing functions
    def move_to_position(self, axis_number, position):
        self.write_command('PA', axis_number, [position])

    def enable_axis_motor(self, axis_number):
        self.write_command('MO', axis_number)

    def set_home(self, axis_number, position):
        self.write_command('DH', axis_number, [position])

    #Runtime functions
    def check_if_moving(self, axis_number):
        return self.query_command('MD', axis_number) #0 is motion not done, 1 is motion done

    def move_step(self, axis_number, step_size):
        self.write_command('PR', axis_number, [step_size])

    def get_absolute_position(self, axis_number):
        return float(self.query_command('TP', axis_number))

    def moving(self):
        motion = self.query_command('MD', 0)
        if motion == '1':
            return False
        else:
            return True

    def positions(self):
        return tuple(eval('['+self.query_command('TP', 0)+']'))

    def close_connection(self):
        self.instrument.clear()
        self.instrument.close()

class CONEX():
    def __init__(self, port, baud_rate = 19200, timeout = 2000): # baud rate is unused, I just kept it for consistency with the usb class, but it can be removed
        self.rm = pyvisa.ResourceManager()
        print(self.rm.list_resources())
        self.port = port
        self.portAddress = 'ASRL' + str(self.port) + '::INSTR'
        self.timeout = timeout
        self._configure_instrument(self.portAddress)

    def _configure_instrument(self, instrument_port):
        self.instrument = self.rm.open_resource(instrument_port)
        self.instrument.read_termination = '\r'
        #self.instrument.write_termination = '\r'
        self.instrument.timeout = self.timeout
        self.instrument.baud_rate = 921600
        print('aye')

    def write_command(self, ascii_cmd):
        try:
            self.instrument.write(ascii_cmd)
        except:
            self.instrument.clear()
            self.instrument.close()
            self._configure_instrument(self.portAddress)
            time.sleep(.5)
            self.instrument.write(ascii_cmd)

    def query_command(self, ascii_cmd):
        try:
            self.instrument.clear()
            return self.instrument.query(ascii_cmd).split(ascii_cmd)[-1]
        except:
            self.instrument.clear()
            self.instrument.close()
            self._configure_instrument(self.portAddress)
            time.sleep(1)
            return self.instrument.query(ascii_cmd)
        
    def home_search(self):
        self.write_command('1OR')

    def get_absolute_position(self, **kwargs):
        return float(self.query_command('1TP'))
    
    def move_absolute(self, position, **kwargs): 
        self.write_command('1PA{0:.2f}'.format(position))

    def move_step(self, step_size, **kwargs):
        self.write_command('1PR{0:.2f}'.format(step_size))

    def moving(self, **kwargs):
        if str(self.query_command('1TS')) == '000033':
            return False
        else:
            return True

    def reset_controller(self):
        self.write_command('1RS')        

    def stop(self):
        self.write_command('1ST')  

