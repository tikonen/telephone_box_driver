# Telephone Box driver

### Introduction

Interface library and test application for the Telephone Box Device.

Telephone Box Device hardware implements a virtual telephone exchange interface for a classic vintage rotary phone. Arduno Nano controls the logic and exposes a serial interface for the application. Supply requirement: 12V 1A.
See [Schematics](firmware/schematics) and [Interface Specification](firmware/telephone_box/README.md)

Package `telephonebox` is a low level interface for the Telephone Box serial interface.

`basicphone.py` is a base class for the applications that want to support the classic rotary phone logic, i.e. dial tone, dialing experience, ringing tone etc..

**SAFETY WARNING** Telephone Box produces up to 90 VAC voltage when physically ringing the phone bell and can give a very painful shock. Keep hands off the circuit board.

### Quickstart

1. Install Python libraries
* [sounddevice](https://pypi.org/project/sounddevice)
* [soundfile](https://pypi.org/project/soundfile)
* [numpy](https://pypi.org/project/numpy/)
* [pyserial](https://pypi.org/project/pyserial/)
* [serial-tool](https://pypi.org/project/serial-tool/)
2. Plugin in Telephone Box device power, usb and audio lines (out and mic). You may need to install [CH340 driver](http://www.wch-ic.com/downloads/CH341SER_ZIP.html) for clone Arduino Nano compatibility.
3. Run demo script to start the default demo application.

	```
	C:\projects\telephone_box_driver>\Python37\python.exe phone_demo.py
	Device port:  COM6
	Demo#1 Call handling
	Loading audio files.
	Connecting...
	Device initialized.
	*** IDLE (ONHOOK)
	```
