import sys
from log import log

def b_sizeof(b: bytes) -> int:
    return sys.getsizeof(b) - sys.getsizeof(bytes('', 'utf-8'))


def loop(input_channel, com_channel, log_channel):
    work_string = ''
    source = 'FRME'
    retry = 0

    while True:

        if not com_channel.empty():
            msg = com_channel.get()
            match msg:
                case 'STOP':
                    print(f'{source} | INFO: Received STOP - Shutting down.')
                    return

                case _:
                    log(log_channel, 'ERROR', source, 'Unrecognised command on COM channel!')

        # wait until new input appears
        if input_channel.empty():
            continue

        # get out only the processed string
        work_string += input_channel.get(timeout=0.5)[2:-3].split(':')[1].strip()[1:]
        input_channel.task_done()

        # don't immediately give up to limit padded frames
        if len(work_string) < 29 and retry < 3:
            retry += 1
            continue
        retry = 0

        frame_str = work_string[:29]
        work_string = work_string[len(frame_str):]
