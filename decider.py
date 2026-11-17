import sys, queue, picp #, configparser

from log import LogAgent, init
from time import sleep
import json
import urllib.request
import urllib.error

def b_sizeof(b: bytes) -> int:
    return sys.getsizeof(b) - sys.getsizeof(bytes('', 'utf-8'))


def ollama_send(messages, ollama_url, ollama_model):
    payload = {
        "model": ollama_model,
        "messages": messages,
        "stream": False
    }

    request = urllib.request.Request(
        ollama_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            result = json.loads(response.read().decode("utf-8"))

        answer = result["message"]["content"]

        messages.append({
            "role": "assistant",
            "content": answer
        })

    except urllib.error.URLError as error:
        raise "CONNECTION ERROR"

    return answer, messages


def loop(input_channel, output_channel, com_channel, log_channel, args):
    logger = LogAgent(log_channel, 'DECIDER')
    config = init()
    retry_time = float(config['uart']['retry_time'])
    ollama_url = config['ollama']['url']
    ollama_model = config['ollama']['model']
    messages = []
    state = 'WORK'
    mode = 'MODEL' if args.ollama else 'STREAM'
    input_string = ''

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

                case 'GET STATE':
                    logger.log('TRACE', 'Received GET STATE.')
                    logger.log('INFO', f'Current state: {state}')

                case 'STOP':
                    logger.log('INFO', 'Received STOP - shutting down.')
                    return

                case _:
                    logger.log('ERROR', f'Unrecognised command {msg} on COM channel!')

        # wait until new input appears or state changes
        if state == 'WAIT' or input_channel.empty():
            sleep(0.5)
            continue

        try:
            input_string = input_channel.get(timeout=0.5)
            input_channel.task_done()
            if args.transcription_test:
                logger.log('INFO', f'Received phrase:\n\t{input_string}')
        except queue.Empty:
            pass


        if input_string.lower() in ['strumień', 'stream'] and mode == 'MODEL':
            input_string = ''
            logger.log('INFO', 'Switching to STREAM mode.')
            mode = "MODEL"
            output_channel.put("~stream~~~~~~~~~~~~~~~~~~~~~~")
            continue

        if input_string.lower() == 'model' and mode == 'STREAM':
            input_string = ''
            logger.log('INFO', 'Switching to MODEL mode.')
            mode = "STREAM"
            try:
                answer, messages = ollama_send(messages, ollama_url, ollama_model)
            except Exception as e:
                if e == "CONNECTION ERROR":
                    logger.log("ERROR", "Encountered OLLAMA connection error.")
                else:
                    logger.log('ERROR', e)
                logger.log('INFO', "COMMAND mode not available. Reverting to STREAM mode.")
                mode = "STREAM"
                continue
            output_channel.put("~model~~~~~~~~~~~~~~~~~~~~~~~")
            continue


        if state == 'WORK':
            output_channel.put(input_string)
            continue

        if state == 'COMMAND':
            try:
                answer, messages = ollama_send(messages, ollama_url, ollama_model)

            except Exception as e:
                if e == "CONNECTION ERROR":
                    logger.log("ERROR", "Encountered connection error.")
                else:
                    logger.log('ERROR', e)
                logger.log('INFO', "Reverting to stream mode after failed COMMAND attempt.")
                mode = "STREAM"
                continue

            output_channel.put(answer)