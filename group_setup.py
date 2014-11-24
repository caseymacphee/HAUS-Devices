import devices
from threading import Lock

def mainprompt(devices):
    choices = ('test devices', 'run forever', 'operate controllers', 'stream monitors')
    response = raw_input("Pick what you'd like to do:\n{}\n{}\n{}\n{}\n:".format(choices))
    if response == 'test devices':
        pass
    elif response == 'run forever':
        pass
    elif response == 'operate controllers':
        pass
    elif response == 'stream monitors':
        pass

def main():
    response = raw_input("Enter all the usb devices now, then hit enter...")
    boards = devices.Boards()
    mainprompt(boards)


if '__name__' == '__main__':
    main()