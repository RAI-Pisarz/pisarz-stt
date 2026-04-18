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

def record_callback(_, audio: sr.AudioData) -> None:
    """
    Threaded callback function to receive audio data when recordings finish.
    audio: An AudioData containing the recorded bytes.
    """
    # print('I am in callback function')
    data = audio.get_raw_data()
    q.put(data)

def linux_workaround(args):
    if 'linux' in platform:
        mic_name = args.default_microphone
        if not mic_name or mic_name == 'list':
            print("Available microphone devices are: ")
            for index, name in enumerate(sr.Microphone.list_microphone_names()):
                print(f"Microphone with name \"{name}\" found")
            return None
        else:
            for index, name in enumerate(sr.Microphone.list_microphone_names()):
                if mic_name in name:
                    source = sr.Microphone(sample_rate=16000, device_index=index)
                    break
    else:
        source = sr.Microphone(sample_rate=16000)

    return source


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
    logger = LogAgent(log_channel, 'WHISPER')
    logger.log('TRACE', 'Initialising model...')
    state = 'WORK'

    phrase_time = None
    phrase_bytes = bytes()
    recorder = sr.Recognizer()
    recorder.energy_threshold = 300 # args.energy_threshold
    recorder.dynamic_energy_threshold = False
    transcription = ''

    record_timeout = int(config['whisper']['record_timeout'])
    phrase_timeout = int(config['whisper']['phrase_timeout'])

    logger.log('TRACE', 'Timeouts set...')

    # Important for linux users.
    # Prevents permanent application hang and crash by using the wrong Microphone
    sound_device = linux_workaround(args)

    logger.log( 'INFO', f'Loading whisper.{args.size}...')
    time_before_model_loaded = datetime.now()

    # Load / Download model
    try:
        audio_model = whisper.load_model(args.size)
    except Exception as e:
        logger.log( 'ERROR', f'Failed to load whisper.\n{e}')
        return

    model_loadtime = datetime.now() - time_before_model_loaded
    logger.log( 'INFO',
        f'Model whisper.{args.size} loaded. Time taken: {model_loadtime.total_seconds()} seconds')

    with sound_device:
        recorder.adjust_for_ambient_noise(sound_device)

    logger.log( 'INFO', 'Sound device set...')

    # Create a background thread that will pass us raw audio bytes.
    recorder.listen_in_background(sound_device, record_callback, phrase_time_limit=record_timeout)

    # Cue the user that we're ready to go.
    logger.log( 'INFO', 'Model ready.')

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
            if not q.empty(): # empty the queue
                q.get()
                q.task_done()
            sleep(0.25)
            continue

        try:
            now = datetime.now()

            if q.empty() and not (phrase_time and now - phrase_time > timedelta(seconds=phrase_timeout)):
                sleep(0.1)
                continue


            phrase_complete = False

            # If enough time has passed between recordings, consider the phrase complete.
            # Clear the current working audio buffer to start over with the new data.
            if phrase_time and now - phrase_time > timedelta(seconds=phrase_timeout):
                phrase_bytes = bytes()
                phrase_complete = True
                if state != 'QUIET': logger.log( 'DEBUG', 'Phrase completed.')
                if state != 'QUIET': logger.log( 'TRACE', f'Time: {datetime.now()}')

            # This is the last time we received new audio data from the queue.
            phrase_time = now

            # Combine audio data from queue
            audio_data = b''.join(q.queue)
            q.queue.clear()
            # Add the new audio data to the accumulated data for this phrase
            phrase_bytes += audio_data
            if state != 'QUIET': logger.log( 'TRACE', 'Updated phrase bytes.')
            # Convert in-ram buffer to something the model can use directly without needing a temp file.
            # Convert data from 16-bit wide integers to floating point with a width of 32 bits.
            # Clamp the audio stream frequency to a PCM wavelength compatible default of 32768hz max.
            audio_np = np.frombuffer(phrase_bytes, dtype=np.int16).astype(np.float32) / 32768.0

            # Read the transcription.
            result = audio_model.transcribe(audio_np, fp16=torch.cuda.is_available(), language='pl')
            text = result['text'].strip()
            if state != 'QUIET': logger.log( 'TRACE', f'stripped text: {text}')
            # If we detected a pause between recordings, add a new item to our transcription.
            # Otherwise, edit the existing one.
            if phrase_complete and not transcription == '':
                if state != 'QUIET': logger.log( 'TRACE', 'Putting transcribed phrase in the queue.\n'
                                                  f'\t\tPhrase is {'empty' if transcription == '' else transcription}')
                output_channel.put(transcription)
                transcription = ''
            elif not text == '':
                transcription = text
            else: # for the sake of cpu's mental health
                sleep(0.3)

        except KeyboardInterrupt:
            break