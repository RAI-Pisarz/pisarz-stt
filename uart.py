def loop(thread_comms, main_comms):
    while True:
        if not main_comms.empty() and main_comms.get() == 'STOP':
            print('Goodnight')
            main_comms.put('STOP')
            main_comms.task_done()
            return



def strip(msg):
    """Prepare text for further communication"""
    msg = msg.split(':')
    return msg