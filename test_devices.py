import pytest
import devices
import io
import time

def test_connections():
    boards = devices.Devices()
    boards = boards.pickup_conn()
    uri = boards[1]
    rachel = boards[0]
    assert not uri.isOpen()
    assert not rachel.isOpen()
    uri.open()
    assert uri.isOpen()
    rachel.open()
    assert rachel.isOpen()
    rachel.flush()
    rachel.readline()
    rachel.close()
    assert not rachel.isOpen()
    uri.flush()
    uri.close()
    assert not uri.isOpen()

def test_message(devices):
    while True:
        for name, device in devices.labeled_connections.iteritems():
            if not device.isOpen():
                device.open()
            # device_wrapper = io.TextIOWrapper(io.BufferedRWPair(device, device))
            # device_wrapper.flush()
            if name == 'uri':
                input = device.readline()
            else:
                input = device.read()
                device.flush()
                device.write('1\r\n')
            # device.flush()
            print len(input)
            input = input.rstrip()
            print devices.username, ":", name, ":", input
            device.close()
            time.sleep(10)
