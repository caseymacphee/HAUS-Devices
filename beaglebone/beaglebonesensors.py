from __future__ import unicode_literals
import Adafruit_BBIO.GPIO as GPIO
import gevent


class DeviceConnection(object):
    """All common device behavior, subclass this for specific device types"""
    boot_time = 1  # Override this in specific subclasses

    def setup(self):
        pass

    def cleanup(self):
        GPIO.cleanup()

    def __enter__(self):
        self.setup()
        gevent.sleep(self.boot_time)  # Wait for sensor to come online
        return self

    def __exit__(self, type, value, traceback):
        self.cleanup()
        return False  # Don't suppress any errors


class PolledDigitalIODeviceConnection(DeviceConnection):
    """Connection to a device that needs to be turned on before a reading,
    i.e., "Polled", and uses 2 digital IO pins (output & input)"""
    def __init__(self, power_pin="P8_7",
                 digital_in_pin="P8_9"):
        self.power_pin = power_pin
        self.digital_in_pin = digital_in_pin

    def setup(self):
        # Turn on power
        GPIO.setup(self.power_pin, GPIO.OUT)
        GPIO.setup(self.digital_in_pin, GPIO.IN)
        GPIO.output(self.power_pin, GPIO.HIGH)

    def read_state(self):
        return GPIO.input(self.digital_in_pin)
