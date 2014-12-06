from __future__ import unicode_literals
from beaglebonesensors import PolledDigitalIODeviceConnection
from haus_connections import HausAccount
import time
import os


def main():
    url = "http://ec2-54-148-194-170.us-west-2.compute.amazonaws.com"
    password = os.environ['HAUS_PASSWORD']
    jason_account = HausAccount(url, "jbbrokaw", password)
    device_name = "Beaglebone"
    dev_type = "monitor"
    with PolledDigitalIODeviceConnection() as hygrometer:
        data_point = hygrometer.read_state()

    print time.time(), data_point

    jason_account.get_devices_from_server()
    if device_name not in jason_account.device_ids:
        jason_account.create_device_on_server(device_name, dev_type)

    data = {"timestamp": time.time(),
            "atoms": {"Moisture Sensor": data_point}
            }

    jason_account.send_data_to_server(device_name, data)

if __name__ == '__main__':
    main()
