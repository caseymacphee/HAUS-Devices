### Python package for the open source RPi-HAUS module ###
### Home Automation User Services ###
###### Configured to be run on Debian-Wheezy BST 2014 armv6l GNU/Linux ######
###########/dev/ttyACM*#######
import serial
import io
import sys
import glob
import time
import json
import threading
from threading import Lock
from synchronize import Allocate_port_locks
class Boards(object):
    """
This function is the working head for Raphi. Currently processes based on regular expressesions of the
 /dev/yourarduinousbserialpathhere (\from the scanportsmodule).
Returns a string with the serials that fit that specification in the form of a list of tuples (connection first, test buffer last).
The connection returns in it's open state .
    """
    __metaclass__ = Allocate_port_locks
    _instances=[]
    def __init__(self):
        _instances=[]
        if(len(self._instances) > 1):
            self._instances.pop(1).kill() #kill the oldest instance
        else:
            self._instances.append(self)

        self.devices
        self.serial_connections = []
        self.labeled_connections = {}
        self.username = 'username'
        self.access_key = 'access_key'
        self.name_type = []
        self.timezone = ''
        self.controllers = {}
        self.monitors = {}

        ### for testing go straight to setup ###
        self.run_setup()
    
    def serve_forever(self):
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
    def delete(self):
        answer = raw_input("are you sure you want to do that? Answer 'yes' or 'no'")
        if answer == 'yes':
            del self

    def pickup_conn(self):
        serial_paths = _serial_ports()
        for port in serial_paths:
            connection = serial.serial_for_url(port, timeout = 5)
            # connection_wrapper = io.TextIOWrapper(io.BufferedRWPair(connection,connection))
            if connection.isOpen():
                connection.close()
            self.serial_connections.append(connection)
        return self.serial_connections

    def test_ports(self):
        pass

    def read_monitors_to_json(self, timeout = 360):
        ### listening for 30 second timeout for testing ###
        start = time.time()
        current_time = start
        for port in self.monitors.itervalues():
            if not port.isOpen():
                port.open()
        while current_time - start < timeout:
            for name, port in self.monitors.iteritems():
                ### Your logic goes here ###
                message = port.readline()
                jsonmessage = self.build_json(message, name)
                print jsonmessage
            current_time = time.time()
        for device in self.monitors.itervalues():
            if device.isOpen:
                device.close()

    def talk_to_controllers(self, message = '', timeout = 360):
        start = time.time()
        current_time = start
        for port in self.controllers.itervalues():
            if not port.isOpen():
                port.open()
        while current_time - start < timeout:
            for name, port in self.controllers.iteritems():
                ### Your logic goes here ###
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
            current_time = time.time()
        for device in self.controllers.itervalues():
            if device.isOpen:
                device.close()

    def build_json(self, message, name):
        message = message.rstrip()
        data_thread = {}
        key_val_pairs = message.split(',')
        for pair in key_val_pairs:
            key, val = pair.split('=')
            data_thread[key] = val 
        data_thread['name'] = name
        data_thread['user'] = self.username
        data_thread['access_key'] = self.access_key
        data_thread['device_type'] = 'monitor'
        return json.dumps(data_thread, sort_keys = True)

    def run_setup(self):
        num_devices=len(self.pickup_conn())
        setup_instructions = """
There are {} ports available.
If you would like to run through the device
setup (which will require you unplugging your
devices, and naming them one by one as they
connect. Enter 'quit' or 'continue': """.format(num_devices)
        answer = raw_input(setup_instructions)
        if answer == 'q' or answer == 'quit':
            pass
        if answer == 'c' or answer == 'continue':
            answer = int(raw_input('How many devices? (1-n): '))
            print "Unplug the devices now to continue..."
            starting = num_devices - answer
            if len(_serial_ports()) > 0:
                while len(_serial_ports()) > (starting):
                    time.sleep(1)
            current_number = 1
            for index in xrange(answer):
                print "Now enter device {}...".format(current_number)
                # print len(self.serial_connections)
                # print (starting + current_number)
                while len(_serial_ports()) < current_number:
                    time.sleep(1)
                name = raw_input("What would you like to call device {}?: ".format(current_number))
                sensor_type = raw_input("Is this device a 'controller' or a 'monitor'?: ")
                baud_rate = raw_input("The default Baud rate is 9600. Set it now if you like, else hit enter: ")
                username = raw_input("What is the account username for this device: ")
                self.devices
                answer = raw_input("What is the access key?: ")
                self.access_key = answer
                answer = raw_input("What is your current timezone?: ")
                self.timezone = answer
                self.name_type.append((str(name), str(sensor_type)))
                last_device_connected = self.pickup_conn()[-1]
                last_device_connected.baud_rate = baud_rate
                if sensor_type == 'controller':
                    self.controllers[name] = last_device_connected
                elif sensor_type == 'monitor':
                    self.monitors[name] = last_device_connected
                self.labeled_connections[name] = last_device_connected
                current_number += 1
                
            return self.labeled_connections

    def PiClient_request(self):
        pass

    def special_json(self, name, port, empty_read_limit = 10):
            if port.readable():
                ### VAL acts as a token to know whether the next bytes string is a key or value in the serialized form###
                ## based on continuos bytes with no newline return##
                # The start of line for this test is the '$' for username, and the EOL is '#' #
                VAL = True
                contents = {}
                if not port.isOpen():
                    port.open()
                current = port.read()
                while current is not '$':
                    current = port.read()
                reading = True
                status = True
                empty_read_count = 0
                
                while reading and empty_read_count <= empty_read_limit:
                    current_key = ''
                    current_value = ''
                    current_char_in = port.read()
                    if current_char_in == '':
                        status = False
                        empty_read_count += 1
                    elif current_char_in == '#':
                        ## IE we are getting data but end of line ##
                        status = True
                        reading = False
                    elif current_char_in == ',':
                        ## There is a new set of key value pairs ##
                        contents[current_key] = current_value
                        current_value = ''
                        current_key = ''
                        status = True
                    elif current_char_in == '=':
                        status = True
                        VAL = not VAL
                    else:
                        status = True
                        if VAL:
                            current_value = current_value + current_char_in
                        else:
                            current_key = current_key + current_char_in

                print "Read status: ",status
                if empty_read_count<= empty_read_limit:
                    contents['name'] = name
                    contents['user'] = self.username
                    contents['access_key'] = self.access_key
                    contents['device_type'] = 'monitor'
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
        ports = glob.glob('/dev/tty.usbmodem*')
    else:
        raise EnvironmentError('Unsupported platform')
    return ports