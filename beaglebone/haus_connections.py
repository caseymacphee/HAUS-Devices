from __future__ import unicode_literals
import requests
import json


class HausAccount(object):
    """Device-side representation of information on the HAUS website and
    interface with the server"""
    # just device ids for now, probably need to keep track of atoms, too
    def __init__(self, url, username, password):
        self.url = url
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.device_ids = {}

    def get_devices_from_server(self):
        response = self.session.get('%s/devices/' % self.url)
        if response.status_code != 200:
            raise IOError("Problem retrieving devices from server")
        device_data = json.loads(response.content)
        self.device_ids = {d['device_name']: d['id'] for d in device_data}

    def create_device_on_server(self, device_name, dev_type, dev_id=None):
        """Set up device_name on the server"""
        payload = {}
        if dev_id is not None:
            payload['id'] = dev_id

        payload['device_name'] = device_name
        payload['device_type'] = dev_type
        payload['atoms'] = []
        response = self.session.post('%s/devices/' % self.url,
                                     data=payload)

        if response.status_code not in (201, 202):
            raise IOError("Problem registering device: HTTPError %s" %
                          response.status_code)

        registered_device_id = json.loads(response.content)['id']
        self.device_ids[device_name] = registered_device_id

    def send_data_to_server(self, device_name, data):
        """This object must know about the device_name: either
        create_device_on_server() should be run, or get_devices_from_server()
        if you are certain it already exists.
        data should be of the form
        {"timestamp" "0.000",
         "atoms": {"atom1": "value1", "atom2": "value2", ...}
        }"""
        device_address = "%s/devices/%s/" % \
            (self.url, self.device_ids[device_name])
        response = self.session.post(device_address, json=data)
        if response.status_code != 202:
            raise IOError("Problem posting data to device %s: HTTPError %s" %
                          (device_name, response.status_code))
