#!/usr/bin/env python3

# prerequisites: as described in https://alphacephei.com/vosk/install and also python module `sounddevice` (simply run command `pip install sounddevice`)
# Example usage using Dutch (nl) recognition model: `python test_microphone.py -m nl`
# For more help run: `python test_microphone.py -h`

import sys
import sounddevice as sd
from queue import Queue
from vosk import Model, KaldiRecognizer
from log import LogAgent

# queue for model callback
q = Queue()


def callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))


def loop(input_channel, com_channel, log_channel, parser, args):
    source = 'VOSK'
    try:
        # set sample rate based on args
        if args.samplerate is None:
            device_info = sd.query_devices(args.device, "input")
            # soundfile expects an int, sounddevice provides a float:
            args.samplerate = int(device_info["default_samplerate"])

        # get model language based on args
        if args.model is None:
            model = Model(lang="en-us")
        else:
            model = Model(lang=args.model)

        # main loop
        with sd.RawInputStream(samplerate=args.samplerate, blocksize = 8000, device=args.device,
                dtype="int16", channels=1, callback=callback):
            print("#" * 80)
            print("Press Ctrl+C to stop the recording")
            print("#" * 80)

            rec = KaldiRecognizer(model, args.samplerate)
            while True:
                # if not com_channel.empty() and com_channel.get() == 'STOP':
                # check for STOP request from main thread
                if not com_channel.empty() and com_channel.get() == 'STOP':
                    com_channel.put('STOP')
                    com_channel.task_done()
                    raise KeyboardInterrupt

                # get data from the recognizer
                data = q.get()
                if rec.AcceptWaveform(data):
                    input_channel.put(rec.Result(), block=True)


    except KeyboardInterrupt:
        print(f'{source} | INFO: Received STOP - Shutting down.')
        parser.exit(0)

    except Exception as e:
        com_channel.put(e)
        parser.exit(type(e).__name__ + ": " + str(e))
    
    return