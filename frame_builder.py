import sys, queue #, configparser

from log import LogAgent, init
from time import sleep

def b_sizeof(b: bytes) -> int:
    return sys.getsizeof(b) - sys.getsizeof(bytes('', 'utf-8'))

def loop(input_channel, output_channel, com_channel, log_channel):
    logger = LogAgent(log_channel, 'FRAMER ')
    config = init()
    work_bytes = b''
    retry = 0
    max_retry = int(config['uart']['max_retry'])
    retry_time = float(config['uart']['retry_time'])
    USE_PICP = config.getboolean('uart', 'USE_PICP')
    state = 'WORK'
    if not USE_PICP:
        frame_size = int(config['uart']['frame_size'])
    else:
        frame_size = 29

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
                    return

                case _:
                    logger.log('ERROR', f'Unrecognised command {msg} on COM channel!')

        # wait until new input appears or state changes
        if state == 'WAIT' or (input_channel.empty() and not retry and work_bytes == b''):
            sleep(retry_time)
            continue

        logger.log('TRACE', f'SLEEPER CONDITION FOR THE LOOP: \n'
                                          f'\t\tinput channel: {'empty' if input_channel.empty() else 'full' }\n'
                                          f'\t\tretry: {retry}\n'
                                          f'\t\twork_bytes: {work_bytes}\n')

        try:
            input_string = input_channel.get(timeout=0.5)
            work_bytes += bytes(input_string, 'utf-8')
            input_channel.task_done()
        except queue.Empty:
            pass

        if len(work_bytes) < frame_size and retry < max_retry:
            logger.log('TRACE', f'Work bytes too short, retrying {retry}...')
            retry += 1
            continue
        retry = 0

        logger.log('TRACE', '\n'
              f'\t\tExtracting from: {work_bytes}\n'
              f'\t\tExtracting {frame_size} bytes\n'
              f'\t\tExtracting {work_bytes[:frame_size]}')


        frame_bytes = work_bytes[:frame_size]
        work_bytes = work_bytes[len(frame_bytes):]

        if not USE_PICP:
            output_channel.put(frame_bytes)
            continue
        # else:
        """
            TODO:
            PICP frame building implementation
        """


