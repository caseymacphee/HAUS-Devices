import devices

def mainprompt():
    response = raw_input("Pick what you'd like to do:\n{}\n{}\n{}\n{}\n:".format('test devices', 'stream forever', 'operate controllers', 'print monitors'))
    if response == 'test devices':
        pass
    elif response == 'stream forever':
        pass
    elif response == 'operate controllers':
        pass
    elif response == 'print monitors':
        pass

def main():
    response = raw_input("Would you like 'single', or 'multi' user set-up?: ")
    users = []
    if response == 'single':
        me = devices.User()
        me.run_setup()
        users.append(me)
    elif response == 'multi':
        num_users = raw_input("How many users?: ")
        for user in xrange(int(num_users)):
            new_user = devices.User()
            new_user.run_setup()
            users.append(new_user)
    mainprompt()

if __name__ == '__main__':
    main()
