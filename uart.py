from log import LogAgent
from time import sleep

def loop(frame_channel, com_channel, log_channel):
    logger = LogAgent(log_channel, 'UART   ')
    while True:
        if not com_channel.empty():
            msg = com_channel.get()

            match msg:
                case 'STOP':
                    logger.log('INFO', 'Received STOP - shutting down.')
                    return

                case _:
                    logger.log('ERROR', 'Unrecognised command on COM channel!')


        if frame_channel.empty():
            # just sleep for a bit to avoid eating the processor time
            sleep(0.25)
            continue

        frame = frame_channel.get()
        print(frame)