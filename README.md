# PiSARZ Speech-To-Text Module

This is a speech-to-text parser module for PiSARZ. This repository contains all software run on speech detection module.
STT module takes in audio from a connected microphone as a data stream and processes it using Vosk model to text. 
Further processing includes splitting text into chunks and calculating CRCs for PICP-based communication with other controllers within the project.

PICP is discussed later on in this document.

# Required python libraries:\
crc, time, system, threading, argparse, sounddevice, queue, whisper, their respective dependencies

# Usage

To launch the program: 

` python main.py`

Program has following possible arguments:

usage: main.py [-h] [-l] [-d DEVICE] [-r SAMPLERATE] [-m MODEL] [-L LANGUAGE] [-s SIZE]\
options:\
  -h, --help            show this help message and exit\
  -l, --list-devices    show list of available audio devices and exit\
  -d, --device DEVICE   input device (numeric ID or substring)\
  -r, --samplerate SAMPLERATE\
                        set sample rate for audio capture in Hz. Defaults to 16000\
  -m, --model MODEL     language model used for transcription; currently available models are: whisper; loremipsum; Defaults to whisper.\
  -L, --language LANGUAGE\
                        language transcription model will focus on; examples for whisper: pl, en\
  -s, --size SIZE       model size; relevant only for whisper. Available: medium, small, base, tiny

You can also access above inbuilt help message via: 

`python main.py -h` or `python main.py --help`

Certain options are not available via commandline arguments. These may be modified within the 'pisarz.md' file.\
These options contain:

**WHISPER**
- Recording timeout in seconds
- Phrase recording timeout in seconds

**UART**
- Maximum retry times for when the current message is too short for defined frame size
- Whether to use PICP (described below. Currently not implemented.)
- Message frame fixed size in bytes
- COM port to be used for communication with downstream device

**LOG**
- Logging level
- Whether to dump logs into a file
- Log dumpfile path
- Whether to log all messages in dumpfile; ignores logging level setting

**OLLAMA**
- url to ollama server
- model hosted on ollama to be communicated with

# PICP - PiSARZ Interal Communication Protocol
**PICP** is an UART based protocol for internal communication between controllers within the project. 
It is designed to allow for two-way communication between devices. Protocol uses 32 byte frames for communication.

### **PICP frame structure**

| Byte No. | Func  | Description                                                                             |
|--------:|-------|-----------------------------------------------------------------------------------------|
|        0 | START | Contains two informations within, MSG_TYPE (first 3 bits) and MSG_LENGTH (last 5 bits). |
|  1 .. 29 | MSG   | Contains information.                                                                   |
|       30 | CRC   | Cyclic Redundancy Check number for error detection.                                     |
|       31 | STOP  | Contains information about what message to expect next.                                 |

### START byte structure

**START** byte contains two separate information. First three bits contain MSG_TYPE:

| Bits | MSG_TYPE | Desc                                                                                                                         |
|------|----------|------------------------------------------------------------------------------------------------------------------------------|
| 001  | NEW_MSG  | Following message is a new, separate message.                                                                                |
| 010  | CNT_MSG  | Following message is a continuation of previous message ended with CNT_END byte. Allows for splitting data between messages. |
| 100  | RPL_MSG  | Following message is a reply to the last recieved message ended with RPL_END byte.                                           |

Following five bits contain length of the message encoded as an unsigned integer. 
Only first MSG_LENGTH bytes after START byte contain useful information. Following bytes up to Byte 29 are padding. 

### CRC Byte

The CRC byte contains a CRC checksum calculated using CRC-8-CCITT algorithm. The checksum is calculated on all previous bytes - both start byte and message bytes.

### END byte structure

**END** byte contains only information regarding this and next message sent as follows:

| Bits      | Hex  | MSG_TYPE | Desc                                                                                                                                     |
|-----------|------|----------|------------------------------------------------------------------------------------------------------------------------------------------|
| 0001 0000 | 0x10 | MSG_END  | This is the end of message.                                                                                                              |
| 0010 0000 | 0x20 | CNT_END  | This message is split between data frames. Last MSG byte of this and first MSG byte of next are likely to be part of the same data unit. |
| 0100 0000 | 0x40 | RPL_END  | Demands a reply from reciever.                                                                                                           |

