##
##
##

# local modules
import uart, vosk_listener, whisper_listener, frame_builder, parser, log

# globals
import sys
import threading as th
from queue import Queue
from time import sleep

if __name__ == "__main__":

    print("#" * 80)
    print("## Welcome.")
    print("#" * 80)

    INPUT_CHANNEL = Queue()
    FRAME_CHANNEL = Queue()
    LOG_CHANNEL = Queue()
    LCOM_CHANNEL = Queue()
    MCOM_CHANNEL = Queue()
    UCOM_CHANNEL = Queue()
    FCOM_CHANNEL = Queue()

    source = 'MAIN   '
    internal_state = ''

    try:
        # parse arguments put in the command
        parser, args = parser.build()

        if args.model == 'vosk':
            model = vosk_listener
        elif args.model == 'whisper':
            model = whisper_listener
        else:
            sys.exit(1)


        # prepare threads
        model_thread = th.Thread(target=model.loop, args=(INPUT_CHANNEL, MCOM_CHANNEL, LOG_CHANNEL, parser, args))
        uart_thread = th.Thread(target=uart.loop, args=(INPUT_CHANNEL, UCOM_CHANNEL,  LOG_CHANNEL))
        frame_thread = th.Thread(target=frame_builder.loop, args=(INPUT_CHANNEL, FCOM_CHANNEL, LOG_CHANNEL))
        log_thread = th.Thread(target=log.loop, args=(LOG_CHANNEL, LCOM_CHANNEL))

        model_thread.start()
        uart_thread.start()
        frame_thread.start()
        log_thread.start()
        internal_state = 'WORK'

        while model_thread.is_alive() and log_thread.is_alive() and frame_thread.is_alive():
            uart_thread.join(0.3)
            frame_thread.join(0.3)
            model_thread.join(0.3)
            log_thread.join(0.3)



            # command thread
            command = input("user@PISARZ $ ").strip()
            match command:
                case 'quit':
                    raise KeyboardInterrupt

                case '':
                    pass

                case _:
                    log.log(LOG_CHANNEL, 'ERROR', source, f'Unknown command: {command}')

            # just sleep for a bit
            sleep(0.25)




    except (KeyboardInterrupt, SystemExit):
        print(f"\n{source} | INFO: Shutting down...")
        LCOM_CHANNEL.put('STOP')
        UCOM_CHANNEL.put('STOP')
        MCOM_CHANNEL.put('STOP')
        FCOM_CHANNEL.put('STOP')
        uart_thread.join(1)
        frame_thread.join(1)
        model_thread.join(1)
        log_thread.join(1)
        sys.exit()
