##
##
##

# local modules
import uart, vosk_listener, whisper_listener, frame_builder, parser, log

# globals
import sys, threading as th, queue as q
from time import sleep

def state(command):
    if len(command) < 2:
        state([command[0], 'help'])
        return
    command[1] = command[1].lower()
    match command[1]:
        case 'set':
            channel = None
            match command[2]:
                case 'model':
                    channel = MCOM_CHANNEL
                case 'uart':
                    channel = UCOM_CHANNEL
                case 'framer':
                    channel = FCOM_CHANNEL
            if channel is None:
                logger.log('ERROR', f'Can\'t set state for: {command[2]}.')
                return
            if command[3].upper() == 'WORK':
                command[3] = 'RESUME'
            channel.put(command[3].upper())

        case 'model':
            if not model_thread.is_alive():
                logger.log('ERROR', f'Frame builder is not running.')
                return
            MCOM_CHANNEL.put('GET STATE')

        case 'uart':
            if not uart_thread.is_alive():
                logger.log('ERROR', f'Frame builder is not running.')
                return
            UCOM_CHANNEL.put('GET STATE')

        case 'framer':
            if not frame_thread.is_alive():
                logger.log('ERROR', f'Frame builder is not running.')
                return
            FCOM_CHANNEL.put('GET STATE')

        case 'logger':
            print('Logging agent has no internal state to track.')

        case 'help':
            print('state - used for checking and setting internal states for threads.\n'
                  '\tusage:\n'
                  '\t\tstate {module}\n'
                  '\t\tstate set {module} {state}\n\n'
                  '\tavailable modules: model uart framer\n'
                  '\tavailable states:  WAIT, WORK, RESUME, STOP\n'
                  '\tmodel has additional QUIET state to suppress any logging.\n'
                  '\tmind: WORK and RESUME are synonymous.\n'
                  '\t\tSTOP will kill the thread\n.')

        case _:
            logger.log('ERROR', f'Incorrect argument: {command[1]}. Check state help for usage.')

if __name__ == "__main__":

    print("#" * 80)
    print("## Welcome.")
    print("#" * 80)

    INPUT_CHANNEL = q.Queue()
    FRAME_CHANNEL = q.Queue()
    LOG_CHANNEL   = q.Queue()
    LCOM_CHANNEL  = q.Queue()
    FCOM_CHANNEL  = q.Queue()
    MCOM_CHANNEL  = q.Queue()
    UCOM_CHANNEL  = q.Queue()
    internal_state = ''
    command = None
    logger = log.LogAgent(LOG_CHANNEL, 'MAIN   ')

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
        uart_thread = th.Thread(target=uart.loop, args=(FRAME_CHANNEL, UCOM_CHANNEL,  LOG_CHANNEL))
        frame_thread = th.Thread(target=frame_builder.loop, args=(INPUT_CHANNEL, FRAME_CHANNEL, FCOM_CHANNEL, LOG_CHANNEL))
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

            command = input("user@PISARZ $ ").strip() if command is None else command
            logger.log('DEBUG', f'Received command {command}')
            command = command.split(' ')
            match command[0]:
                case 'quit':
                    raise KeyboardInterrupt

                case 'state':
                    try:
                        state(command)
                    except:
                        logger.log('ERROR',
                                   f'Encountered unexpected error while executing command: {command[1]}.')

                case _:
                    logger.log('ERROR', f'Unknown command: {' '.join(command)}')
            command = None
            # just sleep for a bit
            sleep(0.1)




    except (KeyboardInterrupt, SystemExit):
        print(f"\n{logger.source} | INFO: Shutting down...")
        UCOM_CHANNEL.put('STOP')
        MCOM_CHANNEL.put('STOP')
        FCOM_CHANNEL.put('STOP')
        uart_thread.join(10)
        frame_thread.join(10)
        model_thread.join(10)

        LCOM_CHANNEL.put('STOP')
        log_thread.join(10)
        sys.exit()
