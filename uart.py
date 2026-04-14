from log import log
from time import sleep

def loop(frame_channel, com_channel, log_channel):
    source = 'UART   '
    while True:
        if not com_channel.empty():
            msg = com_channel.get()

            match msg:
                case 'STOP':
                    log(log_channel, 'INFO', source, 'Received STOP - shutting down.')
                    return

                case _:
                    log(log_channel, 'ERROR', source, 'Unrecognised command on COM channel!')


        if frame_channel.empty():
            # just sleep for a bit to avoid eating the processor time
            sleep(0.25)
            continue

        frame = frame_channel.get()
        print(frame)