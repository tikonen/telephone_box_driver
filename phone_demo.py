import argparse
import os
import time
import serial.tools.list_ports

import sounddevice
import soundfile

from telephonebox import Event, State, LineState
import telephonebox as tb

# Precise tone plan is a signaling specification for plain old telephone
# system (PSTN) that defines the call progress tones used on line.
AUDIO_PATH    ='./audio'
DIAL_TONE     = 'precise_tone_plan/dialtone_350_440.wav'
RINGING_TONE  = 'precise_tone_plan/ringing_tone_440_480_cadence.wav'
LOW_TONE      = 'precise_tone_plan/low_tone_480_620_cadence.wav' # busy/error tone
HIGH_TONE     = 'precise_tone_plan/high_tone_480.wav'

ELEVATOR_MUSIC = 'Elevator-music.wav'
BEEPS = 'clock_sync_beeps.wav'

verbose_debug = False

class BasicPhoneDemo():
    def __init__(self, port):
        print("Loading audio files.")
        self.load_audio()

        print("Connecting...")
        cc = tb.CommandConnection(verbose_debug)
        cc.open_port(port)
        self.driver = tb.Driver(cc, verbose=verbose_debug)
        self.driver.connect()
        print("Device initialized.")

    def load_audio(self):
        self.dial_tone = soundfile.read(os.path.join(AUDIO_PATH, DIAL_TONE))
        self.ringing_tone = soundfile.read(os.path.join(AUDIO_PATH, RINGING_TONE))
        self.low_tone = soundfile.read(os.path.join(AUDIO_PATH, LOW_TONE))

    # Receive events from the driver and update status
    def update(self):
        (ev, params) = self.driver.receive()
        if verbose_debug and ev != Event.NONE:
            print(ev, params)
        return (ev, params, self.driver.get_state())

    def waitInState(self, theState):
        while True:
            (_, _, state) = self.update()
            if state != theState:
                return state

    def idle(self):
        print("*** IDLE (ONHOOK)")
        self.waitInState(State.IDLE)

    def wait(self):
        print("*** WAIT (OFFHOOK)")
        sounddevice.play(self.dial_tone[0], self.dial_tone[1], loop=True)
        state = self.waitInState(State.WAIT)
        sounddevice.stop()
        if state == State.DIAL:
            self.dial()

    def dial(self):
        print("*** DIAL")
        timeout = time.time() + 8 # wait for 8 seconds the first digit
        digits = []
        while True:
            (ev, params, state) = self.update()
            if state == State.DIAL_ERROR:
                self.dial_error()
                break
            elif self.driver.get_line_state() == LineState.ON_HOOK or self.driver.get_state() == State.IDLE:
                # User hang up
                break
            elif time.time() > timeout:
                if len(digits) == 0:
                    # timeout and no number dialed
                    self.dial_error()
                else:
                    self.ringing(''.join(digits))
                break
            elif ev == Event.DIAL:
                print('Digit', params[0])
                digits.append(params[0])
                timeout = time.time() + 3 # 3 seconds for each digit
                if len(digits) > 15:
                    self.dial_error()
                    break

    def ringing(self, digits):
        print("*** RINGING", digits)
        ts = time.time()
        sounddevice.play(self.ringing_tone[0], self.ringing_tone[1], loop=True)
        while True:
            (_, _, state) = self.update()
            if state != State.WAIT:
                break
            if self.answer(digits, time.time() - ts):
                sounddevice.stop()
                time.sleep(1)
                # Todo should play pickup crackle sound effect?
                self.oncall(digits)
                break

        sounddevice.stop()

    def answer(self, number, elapsed):
        if number == "810581":
            if elapsed >= 10: # Answer after 10 seconds
                return True
        else:
            if elapsed >= 4:
                return True
        return False

    def oncall(self, number):
        print("*** ONCALL", number)
        if number == "810581":
            elevator_music = soundfile.read(os.path.join(AUDIO_PATH, ELEVATOR_MUSIC))
            sounddevice.play(elevator_music[0], elevator_music[1], loop=True)
        else:
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

    def dial_error(self):
        print('*** DIAL-ERROR')
        sounddevice.play(self.low_tone[0], self.low_tone[1], loop=True)

        while True:
            (_, _, state) = self.update()
            # User must hang up to clear state
            if state == State.IDLE:
                break

        sounddevice.stop()

    def loop(self):
        while True:
            state = self.driver.get_state();
            if state == State.IDLE:
                self.idle()
            elif state == State.WAIT:
                self.wait()
            else:
                self.update()

parser = argparse.ArgumentParser(description='Phone Demo #1')
parser.add_argument('--verbose', action='store_true', help='verbose mode')
parser.add_argument('-p', '--port', metavar='port', help='Serial port')
#parser.add_argument('-c', '--cmd', nargs='+', metavar='CMD', required=True, help='Command list: LEFT, RIGHT or RESET')
args = parser.parse_args()

verbose_debug = args.verbose

port = None
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

demo = BasicPhoneDemo(port)
demo.loop()
