import configparser, queue, os #, sys
from time import sleep
from datetime import datetime

class LogError(Exception):
    def __init__(self, message):
        self.message = message

class LogAgent:
    """
    An agent to communicate with logger thread
    """
    def __init__(self, log_queue: queue.Queue, source: str):
        """
        :param log_queue: Synchronised queue shared with log thread to put log messages to
        :param source: Name to display in the logs sent from this agent

        An agent to communicate with logger thread. Call method log(level, message) to emmit a log message

        """
        self.queue = log_queue
        self.source = source

    def log(self, level, message: str):
        """
        Send a log message to the log thread
        :param level: See LogLevel dictionary, accepts both string and integer level
        :param message: Message to be displayed
        :return:
        """
        if type(level) is int: level = LogLevel[level]
        self.queue.put([level, self.source, message])

LogLevel = {
    'TRACE':    1,
    'DEBUG':    2,
    'INFO':     3,
    'WARNING':  4,
    'ERROR':    5
}

def init():
    config = configparser.ConfigParser()
    config.read('pisarz.ini')
    return config

def loop(log_channel: queue.Queue, com_channel: queue.Queue):
    logger = LogAgent(log_channel, 'LOGGER ')
    config = init()
    logfile = f'{config['log']['log_path']}pisarz.{datetime.now().strftime('%Y-%m-%d.%H-%M-%S')}.log'
    if not os.path.exists(config['log']['log_path']):
        os.makedirs(config['log']['log_path'])

    while True:
        if not com_channel.empty():
            msg = com_channel.get()
            # do something
            match msg:
                case 'STOP':
                    if log_channel.empty():
                        print(f'LOGGER  | INFO: Received STOP - shutting down.')
                        return
                    com_channel.put(msg)

                case 'UPDATE':
                    logger.log('INFO', 'Updating config.')
                    config = init()

                case _:
                    logger.log('ERROR', 'Unrecognised command on COM channel!')

        try:
            msg = log_channel.get(timeout=2)
            log_channel.task_done()

            # skip the message if logging level wrong
            if LogLevel[config['log']['level']] > LogLevel[msg[0]]:
                raise LogError('Wrong log level, skipping message')

            print(f'{msg[1]} | {msg[0]}: {msg[2]}')

            if not config.getboolean('log', 'dump'):
                raise LogError('Dumping off, ignoring')

            with open(logfile, 'a', encoding='utf-8') as f:
                print(f'{msg[1]} | {msg[0]}: {msg[2]}', file=f)

        except queue.Empty: #ignore timeout
            pass



        except LogError:
            pass

        # just sleep for a bit
        sleep(0.1)