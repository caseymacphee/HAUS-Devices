#Test for monitor and controller
##Relay
import devices
me = devices.User()
me.run_setup()
for name in me.monitors:
    print "Gathering data as soon as possible"
    me.read_monitors_continuously(name, 60, 'A')
    print "Gathering data minutely"
    me.read_monitors_continuously(name, 60, 'M')
    print "Gathering data every 10 minutes"
    me.read_monitors_continuously(name, 600, 'T')
    print "Gathering data hourly"
    # me.read_monitors_continuously(name, 3600, 'H')



##Controller
import devices
you = devices.User()
you.run_setup()

def set_state(states, atoms):
    for key, val in atoms.iteritems():
        relay, num = key.split('_')
        if num == '1':
            atoms[key] = states[0]
        elif num == '2':
            atoms[key] = states[1]
        elif num == '3':
            atoms[key] = states[2]
        elif num == '4':
            atoms[key] = states[3]
    return atoms

for name in you.controllers:
    states = [0,0,0,0]
    for index, state in enumerate(states):
        states[index] = 1
        dictionary = you.ping_controller_state(name)
        atoms = dictionary['atoms']
        dictionary['atoms'] = set_state(states, atoms)
        you.talk_to_controller(dictionary)
        states[index] = 0
        states = [0,0,0,0]
    for index in reversed(xrange(len(states))):
        states[index] = 1
        dictionary = you.ping_controller_state(name)
        atoms = dictionary['atoms']
        dictionary['atoms'] = set_state(states, atoms)
        you.talk_to_controller(dictionary)
        states[index] = 0
        states = [1,1,1,1]
    for index, state in enumerate(states):
        states[index] = 0
        dictionary = you.ping_controller_state(name)
        atoms = dictionary['atoms']
        dictionary['atoms'] = set_state(states, atoms)
        you.talk_to_controller(dictionary)
        states[index] = 1
        states = [1,1,1,1]
    for index, state in enumerate(states):
        states[index] = 0
        dictionary = you.ping_controller_state(name)
        atoms = dictionary['atoms']
        dictionary['atoms'] = set_state(states, atoms)
        you.talk_to_controller(dictionary)
        states[index] = 1
        states = [1,1,1,1]
    for index in reversed(xrange(len(states))):
        states[index] = 0
        dictionary = you.ping_controller_state(name)
        atoms = dictionary['atoms']
        dictionary['atoms'] = set_state(states, atoms)
        you.talk_to_controller(dictionary)
        states[index] = 1
    states = [0,0,0,0]
    dictionary = you.ping_controller_state(name)
    atoms = dictionary['atoms']
    dictionary['atoms'] = set_state(states, atoms)
    you.talk_to_controller(dictionary)
    states = [1,1,1,1]
    dictionary = you.ping_controller_state(name)
    atoms = dictionary['atoms']
    dictionary['atoms'] = set_state(states, atoms)
    you.talk_to_controller(dictionary)
    states = [0,0,0,0]
    dictionary = you.ping_controller_state(name)
    atoms = dictionary['atoms']
    dictionary['atoms'] = set_state(states, atoms)
    you.talk_to_controller(dictionary)
    states = [1,1,1,1]
    dictionary = you.ping_controller_state(name)
    atoms = dictionary['atoms']
    dictionary['atoms'] = set_state(states, atoms)
    you.talk_to_controller(dictionary)
    states = [0,0,0,0]
    dictionary = you.ping_controller_state(name)
    atoms = dictionary['atoms']
    dictionary['atoms'] = set_state(states, atoms)
    you.talk_to_controller(dictionary)
    states = [1,1,1,1]
    dictionary = you.ping_controller_state(name)
    atoms = dictionary['atoms']
    dictionary['atoms'] = set_state(states, atoms)
    you.talk_to_controller(dictionary)


