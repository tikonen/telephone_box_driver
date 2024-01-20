import argparse
import os
import sys
import time
import math
import queue
import serial.tools.list_ports

import sounddevice as sd
import soundfile as sf

from telephonebox import Event, State, LineState, Command
from basicphone import BasicPhone
from dtmfphone import DTMFPhone

verbose_debug = False

# MODEL_LM_ERICSSON_DLG012 0
# MODEL_LM_ERICSSON_DAHH1301 1

AUDIO_PATH = 'audio'
ELEVATOR_MUSIC = 'Elevator-music.wav'
MUSIC = 'Last Ninja 1-1.wav'
BEEPS = 'clock_sync_beeps.wav'
SPEECH = 'The Matrix Agent Smith Monologue.wav'

# Increase audio volume


def adjust_volume(soundfile, db: int):
    (data, samplerate) = soundfile
    data *= math.pow(10, db/20)  # multiply amplitude

# Implement few numbers that have a distinct logic


class PhoneCallDemo(BasicPhone):

    def answer(self, number, elapsed) -> bool:
        if number == "810581":
            return elapsed >= 10  # Answer after 10 seconds
        elif number == '888':
            return elapsed >= 6
        elif number == '911':
            return False  # Never answer
        elif elapsed >= 4:
            return True
        return False

    def oncall(self, number):
        print("*** ONCALL", number)

        # Give time for user to settle the handset on ear
        time.sleep(2)

        if number == "810581":
            # Play elevator music track in an endless loop
            elevator_music = sf.read(os.path.join(AUDIO_PATH, ELEVATOR_MUSIC))
            sd.play(elevator_music[0], elevator_music[1], loop=True)
        elif number == "888":
            # Play a track once
            music = sf.read(os.path.join(AUDIO_PATH, MUSIC))
            sd.play(music[0], music[1], loop=False)
        else:
            # play few beeps and end the call
            beeps = sf.read(os.path.join(AUDIO_PATH, BEEPS))
            sd.play(beeps[0], beeps[1], loop=False)

        # Wait until track ends or the phone hangs up
        self.waitInState(State.WAIT, lambda: sd.get_stream().active)
        sd.stop()

# Rings the phone and plays a clip, then hangs up


class PhoneRingingDemo(BasicPhone):

    def __init__(self, port, verbose_debug):
        super().__init__(port, verbose_debug)
        self.hasCalled = False
        self.timeout = time.time() + 5

    def loop(self):
        if not self.hasCalled:
            # execute call after timer expires
            (_, _, state) = self.update()
            if state == State.IDLE:
                if (time.time() > self.timeout):
                    self.call_out()
                    self.hasCalled = True
            else:
                self.timeout = time.time() + 2
        else:  # already called, execute the default loop
            super().loop()

    def call_out(self):
        print("*** CALL OUT")
        self.driver.command(Command.RING)  # Start ringing the phone
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
        self.waitInState(State.RING)
        self.pickup()

    # Phone was picked up and the line is stable
    def pickup(self):
        print("*** PICK UP")
        speech = sf.read(os.path.join(AUDIO_PATH, SPEECH))
        adjust_volume(speech, 10)  # Make it louder by 10dB (twice as loud)

        # Delay so that user has had time to put handset on the ear.
        answerdelay = time.time() + 3
        while time.time() < answerdelay:
            self.update()

        # start playing audio
        sd.play(speech[0], speech[1], loop=False)
        # wait until audio stops or the phone hangs up
        self.waitInState(State.WAIT, lambda: sd.get_stream().active)
        sd.stop()

        # If still off-hook play hangup effect
        if self.driver.get_state() == State.WAIT:
            sd.play(self.hangup_effect[0], self.hangup_effect[1], loop=False)
            sd.wait()

# Implement sound record example


class PhoneRecordDemo(BasicPhone):

    def oncall(self, number):
        print("*** ONCALL", number)

        time.sleep(2)
        # play few beeps first
        beeps = sf.read(os.path.join(AUDIO_PATH, BEEPS))
        sd.play(beeps[0], beeps[1], loop=False)
        sd.wait()

        # check if phone is still off-hook
        (_, _, state) = self.update()
        if state != State.WAIT:
            return

        q = queue.Queue()

        def callback(indata, frames, time, status):
            """Called (from a separate thread) for each audio block."""
            if status:
                print(status, file=sys.stderr)
            q.put(indata.copy())

        def flush(file):
            """ Write received audio blocks to the record file """
            try:
                while True:
                    file.write(q.get(False))
            except queue.Empty:
                pass
            return True

        samplerate = 22050
        # run soundfile.available_subtypes('WAV') for list of options
        subtype = 'PCM_16'
        filename = 'rec_' + number + '.wav'
        print("Recording to", filename)

        # open soundfile and start recording until user hangs up
        with sf.SoundFile(filename, mode='w', samplerate=samplerate,
                          channels=1, subtype=subtype) as file:
            istream = sd.InputStream(
                samplerate=samplerate, blocksize=0, channels=1, callback=callback)
            istream.start()
            self.waitInState(State.WAIT, lambda: flush(file))
            istream.stop()
            istream.close()
            print("Recording stopped")

        sd.stop()


def main():
    parser = argparse.ArgumentParser(description='Phone Demos')
    parser.add_argument('--verbose', action='store_true', help='verbose mode')
    parser.add_argument('--demo', metavar='mode', default=1,
                        type=int, help='Demo mode [1|2|3|4]')
    parser.add_argument('-p', '--port', metavar='port', help='Serial port')
    # parser.add_argument('-c', '--cmd', nargs='+', metavar='CMD', required=True, help='Command list: LEFT, RIGHT or RESET')
    args = parser.parse_args()

    port = None
    verbose_debug = args.verbose

    if args.port:
        port = args.port
    else:
        if verbose_debug:
            print("Serial ports:")
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            if verbose_debug:
                print("\t", p)
            if "Arduino" in p.description or "CH340" in p.description:
                port = p.device

    if port:
        print("Device port: ", port)
    else:
        print("ERROR: No Device port found.")
        exit(1)

    # print audio devices
    device = sd.query_devices(kind='output')
    if device:
        print(f'AUDIO OUTPUT: {device["name"]}')
    else:
        print("WARNING: No output audio device")
    device = sd.query_devices(kind='input')
    if device:
        print(f'AUDIO INPUT: {device["name"]}')
    else:
        print("WARNING: No input audio device")

    if args.demo == 1:
        print("Demo#1 Call handling")
        demo = PhoneCallDemo(port, verbose_debug)
    elif args.demo == 2:
        print("Demo#2 Ringout")
        demo = PhoneRingingDemo(port, verbose_debug)
    elif args.demo == 3:
        print("Demo#3 Recording")
        demo = PhoneRecordDemo(port, verbose_debug)
    elif args.demo == 4:
        print("Demo#4 DTMF phone")
        demo = DTMFPhone(port, verbose_debug)
    else:
        raise Exception("Unknown demo", args.demo)

    try:
        while True:
            demo.loop()
    except KeyboardInterrupt:
        print("Exiting...")
        pass


if __name__ == '__main__':
    main()
