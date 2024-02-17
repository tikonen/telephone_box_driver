import os
import sounddevice
import soundfile
import time

from telephonebox import Event, State, LineState
import telephonebox as tb

# Precise tone plan is a signaling specification for plain old telephone
# system (PSTN) that defines the call progress tones used on line.
AUDIO_PATH = './audio'
DIAL_TONE = 'tones/euro/dialtone_europe_425.wav'
RINGING_TONE = 'tones/euro/ringing_tone_europe_425_cadence.wav'
LOW_TONE = 'tones/precise_tone_plan/low_tone_480_620_cadence.wav'  # busy/error tone
HIGH_TONE = 'tones/precise_tone_plan/high_tone_480.wav'
PICKUP_EFFECT = 'phone_pickup.wav'
HANGUP_EFFECT = 'phone_hangup.wav'

# Basic phone implements standard line tones and classical rotary phone logic. Methods
# Can be overridden as required.


class BasicPhone():
    def __init__(self, port, verbose):
        print("Loading audio files.")
        self.verbose = verbose
        self.load_audio()

        print("Connecting...")
        cc = tb.CommandConnection(self.verbose)
        cc.open_port(port, timeoutms=500)
        self.driver = tb.Driver(cc, verbose=self.verbose)
        self.driver.connect()
        print("Device initialized.")

    def load_audio(self):
        self.dial_tone = soundfile.read(os.path.join(AUDIO_PATH, DIAL_TONE))
        self.ringing_tone = soundfile.read(
            os.path.join(AUDIO_PATH, RINGING_TONE))
        self.low_tone = soundfile.read(os.path.join(AUDIO_PATH, LOW_TONE))
        self.pickup_effect = soundfile.read(
            os.path.join(AUDIO_PATH, PICKUP_EFFECT))
        self.hangup_effect = soundfile.read(
            os.path.join(AUDIO_PATH, HANGUP_EFFECT))

    # Receive events from the driver and update status
    def update(self) -> tuple[Event, list[str], State]:
        (ev, params) = self.driver.receive()
        if self.verbose and ev != Event.NONE:
            print(ev, params)
        return (ev, params, self.driver.get_state())

    # Wait doing nothing until state changes
    def waitInState(self, theState, predicate=None):
        while True:
            (ev, _, state) = self.update()
            if state != theState:
                return state
            if predicate and not predicate():
                return state

    # Phone is on-hook
    def idle(self):
        print("*** IDLE (ONHOOK)")
        self.waitInState(State.IDLE)

    # Phone is off-hook and user is not dialing a number
    def wait(self):
        print("*** WAIT (OFFHOOK)")
        sounddevice.play(self.dial_tone[0], self.dial_tone[1], loop=True)
        state = self.waitInState(State.WAIT)
        sounddevice.stop()

    # Dialing has started. Wait for each digit and after no new digits have been
    # received start a call
    def dial(self):
        print("*** DIAL")
        timeout = time.time() + 8  # wait for 8 seconds the first digit
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
                timeout = time.time() + 3  # wait 3 seconds for each digit
                if len(digits) > 15:
                    self.dial_error()
                    break

    # Play ringing tone until answer
    def ringing(self, digits):
        print("*** RINGING", digits)
        sounddevice.play(self.ringing_tone[0], self.ringing_tone[1], loop=True)
        ts = time.time()
        while True:
            (_, _, state) = self.update()
            if state != State.WAIT:
                break
            if self.answer(digits, time.time() - ts):
                sounddevice.stop()
                # play pickup crackle sound effect
                sounddevice.play(
                    self.pickup_effect[0], self.pickup_effect[1], loop=False)
                sounddevice.wait()
                self.oncall(digits)
                if self.driver.get_state() == State.WAIT:  # Line is still open
                    sounddevice.play(
                        self.hangup_effect[0], self.hangup_effect[1], loop=False)
                    sounddevice.wait()
                break

        sounddevice.stop()

    # Return true if a call to this number should be answered
    def answer(self, number, elapsed) -> bool:
        return elapsed >= 10  # Answer after 10 seconds

    # Phone is on call.
    def oncall(self, number):
        print("*** ONCALL", number)
        time.sleep(2)
        sounddevice.play(self.low_tone[0], self.low_tone[1], loop=True)

        self.waitInState(State.WAIT)

        sounddevice.stop()

    # Some error in dialing, usually means user failed to operate the rotary dial correctly.
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
        state = self.driver.get_state()
        if state == State.IDLE:
            self.idle()
        elif state == State.WAIT:
            self.wait()
        elif state == State.DIAL:
            self.dial()
        else:
            self.update()
