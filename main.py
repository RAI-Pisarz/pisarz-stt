##
##
##

# local modules
import uart, listener, frame_builder, parser

# globals
import sys
import threading as th
from queue import Queue

if __name__ == "__main__":

    print("#" * 80)
    print("## Welcome.")
    print("#" * 80)

    INPUT_CHANNEL = Queue()
    FRAME_CHANNEL = Queue()
    COM_CHANNEL = Queue()
    internal_state = ''
    try:
        # parse arguments put in the command
        parser, args = parser.build()

        # prepare threads
        vosk_thread = th.Thread(target=listener.loop, args=(INPUT_CHANNEL, COM_CHANNEL, parser, args))
        uart_thread = th.Thread(target=uart.loop, args=(INPUT_CHANNEL, COM_CHANNEL))
        frame_thread = th.Thread(target=frame_builder.loop, args=(INPUT_CHANNEL, COM_CHANNEL))

        uart_thread.start()
        frame_thread.start()
        vosk_thread.start()
        internal_state = 'WORK'

        while vosk_thread.is_alive() and uart_thread.is_alive() and frame_thread.is_alive():
            uart_thread.join(1)
            frame_thread.join(1)
            vosk_thread.join(1)

            # command thread
            command = input("user@PISARZ $ ")
            match command:
                case 'sleep':
                    if internal_state == 'SLEEP':
                        print('Already asleep!')
                    else:
                        print('Sleeping...')
                        COM_CHANNEL.put('SLEEP')
                        internal_state = 'SLEEP'

                case 'wake':
                    if internal_state == 'WORK':
                        print('Already awake!')
                    else:
                        print('Waking up...')
                        COM_CHANNEL.put('WAKE')
                        internal_state = 'WORK'
                case 'quit':
                    raise KeyboardInterrupt

                case _:
                    pass




    except (KeyboardInterrupt, SystemExit):
        print("\nShutting down...")
        COM_CHANNEL.put('STOP')
        sys.exit()
