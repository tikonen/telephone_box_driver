import time
from enum import Enum

from . import connection

Command = Enum('Command', 'RING STOP STATE LINE RESET')
Event = Enum('Event','NONE READY OK INVALID INFO TEST PING DIAL_BEGIN DIAL DIAL_ERROR RING_TRIP RING RING_PAUSE RING_TIMEOUT ERROR STATE LINE')
State = Enum('State', 'UNKNOWN INITIAL IDLE RING WAIT DIAL DIAL_ERROR')
LineState = Enum('LineState', 'UNKNOWN OFF_HOOK ON_HOOK SHORT')

def in_enum(enum, val):
    try:
        enum[val]
        return True
    except KeyError:
        return False

class Driver:
    def __init__(self, conn, verbose=False):
        self.conn = conn
        self.lineState = LineState.UNKNOWN
        self.state = State.INITIAL
        self.ready = False # Ready to receive commands
        self.verbose = verbose

    def connect(self, timeout:float=5):
        self.ready = False
        timeout = time.time() + timeout
        self.conn.send_cmd('') # Send empty command to trigger READY response
        while (time.time() < timeout) and not self.ready:
            while True: # flush input
                (ev, _) = self.receive()
                if ev == Event.ERROR: # permanent failure
                    raise Exception("Device reported unrecoveable error.")
                elif ev == Event.READY:
                    self.ready = True
                    break
                else:
                    timeout = time.time() + 2

        if not self.ready:
            raise Exception("Timeout connecting to the device.")
        self.command(Command.LINE)
        self.command(Command.STATE)

    # is driver ready to receive a command
    def is_ready(self):
        if self.state == State.DIAL_ERROR:
            return False
        return self.ready

    # e.g. 'STATE' ['WAIT'] or 'RING' []
    def parse_and_process(self, cmd, params):
        if not in_enum(Event, cmd):
            return (Event.NONE, [])
        e = Event[cmd]
        if e == Event.READY:
            # Ready for next command
            self.ready = True
        elif e == Event.STATE:
            self.state = State[params[0]] if in_enum(State, params[0])  else State.UNKNOWN
        elif e == Event.LINE:
            self.lineState = LineState[params[0]] if in_enum(LineState, params[0]) else LineState.UNKNOWN
        elif e == Event.ERROR:
            self.ready = False
            raise Exception("Device reported unrecoveable error.")
        return (e, params)

    def receive(self): # tuple of event and parameters
        line = self.conn.recv_cmd()
        if line:
            line = line.split()
            cmd = line[0]
            params = line[1:]
            return self.parse_and_process(cmd, params)
        return (Event.NONE, [])

    def command(self, cmd: Command):
        if not self.is_ready():
            return False
        self.ready = False
        # Send command
        self.conn.send_cmd(cmd.name)
        while True:
            (e, params) = self.receive()
            if e == Event.READY or e == Event.INVALID:
                return e

    def get_state(self):
        return self.state

    def get_line_state(self):
        return self.lineState
