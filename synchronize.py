# This is a function that looks like a decorator but used by AutoSynchronized to
# inject a _auto_lock member on every instance of a class that uses our metaclass.
# This way we don't have to think about locking on methods.
from threading import Lock
import sys
import glob

def wrap_init_with_lock(org_init):
    def wrapped_init(self, *args, **kwargs):
       org_init(self, *args, **kwargs)
       ports = devices._serial_ports()
       serial_locks = {}
       for serial in ports:
            serial_locks[serial] = Lock()
            serial_locks.append(serial_locks)
       self._auto_locks_for_ports = serial_locks
    return wrapped_init

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

class Allocate_port_locks(type):
    """
    This is a metaclass, a class describing how classes should be built. This
    new metaclass wraps the init method with a new version that will add a lock
    object to self.

    It then provides a hook so that calling a method and prepending 'synchronized_'
    to the method name will obtain the injected lock before calling the method and 
    release it when leaving the method. No further work is required other than calling
    the method.
    """
    def __init__(cls, name, bases, namespaces):
        super(type, cls).__init__(name, bases, namespaces)
        cls.__init__ = wrap_init_with_lock(cls.__init__)
