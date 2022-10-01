import os
import sounddevice
import soundfile
import time

from telephonebox import Event, State, LineState
import telephonebox as tb

# Precise tone plan is a signaling specification for plain old telephone
# system (PSTN) that defines the call progress tones used on line.
AUDIO_PATH    ='./audio'
DIAL_TONE     = 'precise_tone_plan/dialtone_350_440.wav'
RINGING_TONE  = 'precise_tone_plan/ringing_tone_440_480_cadence.wav'
LOW_TONE      = 'precise_tone_plan/low_tone_480_620_cadence.wav' # busy/error tone
HIGH_TONE     = 'precise_tone_plan/high_tone_480.wav'

# Basic phone implements standard line tones and classical rotary phone logic. Methods
# Can be overridden as required.
class BasicPhone():
    def __init__(self, port, verbose):
        print("Loading audio files.")
        self.verbose = verbose
        self.load_audio()

        print("Connecting...")
        cc = tb.CommandConnection(self.verbose)
        cc.open_port(port)
        self.driver = tb.Driver(cc, verbose=self.verbose)
        self.driver.connect()
        print("Device initialized.")

    def load_audio(self):
        self.dial_tone = soundfile.read(os.path.join(AUDIO_PATH, DIAL_TONE))
        self.ringing_tone = soundfile.read(os.path.join(AUDIO_PATH, RINGING_TONE))
        self.low_tone = soundfile.read(os.path.join(AUDIO_PATH, LOW_TONE))

    # Receive events from the driver and update status
    def update(self):
        (ev, params) = self.driver.receive()
        if self.verbose and ev != Event.NONE:
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
        return elapsed >= 10 # Answer after 10 seconds

    def oncall(self, number):
        print("*** ONCALL", number)
        sounddevice.play(low_tone[0], low_tone[1], loop=True)

        while True:
            (_, _, state) = self.update()
            if state != State.WAIT:
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
        state = self.driver.get_state();
        if state == State.IDLE:
            self.idle()
        elif state == State.WAIT:
            self.wait()
        else:
            self.update()
