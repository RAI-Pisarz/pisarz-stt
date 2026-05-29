## Original implementation of realtime transcription using whisper model at
# https://github.com/davabase/whisper_real_time, time of access 14.04.26
## Adjusted for specific implementation by Szymon Czerwiński April 2026
## Rewritten realtime transcription implementation using:
## - sounddevice
## - faster-whisper
## Szymon Czerwiński May 2026

import configparser
import numpy as np
import sounddevice as sd

from faster_whisper import WhisperModel

from datetime import datetime, timedelta
from queue import Queue
from time import sleep
from sys import platform

from log import LogAgent


#
# AUDIO QUEUE
#

q = Queue()


def init():
    config = configparser.ConfigParser()
    config.read('pisarz.ini')
    return config


#
# AUDIO CALLBACK
#

def record_callback(indata, frames, time, status):
    """
    Called continuously by sounddevice.

    indata:
        numpy array float32
        shape = (frames, channels)
    """

    if status:
        print(status)

    #
    # convert stereo -> mono if needed
    #

    if len(indata.shape) > 1:
        audio = np.mean(indata, axis=1)
    else:
        audio = indata

    #
    # store copy in queue
    #

    q.put(audio.copy())


def loop(output_channel, com_channel, log_channel, parser, args):
    parser = parser
    config = init()
    logger = LogAgent(log_channel, 'WHISPER')
    logger.log('TRACE', 'Initialising model...')
    state = 'WORK'
    phrase_time = None

    #
    # numpy audio buffer instead of byte buffer
    #

    phrase_audio = np.array([], dtype=np.float32)
    transcription = ''

    record_timeout = float(config['whisper']['record_timeout'])
    phrase_timeout = float(config['whisper']['phrase_timeout'])

    samplerate = int(args.samplerate)

    logger.log('TRACE', 'Timeouts set...')

    #
    # DEVICE SELECTION
    #

    selected_device = None
    if 'linux' in platform:
        mic_name = args.device
        devices = sd.query_devices()

        if not mic_name or mic_name == 'list':
            print("Available microphone devices:\n")

            for index, dev in enumerate(devices):
                print(
                    f'| "{index}" | "{dev["name"]}" '
                    f'| inputs={dev["max_input_channels"]} '
                    f'| samplerate={dev["default_samplerate"]}'
                )
            return None
        else:
            for index, dev in enumerate(devices):
                name = dev['name']
                print(f'{index}, {name}')
                if (
                    isinstance(mic_name, str)
                    and mic_name in name
                ) or (
                    isinstance(mic_name, int)
                    and mic_name == index
                ):
                    selected_device = index
                    print(f'Microphone "{name}" selected')
                    break

    #
    # fallback
    #

    if selected_device is None and 'linux' in platform:
        logger.log(
            'ERROR',
            'Could not find requested microphone device.'
        )
        return

    #
    # LOAD MODEL
    #

    logger.log(
        'INFO',
        f'Loading faster-whisper {args.size}...'
    )

    time_before_model_loaded = datetime.now()

    try:
        audio_model = WhisperModel(
            args.size,
            device='cpu',
            compute_type='int8',
            cpu_threads=1
        )

    except Exception as e:
        logger.log(
            'ERROR',
            f'Failed to load faster-whisper.\n{e}'
        )
        return

    model_loadtime = datetime.now() - time_before_model_loaded

    logger.log(
        'INFO',
        f'Model loaded. '
        f'Time taken: {model_loadtime.total_seconds()} seconds'
    )

    #
    # START AUDIO STREAM
    #

    try:
        stream = sd.InputStream(
            samplerate=samplerate,
            blocksize=int(samplerate * record_timeout),
            device=selected_device,
            channels=1,
            dtype='float32',
            callback=record_callback
        )
        stream.start()

    except Exception as e:
        logger.log(
            'ERROR',
            f'Failed to start audio stream.\n{e}'
        )
        return

    logger.log('INFO', 'Sound device set...')
    logger.log('INFO', 'Model ready.')

    #
    # MAIN LOOP
    #

    while True:
        #
        # COM CHANNEL
        #
        if not com_channel.empty():
            msg = com_channel.get()
            match msg:
                case 'WAIT':
                    logger.log(
                        'INFO',
                        'Received WAIT - halting work.'
                    )
                    state = 'WAIT'
                case 'RESUME':
                    logger.log(
                        'INFO',
                        'Received RESUME - resuming work.'
                    )
                    state = 'WORK'
                case 'QUIET':
                    logger.log(
                        'INFO',
                        'Received QUIET - silent work.'
                    )
                    state = 'QUIET'
                case 'GET STATE':
                    logger.log(
                        'TRACE',
                        'Received GET STATE.'
                    )
                    logger.log(
                        'INFO',
                        f'Current state: {state}'
                    )
                case 'STOP':
                    logger.log(
                        'INFO',
                        'Received STOP - shutting down.'
                    )
                    break
                case 'UPDATE':
                    logger.log(
                        'INFO',
                        'Updating...'
                    )
                    config = init()
                    phrase_timeout = float(
                        config['whisper']['phrase_timeout']
                    )
                case _:
                    logger.log(
                        'ERROR',
                        'Unrecognised command on COM channel!'
                    )

        #
        # WAIT MODE
        #

        if state == 'WAIT':
            while not q.empty():
                q.get()
            sleep(0.25)
            continue

        try:
            now = datetime.now()
            #
            # NO AUDIO YET
            #
            if q.empty() and not (phrase_time and now - phrase_time > timedelta(seconds=phrase_timeout)):
                sleep(0.05)
                continue

            phrase_complete = False
            #
            # PHRASE COMPLETION
            #

            if phrase_time and now - phrase_time > timedelta(seconds=phrase_timeout):
                phrase_complete = True
                if state != 'QUIET':
                    logger.log('DEBUG', 'Phrase completed.')
                    logger.log('TRACE', f'Time: {datetime.now()}')

            phrase_time = now

            # GATHER AUDIO
            chunks = []
            while not q.empty():
                chunks.append(q.get())
            # concatenate queue chunks
            if chunks:
                audio_chunk = np.concatenate(chunks)
                phrase_audio = np.concatenate(
                    [phrase_audio, audio_chunk]
                )
                if state != 'QUIET':
                    logger.log('TRACE','Updated phrase audio.')

            # SKIP EMPTY AUDIO
            if len(phrase_audio) == 0:
                sleep(0.1)
                continue

            # TRANSCRIBE
            segments, info = audio_model.transcribe(
                phrase_audio,
                language=args.language,
                beam_size=1,
                vad_filter=False
            )

            text = ' '.join(segment.text for segment in segments).strip()

            if state != 'QUIET':
                logger.log('TRACE',f'Stripped text: {text}')

            # FINALIZE PHRASE
            if phrase_complete:
                if text != '':
                    if state != 'QUIET':
                        logger.log('TRACE', 'Putting transcribed phrase in queue.\n'
                            f'\t\tPhrase: {text}')
                    output_channel.put(text)
                text = ''

                # reset phrase audio
                phrase_audio = np.array([], dtype=np.float32)

            else:
                sleep(0.3)

        except KeyboardInterrupt:
            break

        except Exception as e:
            logger.log('ERROR', f'Whisper runtime error:\n{e}')
            sleep(0.5)

    #
    # CLEANUP
    #

    try:
        stream.stop()
        stream.close()

    except Exception:
        pass

    logger.log('INFO', 'Whisper thread shut down.')

