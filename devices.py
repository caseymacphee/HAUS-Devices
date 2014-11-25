### Python module for the open source RPi-HAUS application ###
### HAUS ###
###### Configured to be run on Debian-Wheezy BST 2014 armv6l GNU/Linux ######
###########/dev/ttyACM*#######

import sys
import glob
import time
import json
import threading
import serial
from threading import Lock


class User(object):
    """
This function is the working head for Raphi. Currently processes based on regular expressesions of the
 /dev/yourarduinousbserialpathhere (from the scanportsmodule).
Returns a string with the serials that fit that specification in the form of a list of tuples (connection first, test buffer last).
The connection returns in it's open state .
    """
    _instances=[]
    serial_locks = {}

    def __init__(self):
        ports = _serial_ports()
        if len(self._instances) < 1:
            for serial_path in ports:
                self.serial_locks[serial_path] = Lock()
        self._instances.append(self)
        self.device_locks = {}
        self.named_connections = {}
        self.controllers = {}
        self.monitors = {}
        self.device_metadata = {}
        self.serial_connections = []

    def stream_forever(self):
        try:
            self.run_setup()
            inf = float("inf")
            controllers = threading.Thread(target=self.talk_to_controllers, args=(['',inf]))
            monitors = threading.Thread(target=self.read_monitors_to_json, args=([inf]))
            controllers.daemon = True
            monitors.daemon = True
            controllers.start()
            monitors.start()
        except:
            controllers.join()
            monitors.join()

    def pickup_conn(self):
        serial_paths = _serial_ports()
        serial_list = []
        for port in serial_paths:
            connection = serial.serial_for_url(port, timeout = 5)
            # connection_wrapper = io.TextIOWrapper(io.BufferedRWPair(connection,connection))
            if connection.isOpen():
                connection.close()
            serial_list.append(connection)
        self.serial_connections = serial_list
        return serial_list 

    def test_ports(self):
        pass

    def read_monitors_to_json(self, timeout = 360):
        ### listening for 30 second timeout for testing ###
        start = time.time()
        current_time = start

        while current_time - start < timeout:
            for name, port in self.monitors.iteritems():
                port_lock = self.device_locks[name]
                port_lock.acquire()
                if not port.isOpen():
                    port.open()
                current = port.read()
                while current is not '$':
                    current = port.read()
                ### Your logic goes here ###
                message = port.readline()
                jsonmessage = self.build_json(message, name)
                print jsonmessage
                port.close()
                # port_lock.release()
            current_time = time.time()

    def talk_to_controllers(self, message = '', timeout = 360):
        start = time.time()
        current_time = start
        for port in self.controllers.itervalues():
            if not port.isOpen():
                port.open()
        while current_time - start < timeout:
            for name, port in self.controllers.iteritems():
                ### Your logic goes here ###
                port_lock =  self.device_locks[name]
                port_lock.acquire()
                if name == 'zor':
                    response = port.readline()
                    response = self.build_json(response, name)
                    print response
                    for relay in '1234':
                        ## Simple test suite ##
                        port.write(relay)
                        response = port.readline()
                        response = self.build_json(response, name)
                        print response
                        port.write(relay)
                        response = port.readline()
                        response = self.build_json(response, name)
                        print response
                        time.sleep(1)
                else:
                    port.write(response)
                    response = port.readline()
                    jsonmessage = self.build_json(response, name)
                    print jsonmessage
                port_lock.release()
            current_time = time.time()
        for device in self.controllers.itervalues():
            if device.isOpen:
                device.close()

    def build_json(self, message, name):
        message = message.rstrip()
        data_thread = {}
        key_val_pairs = message.split(',')
        for pair in key_val_pairs:
            print pair
            key, val = pair.split('=')
            data_thread[key] = val
        meta_data = self.device_metadata[name]
        data_thread['device_name'] = meta_data['device_name']
        data_thread['username'] = meta_data['username']
        data_thread['access_key'] = meta_data['access_key']
        data_thread['device_type'] = meta_data['device_type']
        data_thread['timezone'] = meta_data['timezone']
        data_thread['timestamp'] = time.time()
        return json.dumps(data_thread, sort_keys = True)

    def run_setup(self, group_mode = False):
        setup_instructions = """
There are {} ports available.
If you would like to run through the device
setup (which will require you unplugging your
devices, and naming them one by one as they
connect. Enter 'quit' or 'continue': """.format(len(_serial_ports()))
        answer = raw_input(setup_instructions)
        if answer == 'q' or answer == 'quit':
            pass
        if answer == 'c' or answer == 'continue':
            answer = raw_input('Plug all your devices in now to continue, then hit enter')
            num_devices = len(_serial_ports())
            answer = int(raw_input('Found {} devices, how many devices do you want to name? (1-n): '.format(num_devices)))
            print "Unplug them now to continue..."
            ### Take number of devices connected initially and subtract devices to program ###
            
            starting = num_devices - answer
            
            while len(_serial_ports()) > (starting):
                time.sleep(1)

            device_meta_data_field_names = ('device_name', 'device_type', 'username', 'access_key', 'timezone', 'timestamp')

            username = raw_input("What is the account username for all your devices: ")
            access_key = raw_input("What is the access key?: ")
            timezone = raw_input("What is your current timezone?: ")
            
            current_number = 1
            for devices in xrange(answer):
                current_ports = _serial_ports()
                print "Now plug in device {}...".format(current_number)

                while len(current_ports) < current_number + starting:
                    time.sleep(1)
                    current_ports = _serial_ports()

                metadata = {}
                device_name = raw_input("What would you like to call device {}?: ".format(current_number))
                device_type = raw_input("Is this device a 'controller' or a 'monitor'?: ")
                baud_rate = raw_input("The default Baud rate is 9600. Set it now if you like, else hit enter: ")
                timestamp = 'timestamp'

                device_data = []
                device_data.append(device_name)
                device_data.append(device_type)
                device_data.append(username)
                device_data.append(access_key)
                device_data.append(timezone)
                device_data.append(timestamp)

                metadata = dict(zip(device_meta_data_field_names, device_data))

                self.device_metadata[device_name] = metadata

                last_port = current_ports.pop()
                ### need logic here ###

                try:
                    self.device_locks[device_name] = self.serial_locks[last_port]
                except KeyError:
                    self.serial_locks[last_port] = Lock()
                    self.device_locks[device_name] = self.serial_locks[last_port]
                
                last_device_connected = self.pickup_conn()[-1]
                if baud_rate != '':
                    try:
                        last_device_connected.baud_rate = int(baud_rate)
                    except:
                        raise Exception('Could not set that baud rate, check your input and try again.')

                if device_type == 'controller':
                    self.controllers[device_name] = last_device_connected
                elif device_type == 'monitor':
                    self.monitors[device_name] = last_device_connected
                
                self.named_connections[device_name] = last_device_connected
                current_number += 1

            current_connections = self.named_connections
            return current_connections

    def haus_api_put(self):
        pass
    def haus_api_get(self):
        pass

    def special_json(self, name, port, empty_read_limit = 10):
        if not port.readable():
            return
        ### Method broken! Byte read in is not comparable using =.
        ### VAL acts as a token to know whether the next bytes string is a key or value in the serialized form###
        ## based on continuos bytes with no newline return##
        # The start of line for this test is the '$' for username, and the EOL is '#' #
        VAL = False
        contents = {}
        port_lock = self.device_locks[name]
        port_lock.acquire()
        if not port.isOpen():
            port.open()
        current = port.read()
        while current is not '$':
            current = port.read()
        reading = True
        status = True
        empty_read_count = 0

        while reading:
            current_key = ''
            current_value = ''
            current_char_in = port.read()
            
            current_char_in = current_char_in.decode("utf-8")
            print type(current_char_in)
            if current_char_in == u'':
                status = False
                empty_read_count += 1
            elif current_char_in == u'#':
                ## IE we are getting data but end of line ##
                status = True
                reading = False
                contents[current_key] = current_value
            elif current_char_in == u',':
                ## There is a new set of key value pairs ##
                contents[current_key] = current_value
                current_value = u''
                current_key = u''
                status = True
            elif current_char_in == u'=':
                status = True
                VAL = not VAL
            else:
                status = True
                print "current val" , current_value
                print "current key" , current_key
                if VAL:
                    current_value = current_value + current_char_in
                else:
                    current_key = current_key + current_char_in
            
        print port_lock.locked()
        port_lock.release()
        print "Read status: ", status
        # if empty_read_count <= empty_read_limit:
        meta_data = self.device_metadata[name]
        contents['device_name'] = meta_data['device_name']
        contents['username'] = meta_data['username']
        contents['access_key'] = meta_data['access_key']
        contents['device_type'] = meta_data['device_type']
        contents['timezone'] = meta_data['timezone']
        contents['timestamp'] = time.time()
        return json.dumps(contents, sort_keys = True)

def _serial_ports():
    """Lists serial ports
    :raises EnvironmentError:
    On unsupported or unknown platforms
    :returns:
    A list of available serial ports
    """
    if sys.platform.startswith('win'):
        ports = ['COM' + str(i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('linux2') or sys.platform.startswith('cygwin'):
        ports = glob.glob('/dev/ttyACM*')
    elif sys.platform.startswith('darwin'):
        ### the second glob is for the xbee
        ports = glob.glob('/dev/tty.usbmodem*') + glob.glob('/dev/tty.usbserial*')
    else:
        raise EnvironmentError('Unsupported platform')
    return ports
