import argparse
import sounddevice as sd


def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text


def build():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "-l", "--list-devices", action="store_true",
        help="show list of audio devices and exit")
    args, remaining = parser.parse_known_args()

    if args.list_devices:
        print(sd.query_devices())
        parser.exit(0)

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[parser])
    parser.add_argument(
        "-d", "--device", type=int_or_str,
        help="input device (numeric ID or substring)"
    )
    parser.add_argument(
        "-r", "--samplerate", type=int, help="sampling rate"
    )
    parser.add_argument(
        "-m", "--model", default='whisper', type=str, help="language model; "
                                                           "available models are vosk and whisper"
    )
    parser.add_argument(
        "-L", "--language", type=str, help="language model; "
                                           "examples for vosk:\n en-us, pl-pl\n examples for whisper:\npl, en"
    )
    parser.add_argument(
        "-s", "--size", default='base', type=str, help="model size; relevant only for whisper. Available:\n"
                                       "medium, small, base, tiny"
    )

    args = parser.parse_args(remaining)
    return parser, args