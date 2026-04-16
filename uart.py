# requires pyserial package
import serial
from log import LogAgent, init
from time import sleep

def loop(frame_channel, com_channel, log_channel):
    ########
    # INIT #
    ########

    config = init()
    logger = LogAgent(log_channel, 'UART   ')
    USE_PICP = config.getboolean('uart', 'use_picp')
    com = None
    # Serial init
    try:
        com = serial.Serial(config['uart']['COM_port'], 115200, timeout=1)
        if not com.is_open:
            raise serial.serialutil.SerialException()
        logger.log('INFO', f'Opened serial port {config['uart']['COM_port']}.')
    except:
        logger.log('ERROR', 'Could not open serial port.')

    ##################
    # MAIN UART LOOP #
    ##################
    while True:
        if not com_channel.empty():
            msg = com_channel.get()

            match msg:
                case 'STOP':
                    logger.log('INFO', 'Received STOP - shutting down.')
                    if com.is_open:
                        com.close()
                    return

                case _:
                    logger.log('ERROR', 'Unrecognised command on COM channel!')


        if frame_channel.empty():
            # just sleep for a bit to avoid eating the processor time
            sleep(0.25)
            continue

        if not USE_PICP:
            frame = frame_channel.get()
            logger.log('TRACE', f'Received frame from FRAMEBUILDER: {frame}.')
            if com.is_open:
                com.write(frame)
            continue
