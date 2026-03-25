import sys

def b_sizeof(b: bytes) -> int:
    return sys.getsizeof(b) - sys.getsizeof(bytes('', 'utf-8'))


def loop(input_channel, com_channel):
    work_string = ''
    retry = 0

    try:
        while True:

            if not com_channel.empty() and com_channel.get() == 'STOP':
                com_channel.put('STOP')
                com_channel.task_done()
                raise KeyboardInterrupt

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






    except KeyboardInterrupt:
        print('wee')
        return