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
import requests
import getpass
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
    url = "http://ec2-54-148-194-170.us-west-2.compute.amazonaws.com"  # Update this as needed
    primary_key_owners = {}  # {port : [(device_id, username, device_name)]}
    def __init__(self):
        self.send_attempt_number = 0
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
            'timestamp')

    def stream_forever(self, read = 'A', poll = 'S'):
        inf = float("inf")
        monitor_threads = []
        controller_threads = []
        try:
            for name in self.monitors:
                thread = threading.Thread(target=self.read_monitor_continuously, args = (name, inf, read))
                thread.daemon = True
                thread.start()
                monitor_threads.append(thread)
     
            for name in self.controllers:
                thread = threading.Thread(target=self.sync_controller_continuously, args = (name, inf, poll))
                thread.daemon = True
                thread.start()
                controller_threads.append(thread)
        except:
            for thread in monitor_threads:
                thread.join()
            for thread in controller_threads:
                thread.join()

    def pickup_conn(self):
        serial_paths = _serial_ports()
        serial_list = []
        for port in serial_paths:
            connection = serial.serial_for_url(port, timeout = 5)
            serial_list.append(connection)
        self.serial_connections = serial_list
        return serial_list

    def read_monitor_continuously(self, name, timeout=30, frequency = 'A'):
        start = time.time()
        current_time = start
        port_lock = self.device_locks[name]
        port = self.named_connections[name]
        with port_lock:
            while (current_time - start) < timeout:
                ### frequency logic goes here
                if frequency == 'A':
                    data_dict = self.read_raw(name)
                    self._send_to_server(data_dict)
                    current_time = time.time()
                elif frequency == 'M':
                    minute_average_dict = self.log_data(name, 60)
                    self._send_to_server(minute_average_dict)
                elif frequency == 'T':
                    ## same for ten minutes ##
                    ten_min_average_dict = self.log_data(name, 600)
                    self._send_to_server(ten_min_average_dict)
                elif frequency == 'H':
                    hour_average_dict = self.log_data(name, 3600)
                    self._send_to_server(hour_average_dict)

                current_time = time.time()

    
    def log_data(self, name, timeout):
        ### Please note that the reported timestamp on averaged data is also and average value.
        logs = []
        start = time.time()
        current_time = start
        data_gathered = 0
        while current_time - start < timeout:
            print "Gathering data...got {} records so far.".format(data_gathered)
            current_data = self.read_raw(name)
            logs.append(current_data)
            data_gathered += 1
            current_time = time.time()  
        average_data = {}
        for log in logs:
            for key, val in log['atoms'].iteritems():
                if is_number(val):
                    try:
                        average_data[key] = float(average_data[key]) + float(val)
                    except:
                        average_data[key] = val
                else:
                    ### If it's not a number, the last value is reported
                    average_data[key] = val
        for key, summed_data in average_data.iteritems():
            if is_number(summed_data):
                average_data[key] = float(summed_data) / len(logs)
        log['atoms'] = average_data
        return log

    def _ensure_port_is_open(self, port):
        if not port.isOpen():
            port.open()
            port.write('Okay')
            print "opened the port"
        return

    def _send_to_server(self, jsonmessage):
        try:
            self.send_attempt_number += 1
            payload = {}
            payload['timestamp'] = jsonmessage['timestamp']
            payload['atoms'] = jsonmessage['atoms']
            dev_id = self.device_metadata[jsonmessage['device_name']]['device_id']
            device_address = "%s/devices/%d/" % (self.url, dev_id)
            response = self.session.post(device_address, json=payload)
            print "Api receipt: "
            print response.status_code
            if response.status_code == 500:
                import io
                with io.open('error.html', 'wb') as errorfile:
                    errorfile.write(response.content)
            else:
                print response.content
        except:
            print "didn't have enough content to send"

    def sync_controller_continuously(self, name, timeout = 30, frequency = 'A'):
        start = time.time()
        current_time = start
        port_lock = self.device_locks[name]
        with port_lock:
            while (current_time - start) < timeout:
                if frequency == 'A':
                    self._sync_controller_states(name)
                elif frequency == 'S':
                    start_time = time.time()
                    freq = 10
                    self._sync_controller_states(name)
                    current = time.time()
                    while current - current_time < freq:
                        time.sleep(1)
                        current = time.time()
                elif frequency == 'M':
                    start_time = time.time()
                    freq = 60
                    self._sync_controller_states(name)
                    current = time.time()
                    while current - current_time < freq:
                        time.sleep(1)
                        current = time.time()
                elif frequency == 'T':
                    start_time = time.time()
                    freq = 600
                    self._sync_controller_states(name)
                    current = time.time()
                    while current - current_time < freq:
                        time.sleep(1)
                        current = time.time()
                current_time = time.time()

    def _sync_controller_states(self, name):
        dev_id = self.device_metadata[name]['device_id']
        device_address = "%s/devices/%d/current/" % (self.url, dev_id)
        response = self.session.get(device_address)
        if response.status_code != 200:
            print "Something went wrong when contacting the server"
            return
        response_dict = json.loads(response.content)
        desired_states = {}
        for atom in response_dict:
            if 'atom_name' in atom:
                desired_states[atom['atom_name']] = atom['value']
        # print desired_states
        
        response = self.talk_to_controller(name, desired_states)
        device_address = "%s/devices/%d/" % (self.url, dev_id)
        response = self.session.post(device_address, json=response)
        print response

    def ping_controller_state(self, name):
        port = self.named_connections[name]
        self._ensure_port_is_open(port)
        port.write('$')
        dictionary = self.read_raw(name)
        return dictionary

    def talk_to_controller(self, name, desired_state):
        """
Use method like this:
for name, port in me.controllers.iteritems():
    me.talk_to_controller(name, port, 'Relay1', '1')

Relay's must have an '@' before them.
        """
        port = self.named_connections[name]
        state_dict = None
        start_time = time.time()
        current_state = self.ping_controller_state(name)['atoms']
        # print current_state
        for key, val in current_state.iteritems():
            if key[0] == '@':
                relay_name, relay_number = key.split('_')
                if int(val) != int(float(desired_state[key])):
                    # print "current = ", val, " desired = ", desired_state[key]
                    port.write(str(relay_number))
        port.write('$')
        state_dict = self.read_raw(name)
        # print 'method took :', int(time.time() - start_time), ' seconds'
        return state_dict

    # CMGTODO: without memorized decorator, setup dictionary if seen before
    def _delimiter_factory(self, message, device_name):
        if device_name in self.delimiters:
            return self.delimiters[device_name]

        field_separator = {[',', ';', '\n']}
        keyval_separator = {[':', '=']}
        in_single_quote = False
        in_double_quote = False
        index = 0
        maxlen = len(message)

        while (index < maxlen) and (
              (len(field_separator) > 1) or (len(keyval_separator) > 1)):
            c = message[index]
            if (c == '"') and (not in_single_quote):
                in_double_quote = not in_double_quote
            elif (c == "'") and (not in_double_quote):
                in_single_quote = not in_single_quote
            elif in_single_quote or in_double_quote:
                # if in a quoted string, don't check for separators
                pass
            elif (c in keyval_separator):
                keyval_separator = c
            elif (c in field_separator):
                field_separator = c
            index += 1

        self.delimiters[device_name] = [field_separator, keyval_separator]
        print "In factory: {} has field_separator[{}], keyval_separator[{}]".format(
            device_name,
            field_separator,
            keyval_separator)
        print "Original message: [{}]".format(message)

        return field_separator, keyval_separator
    
    def read_raw(self, name, timeout = 5):
        """ return dictionary representation of parsed line from port """
       
        # We can start our data structure with any key value pair. A key value pair
        #  starts after a field_separator (comma or semi-colon), or after a new-line
        #  Apparently, there are also some scenarios where this could occur after a
        #  dollar sign. So, if you see any four of these characters, you are probably
        #  just about to start a key value pair. Well, as long as none of these
        #  characters occur in strings.
        # If the string is already read, a potentially slower but more robust
        #  way to read is to use the split and strip methods on the entire line
        key_value_start_set = {b'\n', b',', b';', b'$'}
        fieldsep = {b',', b';', b'\n', b'\r', b'#'}
        keysep = {b':', b'='}
        whitespace_set = {b' ', b'\t'}
        if self.delimiters:
            if self.delimiters[0]:
                fieldsep = self.delimiters[0] + {b'\n', b'#'}
            if self.delimiters[1]:
                keysep = self.delimiters[1]

        atoms = {}
        contents = {}
        start_time = time.time()
        port = self.named_connections[name]
        current = port.read()
        # while current not in key_value_start_set:
        while current not in key_value_start_set:
            current = port.read()
            if time.time() - start_time > timeout: return

        done = False
        while not done:
            current_key = ''
            current_value = ''

            c = port.read()
            while c in whitespace_set:
                c = port.read()

            while c not in keysep:
                current_key += c
                c = port.read()

            c = port.read()
            while c in whitespace_set:
                c = port.read()

            while c not in fieldsep:
                current_value += c
                c = port.read()

            atoms[current_key] = current_value

            # either of these mark the EOL
            done = c in {b'\n', b'#', b'\r'}

        # if empty_read_count <= empty_read_limit:
        meta_data = self.device_metadata[name]

        for key in self.device_meta_data_field_names:
            contents[key] = meta_data[key]
        contents['timestamp'] = time.time()
        contents['atoms'] = atoms

        return contents

    def virtual_connections(self, group_mode):
        """ ubuntu (in a vbox) does not alter the /dev dynamically """
        answer = raw_input("Would you like to set up devices? (y/n)")
        if (answer.lower()[0] != 'y'):
            return None

        # CMGTODO: remove constant values from front of 'or'
        username = "Charles" or raw_input("What is the account username for all your devices?: ")
        # access_key = "Gust" or raw_input("What is the access key?: ")
        
        while raw_input("Would you like to set up a device? (y/n)").startswith('y'):
            debug_only_device_select = int(raw_input("Are you setting up (1) LoveMeter, (2) ServoMood, or (3) Other?: "))

            if debug_only_device_select == 1:
                device_name = "LoveMeter"
                new_dev = "/dev/ttyS1"
                device_type = "monitor"
                baud_rate = "9600"

            if debug_only_device_select == 2:
                device_name = "ServoMood"
                new_dev = "/dev/ttyS1"
                device_type = "controller"
                baud_rate = "9600"

            if debug_only_device_select == 3:
                device_name = raw_input("What would you like to call the device?")
                new_dev = raw_input("What is the path to {}? ".format(device_name))
                device_type = raw_input("Is {} a 'controller' or a 'monitor'?: ".format(device_name))
                baud_rate = raw_input("The default Baud rate is 9600. Set it now if you like, else hit enter: ")


            timestamp = time.time()

            device_data = []
            device_data.append(device_name)
            device_data.append(device_type)
            device_data.append(username)
            # device_data.append(access_key)
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
There are {} visible serial ports.
If you would like to run through the device
setup (which will require you unplugging your
devices, and naming them one by one as they
connect. Enter 'quit' or 'continue': """.format(num_devices)
        answer = raw_input(setup_instructions)
        if answer[0] == 'q' :
            pass
        if answer[0] == 'c':
            num_devices = len(_serial_ports())
            answer = int(raw_input('Found {} devices, how many devices do you want to name? (1-n): '.format(num_devices)))
            username = raw_input("What is the account username for all your devices?: ")
            password = getpass.getpass("Enter your password: ")
            self.session = requests.Session()
            self.session.auth = (username, password)
            response = self.session.get('%s/devices' % self.url)
            if response.status_code == 200:
                devices = json.loads(response.content)
                print "Your known devices: %s" % \
                    ", ".join([device['device_name'] for device in devices])
            else:
                print "HTTP Error retrieving devices: ", response.status_code
            print "Unplug them now to continue..."
            ### Take number of devices connected initially and subtract devices to program ###
            starting = num_devices - answer
            while len(_serial_ports()) > (starting):
                time.sleep(1)
            current_number = 1
            for devices in xrange(answer):
                current_ports = _serial_ports()
                print "Now plug in device {}...".format(current_number)
                while len(current_ports) < current_number + starting:
                    time.sleep(1)
                    current_ports = _serial_ports()
                metadata = {}
                last_port = current_ports.pop()
                # Add logic for permissions here
                known_id = -99
                if last_port in User.primary_key_owners:  # Maybe put last_port in primary_key_owners and do this automatically
                    print "A device can only have one owner, if you'd like to share data you can do so from the device owner's dashboard."
                    print "Alternatively you may have hit this break-out if you accidentally swapped devices on a usb which is not supported."
                    print "Try again"
                    break
                device_name = raw_input("What would you like to call device {}?: ".format(current_number))
                device_type = raw_input("Is this device a 'controller' or a 'monitor'?: ")
                baud_rate = raw_input("The default Baud rate is 9600. Set it now if you like, else hit enter: ")
                timestamp = 'timestamp'

                try:
                    self.device_locks[device_name] = self.serial_locks[last_port]
                except KeyError:
                    self.serial_locks[last_port] = Lock()
                    self.device_locks[device_name] = self.serial_locks[last_port]
                
                device_data = []
                device_data.append(device_name)
                device_data.append(device_type)
                device_data.append(username)
                # device_data.append(device_id)

                device_data.append(timestamp)
                metadata = dict(zip(self.device_meta_data_field_names, device_data))
                self.device_metadata[device_name] = metadata
                
                if sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
                    last_device_connected = self.pickup_conn()[0]
                else:
                    last_device_connected = self.pickup_conn()[-1]
                
                self.named_connections[device_name] = last_device_connected
                self._ensure_port_is_open(last_device_connected)
                ### This is Arduino protocol ###
                last_device_connected.write('Okay')
                response = last_device_connected.readline()
                ######
                if device_type == 'monitor':
                    atoms = self.read_raw(device_name)['atoms']
                    if atoms is None:
                        print "Read nothing from the monitor."
                        break
                    atom_identifiers = [name for name in atoms]
                else:
                    atoms = self.ping_controller_state(device_name)['atoms']
                    atom_identifiers = [name for name in atoms]
                payload = {'device_name': device_name, 'device_type': device_type, 'atoms': atom_identifiers}
                if known_id != -99:
                    payload['device_id'] = known_id
                response = self.session.post('%s/devices' % self.url,
                                         data=payload)

                # JBB: Make this handle server errors gracefully
                if response.status_code in (201, 202):
                    print "Device registered with server"
                else:
                    print "Problem registering device: HTTPError ",\
                        response.status_code

                response = json.loads(response.content)
                device_id = response['id']
                if device_id in User.primary_key_owners:
                    User.primary_key_owners[last_port].append((device_id, username, device_name))
                else:
                    User.primary_key_owners[last_port] = [(device_id, username, device_name)]
                self.device_metadata[device_name]['device_id'] = device_id
                
                if device_type == 'controller':
                    response = self.ping_controller_state(device_name)
                    device_address = "%s/devices/%d/" % (self.url, device_id)
                    response = self.session.post(device_address, json=response)

                if baud_rate != '':
                    try:
                        last_device_connected.baud_rate = int(baud_rate)
                    except:
                        raise Exception('Could not set that baud rate, check your input and try again.')
                
                if device_type == 'controller':
                    self.controllers[device_name] = last_device_connected
                elif device_type == 'monitor':
                    self.monitors[device_name] = last_device_connected
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
        ### The second is for xbee port ###
        ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
        ###This cannot go here.
        # if len(ports) == 0:
        #     # on ubuntu with virtual connections
        #     ports = ['/dev/ttyS1']
    elif sys.platform.startswith('darwin'):
        ### the second glob is for the xbee
        ports = glob.glob('/dev/tty.usbmodem*') + glob.glob('/dev/tty.usbserial*')
    else:
        raise EnvironmentError('Unsupported platform')
    return ports

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
