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

class User(object):
    """
This function is the working head for Raphi. Currently processes based on regular expressesions of the
 /dev/yourarduinousbserialpathhere (from the scanportsmodule).
Returns a string with the serials that fit that specification in the form of a list of tuples (connection first, test buffer last).
The connection returns in it's open state .
    """
    _instances=[]
    serial_locks = {}
    url = "http://localhost:8000"  # Update this as needed

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

    def stream_forever(self):
        try:
            inf = float("inf")
            # controllers = threading.Thread(target=self.talk_to_controllers, args=(['',inf]))
            monitors = threading.Thread(target=self.read_monitors_to_json, args=([inf]))
            # controllers.daemon = True
            monitors.daemon = True
            # controllers.start()
            monitors.start()
        except:
            # controllers.join()
            monitors.join()

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

    def read_monitors_to_json(self, timeout = 30):
        ### listening for 30 second timeout for testing ###
        ### if you think your monitors are running slow, check for delays in your arduino sketch ###
        start = time.time()
        current_time = start

        while current_time - start < timeout:
            for name, port in self.monitors.iteritems():
                port_lock = self.device_locks[name]

                # if port_lock.locked:
                #     print 'locked'
                port_lock.acquire()
                if port_lock.locked():
                    print port_lock,' acquired'
                if not port.isOpen():
                    port.open()
                jsonmessage = self.read_raw(name, port)
                print jsonmessage
                self._send_to_server(jsonmessage)
                port.close()
                port_lock.release()
                if not port_lock.locked():
                    print port_lock, 'released'
                last_time = current_time
                current_time = time.time()
                print name,' took: ', int(current_time - last_time), 'seconds'

    def _send_to_server(self, jsonmessage):
        self.send_attempt_number += 1
        if (self.send_attempt_number % 60):  # not zero
            return
        payload = json.loads(jsonmessage)
        print "Here is where I'd put the following data: "
        print payload

    def talk_to_controller(self, name, port, target, message = '1'):
        """
Use method like this:
for name, port in me.controllers.iteritems():
    me.talk_to_controller(name, port, 'Relay1', '1')
        """

        jsonmessage = None
        start = time.time()
        current_time = start
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
        port.write(message)
        # self.read_raw(name, port)
        port.write('$')
        jsonmessage = self.read_raw(name, port)
        port.close()
        port_lock.release()
        if not port_lock.locked():
            print port_lock, 'released'
        last_time = current_time
        current_time = time.time()
        print 'method took :', int(current_time - last_time), ' seconds'
        return jsonmessage

    def _build_json(self, name, message, delim = ',', key_val_split = '='):
        try:
            message = message.rstrip()
            data_thread = {}
            key_val_pairs = message.split(delim)
            for pair in key_val_pairs:
                try:
                    key, val = pair.split(key_val_split)
                    data_thread[key] = val
                except:
                    print 'got exception, pair is:', pair
                    return None
            meta_data = self.device_metadata[name]
            data_thread['device_name'] = meta_data['device_name']
            data_thread['username'] = meta_data['username']
            data_thread['device_id'] = meta_data['device_id']
            data_thread['device_type'] = meta_data['device_type']
            data_thread['timezone'] = meta_data['timezone']
            data_thread['timestamp'] = time.time()
            return json.dumps(data_thread)
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
            current = port.read()
            if time.time() - start_time > timeout: return
        VAL = False
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
                    contents[current_key] = current_value
                elif current_char_in == delim:
                    ## There is a new set of key value pairs ##
                    contents[current_key] = current_value
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
        contents['device_name'] = meta_data['device_name']
        contents['username'] = meta_data['username']
        contents['device_id'] = meta_data['device_id']
        contents['device_type'] = meta_data['device_type']
        contents['timezone'] = meta_data['timezone']
        contents['timestamp'] = time.time()
        return json.dumps(contents)

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
                answer = raw_input('Plug all your devices in now to continue, then hit enter:')
                num_devices = len(_serial_ports())
                answer = int(raw_input('Found {} devices, how many devices do you want to name? (1-n): '.format(num_devices)))
                username = raw_input("What is the account username for all your devices?: ")
                username = raw_input("What is the account username for all your devices?: ")
                password = raw_input("Enter your password: ")
                timezone = raw_input("What is your current timezone?: ")
                self.session.auth = (username, password)
                response = self.session.get('%s/devices' % self.url)
                print "Your known devices: %s" % ", ".join[device['name']
                                    for device in json.loads(response.content)]
                print "Unplug them now to continue..."
                ### Take number of devices connected initially and subtract devices to program ###
                starting = num_devices - answer
                while len(_serial_ports()) > (starting):
                    time.sleep(1)
                device_meta_data_field_names = ('device_name', 'device_type', 'username', 'device_id', 'timezone', 'timestamp')
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
                    payload = {'name': device_name, 'device_type': device_type, 'serialpath': 0, 'user': 1}
                    response = self.session.post('%s/devices' % self.url,
                                                 data=payload)
                    response = json.loads(response.content)
                    device_id = response['id']
                    print response
                    device_data = []
                    device_data.append(device_name)
                    device_data.append(device_type)
                    device_data.append(username)
                    device_data.append(device_id)
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
    elif sys.platform.startswith('linux') or sys.platform.startswith('linux2') or sys.platform.startswith('cygwin'):
        ports = glob.glob('/dev/ttyACM*')
    elif sys.platform.startswith('darwin'):
        ### the second glob is for the xbee
        ports = glob.glob('/dev/tty.usbmodem*') + glob.glob('/dev/tty.usbserial*')
    else:
        raise EnvironmentError('Unsupported platform')
    return ports

if __name__ == '__main__':
    import devices
    charlie = devices.User()
    charlie.run_setup()
