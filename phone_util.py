import re
import math
import queue
import time

from telephonebox import Event, State, Command, LineState, CommandConnection, Driver


def load_model_config(model):
    config = {}
    if model:
        print(f'Loading model configration {model}')
        with open(model, 'rt') as file:
            # matches: key:val
            kvpre = re.compile(
                r'^\s*(\w+)\s*:\s*([ -~]+)')
            # matches: # comment
            commentre = re.compile(r'^\s*#.*$')
            for line in file.readlines():
                line = line.strip()
                # skip empty lines and comments
                if line and not commentre.match(line):
                    m = kvpre.match(line)
                    if not m:
                        raise Exception(f'Invalid configuration {line}')
                    config[m[1]] = m[2]

    return config

# Increase audio volume


def adjust_volume(soundfile, db):
    (data, samplerate) = soundfile
    data *= math.pow(10, db/20)  # multiply amplitude


def create_device_emulator(verbose_level, port, model):
    """Phonebox emulator that can be used with applications that normally talk to the Phonebox. UI is the phone."""
    print("Emulator")

    class EmulationDevice:
        eventq = queue.Queue()  # outgoing events
        cmdq = queue.Queue()  # incoming commands
        state = State.IDLE
        linestate = LineState.ON_HOOK

        def receive_cmd(self):
            if self.cmdq.empty():
                return (None, [])
            return self.cmdq.get_nowait()

        def receive(self):
            try:
                ev = self.eventq.get(timeout=1.0)
                (event, params) = ev
                if event == Event.STATE:
                    self.state = State[params[0]]
                return ev
            except queue.Empty:
                pass
            return (Event.NONE, [])

        def get_state(self):
            return self.state

        def set_line_state(self, linestate):
            self.linestate = linestate

        def set_state(self, state):
            self.put_event(Event.STATE, [state.name])

        def get_line_state(self):
            return self.linestate

        def put_event(self, event, params=[]):
            # print("PUT", event, params)
            self.eventq.put((event, params))

        def command(self, cmd: Command, params={}):
            self.cmdq.put((cmd, params))

    return EmulationDevice()


# Connects to the Phonebox hardware. UI is monitoring.


def create_device_driver(verbose_level, port, model):
    config = load_model_config(model)
    if verbose_level:
        print(config)

    if not port:
        print("Finding PhoneBox")
        if verbose_level:
            print("Serial ports:")
        import serial.tools.list_ports
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

    print("Connecting...")
    cc = CommandConnection(verbose_level)
    cc.open_port(port, timeoutms=500)
    driver = Driver(cc, verbose=verbose_level)
    driver.connect()
    print("Device initialized.")
    if config:
        driver.configure(config)

    # Get state from the driver as event
    driver.command_async(Command.STATE)

    return driver
