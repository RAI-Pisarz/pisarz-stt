from log import log

def loop(frame_channel, com_channel, log_channel):
    source = 'UART'
    while True:
        if not com_channel.empty():
            msg = com_channel.get()

            match msg:
                case 'STOP':
                    print(f'{source} | INFO: Received STOP - shutting down.')
                    return

                case _:
                    log(log_channel, 'ERROR', source, 'Unrecognised command on COM channel!')

