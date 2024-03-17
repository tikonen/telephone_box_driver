import time

from telephonebox import Event, State, LineState, Command
import phone_audio as pa

# Basic phone implements standard line tones and classical rotary phone logic. Methods
# Can be overridden as required.


class BasicPhone():
    def __init__(self, driver, verbose):
        print("Loading audio files.")
        self.verbose = verbose
        self.driver = driver
        pa.load_audio(self)

    def config(self, conf):
        if conf:
            self.driver.configure(conf)

    # Receive events from the driver and update status
    def update(self) -> tuple[Event, list[str], State]:
        (ev, params) = self.driver.receive()
        if self.verbose and ev != Event.NONE:
            print(ev, params)
        return (ev, params, self.driver.get_state())

    # Wait doing nothing until state changes
    def waitInState(self, theState, predicate=None) -> State:
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
        pa.play_audio(self.dial_tone)
        self.waitInState(State.WAIT)
        pa.stop_audio()

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
            elif ev == Event.DIAL_BEGIN:
                timeout = time.time() + 5
            elif ev == Event.DIAL:
                print('Digit', params[0])
                digits.append(params[0])
                timeout = time.time() + 3  # wait few seconds for each digit
                if len(digits) > 15:
                    self.dial_error()
                    break

    # Play ringing tone until answer
    def ringing(self, digits):
        print("*** RINGING", digits)
        pa.play_audio(self.ringing_tone)
        ts = time.time()

        def answer_check():
            return not self.answer(digits, time.time() - ts)

        result = self.waitInState(State.WAIT, answer_check)
        pa.stop_audio()
        if result == State.WAIT:
            # play pickup crackle sound effect
            pa.play_audio(self.pickup_effect, wait=True)
            self.oncall(digits)
            if self.driver.get_state() == State.WAIT:  # Line is still open
                pa.play_audio(self.hangup_effect, wait=True)

    # Return true if a call to this number should be answered
    def answer(self, number, elapsed) -> bool:
        return elapsed >= 10  # Answer after 10 seconds

    # Phone is on call.
    def oncall(self, number):
        print("*** ONCALL", number)
        time.sleep(2)
        pa.play_audio(self.low_tone)
        self.waitInState(State.WAIT)
        pa.stop_audio()

    # Some error in dialing, usually means user failed to operate the rotary dial correctly.
    def dial_error(self):
        print('*** DIAL-ERROR')
        pa.play_audio(self.low_tone)

        while True:
            (_, _, state) = self.update()
            # User must hang up to clear state
            if state == State.IDLE or state == State.EXIT:
                break

        pa.stop_audio()

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
