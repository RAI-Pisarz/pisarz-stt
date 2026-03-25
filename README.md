# PiSARZ Speech-To-Text Module

This is a speech-to-text parser module for PiSARZ. This repository contains all software run on speech detection module.
STT module takes in audio from a connected microphone as a data stream and processes it using Vosk model to text. 
Further processing includes splitting text into chunks and calculating CRCs for PICP-based communication with other controllers within the project.

PICP is discussed later on in this document.

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
Only first MSG_LENGTH bytes after START contain useful information. Following bytes up to Byte 29 are padding. 

### END byte structure

**END** byte contains only information regarding this and next message sent as follows:

| Bits      | MSG_TYPE | Desc                                                                                                                                     |
|-----------|----------|------------------------------------------------------------------------------------------------------------------------------------------|
| 0001 0000 | MSG_END  | This is the end of message.                                                                                                              |
| 0010 0000 | CNT_END  | This message is split between data frames. Last MSG byte of this and first MSG byte of next are likely to be part of the same data unit. |
| 0100 0000 | RPL_END  | Demands a reply from reciever.                                                                                                           |


Required libraries:
- 
- system
- argparse
- sounddevice
- queue
- vosk
