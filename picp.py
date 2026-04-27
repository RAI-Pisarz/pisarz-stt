from enum import Enum

"""
the following is a series of enumerations, containing standard picp bytes and messages
"""

class EndBytes(Enum):
    MSG_END = b'\x10'
    CNT_END = b'\x20'
    RPL_END = b'\x40'


class StartBits(Enum):
    MSG_START = 0b00100000
    CNT_START = 0b01000000
    RPL_START = 0b10000000

class StandardMessages(Enum):
    HELLO = b'\x10'
    GOODBYE = b'\x10'
    WAIT = b'\x20'
    RESUME = b'\x10'
    RECEIVED = b'\x10'


def compute_start_byte(length: int, start_bits):
    return (length + start_bits).to_bytes(1, byteorder='big')