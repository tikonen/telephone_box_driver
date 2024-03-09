import argparse
import os
import sys
import time
import queue
import serial.tools.list_ports

import sounddevice as sd
import soundfile as sf

from telephonebox import Event, State, Command, CommandConnection, Driver
from basicphone import BasicPhone
from dtmfphone import DTMFPhone
from phone_util import load_model_config, adjust_volume
import phone_audio

verbose_debug = False

AUDIO_PATH = 'audio'
ELEVATOR_MUSIC = 'Elevator-music.wav'
MUSIC = 'Last Ninja 1-1.wav'
BEEPS = 'clock_sync_beeps.wav'
SPEECH = 'The Matrix Agent Smith Monologue.wav'


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
            elevator_music = sf.read(os.path.join(
                AUDIO_PATH, ELEVATOR_MUSIC), dtype='float32')
            phone_audio.play_audio(elevator_music)
        elif number == "888":
            # Play a track once
            music = sf.read(os.path.join(AUDIO_PATH, MUSIC), dtype='float32')
            phone_audio.play_audio(music, loop=False)
        else:
            # play few beeps and end the call
            beeps = sf.read(os.path.join(AUDIO_PATH, BEEPS), dtype='float32')
            phone_audio.play_audio(beeps, loop=False)

        # Wait until track ends or the phone hangs up
        self.waitInState(State.WAIT, lambda: phone_audio.is_playing())
        phone_audio.stop_audio()

# Rings the phone and plays a clip, then hangs up


class PhoneRingingDemo(BasicPhone):

    def __init__(self, driver, verbose_debug):
        super().__init__(driver, verbose_debug)
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
        speech = sf.read(os.path.join(AUDIO_PATH, SPEECH), dtype='float32')
        adjust_volume(speech, 10)  # Make it louder by 10dB (twice as loud)

        # Delay so that user has had time to put handset on the ear.
        answerdelay = time.time() + 3
        while time.time() < answerdelay:
            self.update()

        # start playing audio
        phone_audio.play_audio(speech, loop=False)
        # wait until audio stops or the phone hangs up
        self.waitInState(State.WAIT, lambda: phone_audio.is_playing())
        phone_audio.stop_audio()

        # If still off-hook play hangup effect
        if self.driver.get_state() == State.WAIT:
            phone_audio.play_audio(self.hangup_effect, wait=True)

# Implement sound record example


class PhoneRecordDemo(BasicPhone):

    def oncall(self, number):
        print("*** ONCALL", number)

        time.sleep(2)
        # play few beeps first
        beeps = sf.read(os.path.join(AUDIO_PATH, BEEPS), dtype='float32')
        phone_audio.play_audio(beeps, wait=True)

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
            while not q.empty():
                file.write(q.get(False))

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
    demohelp = """'call' Dialing and call handling,
        'ring' Phone ringing,
        'record' Voice recording and
        'dtmf Dial Tone Multi Frequency decoding
        """
    parser = argparse.ArgumentParser(description='Phone Demos')
    parser.add_argument('demo', help=demohelp, default='call')
    parser.add_argument('-v', '--verbose', default=0,
                        action='count', help='verbose mode')
    parser.add_argument('-p', '--port', metavar='PORT', help='Serial port')
    parser.add_argument(
        '-m', '--model', metavar='FILE', help='Phone model file')
    args = parser.parse_args()

    port = None
    verbose_level = args.verbose

    config = load_model_config(args.model)
    if verbose_level:
        print(config)

    if args.port:
        port = args.port
    else:
        print("Finding PhoneBox")
        if verbose_level:
            print("Serial ports:")
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            if verbose_level:
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

    print("Connecting...")
    cc = CommandConnection(verbose_level)
    cc.open_port(port, timeoutms=500)
    driver = Driver(cc, verbose=verbose_level)
    driver.connect()
    print("Device initialized.")

    if args.demo == 'call':
        print("Demo#1 Call handling")
        demo = PhoneCallDemo(driver, verbose_level)
    elif args.demo == 'ring':
        print("Demo#2 Ringout")
        demo = PhoneRingingDemo(driver, verbose_level)
    elif args.demo == 'record':
        print("Demo#3 Recording")
        demo = PhoneRecordDemo(driver, verbose_level)
    elif args.demo == 'dtmf':
        print("Demo#4 DTMF phone")
        demo = DTMFPhone(driver, verbose_level)
    else:
        raise Exception("Unknown demo", args.demo)

    # Load model definitions and configure
    demo.config(config)

    try:
        while True:
            demo.loop()
    except KeyboardInterrupt:
        print("Exiting...")


if __name__ == '__main__':
    main()
