## Original implementation of realtime transcription using whisper model at
# https://github.com/davabase/whisper_real_time, time of access 14.04.26
## Adjusted for specific implementation by Szymon Czerwiński April 2026

import argparse, numpy as np, speech_recognition as sr, whisper, torch, configparser

from datetime import datetime, timedelta
from queue import Queue
from time import sleep
from sys import platform
# from turtledemo.chaos import jumpto

from log import LogAgent

# queue for model callback
q = Queue()

def init():
    config = configparser.ConfigParser()
    config.read('pisarz.ini')
    return config

def loop(output_channel, com_channel, log_channel, parser, args):
    """
    :param output_channel:
    :param com_channel:
    :param log_channel:
    :param parser:
    :param args:
    :return:

    phrase_time - The last time a recording was retrieved from the queue.
    phrase_bytes - Bytes object which holds audio data for the current phrase
    recorder = sr.Recognizer() - We use SpeechRecognizer to record our audio because it has a nice feature where it can detect when speech ends.
    recorder.dynamic_energy_threshold = dynamic energy compensation lowers the energy threshold dramatically to a point where the SpeechRecognizer never stops recording.
    """
    parser = parser # I was annoyed by a warning
    config = init()
    logger = LogAgent(log_channel, 'LOREM')
    state = 'WORK'

    phrase_time = None
    transcription = ''

    record_timeout = int(config['whisper']['record_timeout'])
    phrase_timeout = int(config['whisper']['phrase_timeout'])

    logger.log('TRACE', 'Timeouts set...')

    # Important for linux users.
    # Prevents permanent application hang and crash by using the wrong Microphone


    file_path = 'pan-tadeusz.txt'

    with open(file_path, 'r', encoding='utf-8') as file:
        file_content = file.read()
        file_content = file_content.split('\n')
    i = 0
    logger.log( 'INFO', 'Test ready.')

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

                case 'QUIET':
                    logger.log('INFO', 'Received QUIET - silent work.')
                    state = 'QUIET'

                case 'GET STATE':
                    logger.log('TRACE', 'Received GET STATE.')
                    logger.log('INFO', f'Current state: {state}')

                case 'STOP':
                    logger.log( 'INFO', 'Received STOP - shutting down.')
                    break

                case 'UPDATE':
                    logger.log( 'INFO', 'Updating...')
                    config = init()
                    phrase_timeout = int(config['whisper']['phrase_timeout'])

                case _:
                    logger.log( 'ERROR', 'Unrecognised command on COM channel!')

        if state == 'WAIT':
            sleep(0.25)
            continue

        try:
            if not phrase_time:
                sleep(phrase_timeout)
                phrase_time = True
                continue

            text = f'{file_content[i]} '
            i += 1
            if i == len(file_content): i = 0
            phrase_complete = True
            if phrase_complete and not transcription == '':
                if state != 'QUIET': logger.log( 'TRACE', 'Putting transcribed phrase in the queue.\n'
                                                  f'\t\tPhrase is {'empty' if transcription == '' else transcription}')
                output_channel.put(transcription)
                transcription = ''
                phrase_time = False
                phrase_complete = False
            elif not text == '':
                transcription = text
            else: # for the sake of cpu's mental health
                sleep(0.3)

        except KeyboardInterrupt:
            break