import pyvisa
import serial
import time
#To check port, run 'ls /dev/tty*' in terminal, find device's name

class esp301_GPIB():
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

#To check port, run 'ls /dev/tty*' in terminal, find device's name
class smc100_serial(serial.Serial):
    # only works for single digits axis number (string concatenations).
    def __init__(port=None, baudrate=57600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=None, xonxoff=True):
        super().__init__(baudrate, bytesize, parity, stopbits, timeout, xonxoff)
  

    def _configure_instrument(self, ser_port):
        self.port = ser_port
        self.open()
        print('serial port is open ==', self.isOpen())

    def write_command(self, cmd, param1 = '', param2 = ''):
        self.write(str(param1) + cmd + str(param2) + '\r\n')
            #self.instrument.write(str(param1) + ascii_cmd + ','.join(list(map(lambda x: str(x), param2))) )

    def query_command(self, cmd, param1 = ''):
        self.write(str(param1) + cmd + '?' + '\r\n')
        return self.readline()
        #return self.instrument.query(str(param1) + ascii_cmd + '?' + ','.join(list(map(lambda x: str(x), param2))) )

    #Initializing functions
    def move_to_position(self, axis_number, position):
        self.write_command('PA', axis_number, position)

    """def enable_axis_motor(self, axis_number):
        self.write_command('MO', axis_number)"""

    def set_home(self, axis_number, position):
        self.write_command('SE', axis_number, position)
        # see the user manual for the set point position and simutaneous move of all motors to the set point position

    #Runtime functions
    def check_if_moving(self, axis_number):
        temp = self.query_command('TS', axis_number)
        if temp[-2:] in ['32', '33', '34', '35']:
            return '1'
        else:
            return '0'
        #return self.query_command('MD', axis_number) #0 is motion not done, 1 is motion done

    def move_step(self, axis_number, step_size):
        self.write_command('PR', axis_number, step_size)

    def get_absolute_position(self, axis_number):
        temp = self.query_command('TP', axis_number)
        return float(temp[3:])

    # NEED TO BE CHANGED
    def moving(self):
        motion = self.query_command('MD', 0)
        if motion == '1':
            return False
        else:
            return True

    def positions(self):
        return tuple(eval('['+self.query_command('TP', 0)+']'))

    def close_connection(self):
        self.close()
     
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