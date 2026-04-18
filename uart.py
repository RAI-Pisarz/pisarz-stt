# requires pyserial package
import serial as s
from log import LogAgent, init
from time import sleep

def connect(logger, config):
    try:
        serial = s.Serial(config['uart']['COM_port'], 115200, timeout=1)
        if not serial.is_open:
            raise s.serialutil.SerialException()
        logger.log('INFO', f'Opened serial port {config['uart']['COM_port']}.')
    except:
        logger.log('ERROR', 'Could not open serial port.')
        serial = type('serial_closed', (object,), {'is_open': False})

    return serial

def loop(frame_channel, com_channel, log_channel):
    ########
    # INIT #
    ########

    config = init()
    logger = LogAgent(log_channel, 'UART   ')
    state = 'WORK'
    USE_PICP = config.getboolean('uart', 'use_picp')

    # Serial init
    serial = connect(logger, config)

    ##################
    # MAIN UART LOOP #
    ##################
    while True:
        if not com_channel.empty():
            msg = com_channel.get()

            match msg:
                case 'WAIT':
                    logger.log('INFO', 'Received WAIT - halting work.')
                    state = 'WAIT'

                case 'RESUME':
                    logger.log('INFO', 'Received RESUME - resuming work.')
                    state = 'WORK'

                case 'GET STATE':
                    logger.log('TRACE', 'Received GET STATE.')
                    logger.log('INFO', f'Current state: {state}')

                case 'STOP':
                    logger.log('INFO', 'Received STOP - shutting down.')
                    if serial.is_open:
                        serial.close()
                    return

                case _:
                    logger.log('ERROR', 'Unrecognised command on COM channel!')


        if frame_channel.empty() or state == 'WAIT':
            # just sleep for a bit to avoid eating the processor time
            sleep(0.25)
            continue

        if not USE_PICP:
            frame = frame_channel.get()
            logger.log('TRACE', f'Received frame from FRAMEBUILDER: {frame}.')
            if serial.is_open:
                serial.write(frame)
            continue
