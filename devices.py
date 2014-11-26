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
from contextlib import closing


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
        self.delimiters = {}
        self.device_meta_data_field_names = (
            'device_name',
            'device_type',
            'username',
            'access_key',
            'timezone',
            'timestamp')

    def stream_forever(self):
        try:
            pass
        except:
            pass

    def pickup_conn(self):
        serial_paths = _serial_ports()
        serial_list = []
        for port in serial_paths:
            connection = serial.serial_for_url(port, timeout = 5)
            ### Make sure to close a
            if connection.isOpen():
                connection.close()
            serial_list.append(connection)
        self.serial_connections = serial_list
        return serial_list

    def test_ports(self):
        pass

    # CMGTODO: _ensure_port_is_open should be static function, or in another class
    def _ensure_port_is_open(self, port):
        if not port.isOpen():
            port.open()
        return

    def read_monitors_to_json(self, name, port, timeout = 30):
        ### listening for 30 second timeout for testing ###
        ### if you think your monitors are running slow, check for delays in your arduino sketch ###
        start_time = time.time()
        name_time = start_time

        while name_time - start_time < timeout:
            port_lock = self.device_locks[name]
            # CMGTODO
            # if we can't get a port_lock, it would probably be more
            #  efficient to give up on the current monitor than have
            #  everything else wait for it to become free.
            with port_lock:
                self._ensure_port_is_open(port)

                if ((name in self.delimiters) and
                        (self.delimiters[name][0] == ',') and
                        (self.delimiters[name][1] == '=')):
                    # CMGTODO
                    # may be possible to call read_raw passing in the
                    #  delimiters if they are available
                    jsonmessage = self.read_raw(name, port)
                else:
                    # read twice because first line may be partial
                    message = port.readline()
                    message = port.readline()
                    print message
                    jsonmessage = self._build_json(message, name)

                print jsonmessage

            now_time = time.time()
            print name, ' took: ', int(now_time - name_time), 'seconds'
            name_time = now_time

    def ping_controller_atoms(self, name, port):
        if not port.isOpen():
            port.open()
        port_lock = self.device_locks[name]
        port_lock.acquire()
        if port_lock.locked():
            print port_lock,'acquired'
            try:
                response = port.write('Okay')
                response = port.readline()
                assert response == 'Okay'
            except:
                raise Exception("Arduino didn't wake up.")
        port.write('$')
        jsonmessage = self.read_raw(name, port)
        port.close()
        port_lock.release()
        if not port_lock.locked():
            print port_lock, 'released'
        return jsonmessage

    def talk_to_controller(self, state):
        """
Use method like this:
for name, port in me.controllers.iteritems():
    me.talk_to_controller(name, port, 'Relay1', '1')

Relay's must have an '@' before them.
        """
        name = state['device_name']
        port = self.named_connections[name]

        start_time = time.time()

        jsonmessage = None

        port_lock = self.device_locks[name]
        with port_lock:
            self._ensure_port_is_open()
            try:
                response = port.write('Okay')
                response = port.readline()
                if response[0] != 'O':
                    if response != 'Okay':
                        raise("Controller is not Okay")
            except:
                raise Exception("Controller didn't wake up.")

            atoms = state['atoms']
            for key, val in atoms.iteritems():
                if key[0] == '@':
                    switch_name, switch_number = key.split('_')
                    if val == '1' or val == 1:
                        print switch_number
                        print type(switch_number)
                        port.write(str(switch_number))
                        self.read_raw(name, port)

            port.write('$')
            jsonmessage = self.read_raw(name, port)

            # CMGTODO: I don't know why this code closes
            # the port. Maybe it's required to make sure the
            # write works.
            if port.isOpen():
                port.close()

        print 'method took :', int(time.time() - start_time), ' seconds'
        return jsonmessage

    # CMGTODO: without memorized decorator, setup dictionary if seen before
    def _delimiter_factory(self, message, device_name):
        if device_name in self.delimiters:
            return self.delimiters[device_name]

        field_separator = None
        keyval_separator = None
        in_single_quote = False
        in_double_quote = False
        index = 0
        maxlen = len(message)

        while (index < maxlen) and (
              (field_separator is None) or (keyval_separator is None)):
            c = message[index]
            if (c == '"') and (not in_single_quote):
                in_double_quote = not in_double_quote
            elif (c == "'") and (not in_double_quote):
                in_single_quote = not in_single_quote
            elif in_single_quote or in_double_quote:
                # if in a quoted string, don't check for separators
                pass
            elif (c == ':') or (c == '='):
                keyval_separator = c
            elif (c == ',') or (c == ';') or (c == '\n'):
                field_separator = c
            index += 1

        self.delimiters[device_name] = [field_separator, keyval_separator]
        print "In factory: {} has field_separator[{}], keyval_separator[{}]".format(
            device_name,
            field_separator,
            keyval_separator)
        print "Original message: [{}]".format(message)

        return field_separator, keyval_separator

    def _build_json(self, message, device_name):
        try:
            message = message.rstrip()

            contents = {}
            atoms = {}

            field_separator, keyval_separator =\
                self._delimiter_factory(message, device_name)

            try:
                key_val_pairs = message.split(field_separator)
                for pair in key_val_pairs:
                    pair_list = pair.split(keyval_separator)
                    key = pair_list[0].lstrip()
                    val = pair_list[1].lstrip()
                    atoms[key] = val
            except:
                print 'got exception, pair is:', pair
                print 'field_separator is [{}]'.format(field_separator)
                print 'keyval_separator is [{}]'.format(keyval_separator)
                return None
            meta_data = self.device_metadata[device_name]

            for key in self.device_meta_data_field_names:
                contents[key] = meta_data[key]
            contents['timestamp'] = time.time()
            contents['atoms'] = atoms

            return json.dumps(contents)
        except:
            raise

    def haus_api_put(self):
        pass

    def haus_api_get(self):
        pass

    def read_raw(self, name, port, begin_of_line='$', end_of_line='#', delim=',', key_val_split = '=', timeout = 1):
        #### Should change empty readline to a timeout method.
        ### Method broken! Byte read in is not comparable using =.
        ### VAL acts as a token to know whether the next bytes string is a key or value in the serialized form###
        ## based on continuos bytes with no newline return##
        # The start of line for this test is the '$' for username, and the EOL is '#' #
        start_time = time.time()
        if not port.isOpen():
            port.open()
        current = port.read()
        while current != begin_of_line:
            print "Looking for {} but found {}".format(begin_of_line,current)
            current = port.read()
            if time.time() - start_time > timeout: return
        VAL = False
        atoms = {}
        contents = {}
        reading = True
        status = True
        empty_read_count = 0
        current_key = ''
        current_value = ''
        try:
            while reading:
                current_char_in = port.read()
                if current_char_in == '':
                    status = False
                    empty_read_count += 1
                elif current_char_in == end_of_line:
                    ## IE we are getting data but end of line ##
                    status = True
                    reading = False
                    atoms[current_key] = current_value
                elif current_char_in == delim:
                    ## There is a new set of key value pairs ##
                    atoms[current_key] = current_value
                    current_value = ''
                    current_key = ''
                    status = True
                    VAL = not VAL
                elif current_char_in == '=':
                    status = True
                    VAL = not VAL
                else:
                    status = True
                    if VAL:
                        current_value += current_char_in
                    else:
                        current_key += current_char_in
        except:
            print "Didn't read"
        print "Read status: ", status
        # if empty_read_count <= empty_read_limit:
        meta_data = self.device_metadata[name]
        for key in self.device_meta_data_field_names:
            contents[key] = meta_data[key]
        contents['timestamp'] = time.time()
        contents['atoms'] = atoms

        return json.dumps(contents)

    def virtual_connections(self, group_mode):
        """ ubuntu (in a vbox) does not alter the /dev dynamically """
        answer = raw_input("Would you like to set up devices? (y/n)")
        if (answer.lower()[0] != 'y'):
            return None

        username = "Charles" or raw_input("What is the account username for all your devices?: ")
        access_key = "Gust" or raw_input("What is the access key?: ")
        timezone = "LA" or raw_input("What is your current timezone?: ")

        while raw_input("Would you like to set up a device? (y/n)").startswith('y'):
            device_name = "LoveMeter" or raw_input("What would you like to call the device?")
            new_dev = "/dev/ttyS1" or raw_input("What is the path to {}? ".format(device_name))
            device_type = "monitor" or raw_input("Is {} a 'controller' or a 'monitor'?: ".format(device_name))
            baud_rate = "9600" or raw_input("The default Baud rate is 9600. Set it now if you like, else hit enter: ")
            timestamp = time.time()

            device_data = []
            device_data.append(device_name)
            device_data.append(device_type)
            device_data.append(username)
            device_data.append(access_key)
            device_data.append(timezone)
            device_data.append(timestamp)

            metadata = dict(zip(self.device_meta_data_field_names, device_data))
            self.device_metadata[device_name] = metadata

            last_port = new_dev
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
            print("Device {} at {} is registered!".format(device_name, new_dev))

        current_connections = self.named_connections
        return current_connections

    def run_setup(self, group_mode = False):
        num_devices = len(_serial_ports())

        if (sys.platform.startswith('linux2') and (num_devices == 1) and
            (_serial_ports()[0].startswith('/dev/ttyS1'))):
            return self.virtual_connections(group_mode)

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
                answer = raw_input('Plug all your devices in now to continue, then hit enter:')
                num_devices = len(_serial_ports())
                answer = int(raw_input('Found {} devices, how many devices do you want to name? (1-n): '.format(num_devices)))
                username = raw_input("What is the account username for all your devices?: ")
                access_key = raw_input("What is the access key?: ")
                timezone = raw_input("What is your current timezone?: ")
                print "Unplug them now to continue..."
                ### Take number of devices connected initially and subtract devices to program ###
                starting = num_devices - answer
                while len(_serial_ports()) > (starting):
                    time.sleep(1)
                device_meta_data_field_names = ('device_name', 'device_type', 'username', 'access_key', 'timezone', 'timestamp')
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

                    if last_device_connected.isOpen():
                        last_device_connected.close()

                    self.named_connections[device_name] = last_device_connected
                    current_number += 1
                current_connections = self.named_connections
                return current_connections


def _serial_ports():
    """Lists serial ports
    :raises EnvironmentError:
    On unsupported or unknown platforms
    :returns:
    A list of available serial ports
    """
    if sys.platform.startswith('win'):
        ports = ['COM' + str(i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        ports = glob.glob('/dev/ttyACM*')
        if len(ports) == 0:
            # on ubuntu with virtual connections
            ports = ['/dev/ttyS1']
    elif sys.platform.startswith('darwin'):
        ### the second glob is for the xbee
        ports = glob.glob('/dev/tty.usbmodem*') + glob.glob('/dev/tty.usbserial*')
    else:
        raise EnvironmentError('Unsupported platform')
    return ports
