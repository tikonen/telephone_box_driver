import argparse
import os
import time
import math
import serial.tools.list_ports

import sounddevice
import soundfile

from telephonebox import Event, State, LineState, Command
import telephonebox as tb
from basicphone import BasicPhone

verbose_debug = False

AUDIO_PATH = 'audio'
ELEVATOR_MUSIC = 'Elevator-music.wav'
MUSIC = 'Last Ninja 1-1.wav'
BEEPS = 'clock_sync_beeps.wav'
SPEECH = 'The Matrix Agent Smith Monologue.wav'

# multiply amplitude of sound data
def adjust_volume(soundfile, db: int):
    (data, samplerate) = soundfile
    data *= math.pow(10, db/20) # multiply amplitude

# Implement few numbers that have distinct logic
class PhoneDemo1(BasicPhone):

    def answer(self, number, elapsed):
        if number == "810581" and elapsed >= 10: # Answer after 10 seconds
            return True
        elif number == '888' and elapsed >= 6:
            return True
        elif number == '911':
            return False # Never answer
        elif elapsed >= 4:
                return True
        return False

    def oncall(self, number):
        print("*** ONCALL", number)
        if number == "810581":
            # Play elevator music track in an endless loop
            elevator_music = soundfile.read(os.path.join(AUDIO_PATH, ELEVATOR_MUSIC))
            sounddevice.play(elevator_music[0], elevator_music[1], loop=True)
        elif number == "888":
            # Play a track once
            music = soundfile.read(os.path.join(AUDIO_PATH, MUSIC))
            sounddevice.play(music[0], music[1], loop=False)
        else:
            # play few beeps and end the call
            beeps = soundfile.read(os.path.join(AUDIO_PATH, BEEPS))
            sounddevice.play(beeps[0], beeps[1], loop=False)

        while True:
            (_, _, state) = self.update()
            if state != State.WAIT:
                break
            if not sounddevice.get_stream().active:
                # audio completed, end the call
                break

        sounddevice.stop()

# Rings the phone and plays a clip, then hangs up
class PhoneDemo2(BasicPhone):

    def __init__(self, port, verbose_debug):
        super().__init__(port, verbose_debug)
        self.hasCalled = False
        self.timeout = time.time() + 5

    def loop(self):
        if not self.hasCalled:
            # execute call after timer expires
            state = self.driver.get_state();
            if state == State.IDLE:
                if(time.time() > self.timeout):
                    self.call_out()
                    self.hasCalled = True
            else:
                self.update()
                self.timeout = time.time() + 2
        else: # already called, execute the default loop
            super().loop()

    def call_out(self):
        print("*** CALL OUT")
        self.driver.command(Command.RING) # Start ringing the phone
        while True:
            (ev, _, state) = self.update()
            if ev == Event.RING_TRIP or state == State.WAIT:
                # Phone has been picked up
                self.ring_trip()
                break
            elif ev == Event.RING:
                print("RING")
            elif ev == Event.RING_PAUSE:
                print("...")
            elif state != State.RING or ev == Event.RING_TIMEOUT:
                break

    def ring_trip(self):
        print("*** RING_TRIP")
        # Wait until line exists the RING state
        while True:
            (_, _, state) = self.update()
            if state != State.RING:
                break
        self.pickup()

    # Phone was picked up and line is stable
    def pickup(self):
        print("*** PICK UP")
        speech = soundfile.read(os.path.join(AUDIO_PATH, SPEECH))
        adjust_volume(speech, 10) # Make it louder by 10dB (twice as loud)

        # Delay so that user has had time to put handset on the ear.
        answerdelay = time.time() + 3
        while time.time() < answerdelay:
            self.update()

        sounddevice.play(speech[0], speech[1], loop=False)
        while True:
            (ev, _, state) = self.update()
            if state != State.WAIT:
                break
            if not sounddevice.get_stream().active:
                # audio completed, end the call
                break
        sounddevice.stop()


parser = argparse.ArgumentParser(description='Phone Demos')
parser.add_argument('--verbose', action='store_true', help='verbose mode')
parser.add_argument('--demo', metavar='mode', default=1, type=int, help='Demo mode [1|2]')
parser.add_argument('-p', '--port', metavar='port', help='Serial port')
#parser.add_argument('-c', '--cmd', nargs='+', metavar='CMD', required=True, help='Command list: LEFT, RIGHT or RESET')
args = parser.parse_args()

port = None
verbose_debug = args.verbose;

if args.port:
    port = args.port
else:
    if verbose_debug:
        print("Serial ports:")
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        if verbose_debug:
            print("\t",p)
        if "Arduino" in p.description or "CH340" in p.description:
            port = p.device

if port:
    print ("Device port: ", port)
else:
    print("ERROR: No Device port found.")
    exit(1);

if args.demo == 1:
    print("Demo#1")
    demo = PhoneDemo1(port, verbose_debug)
elif args.demo == 2:
    print("Demo#2")
    demo = PhoneDemo2(port, verbose_debug)
else:
    raise Exception("Unknown demo", args.demo)
while True:
    demo.loop()
