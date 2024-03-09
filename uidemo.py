
import argparse
import time
import threading
import queue

import serial.tools.list_ports
import pygame
from telephonebox import Event, State, Command, LineState, CommandConnection, Driver
from phone_util import load_model_config


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


# Dummy phone box emulator for UI testing. UI is monitoring.
def create_test_emulator(verbose_level, port, model):

    print("Test device")

    class TestDriver:
        state = State.UNKNOWN
        idx = 0
        events = [
            (Event.STATE, [State.IDLE.name]),
            (Event.STATE, [State.RING.name]),
            (Event.NONE, []),
            (Event.NONE, []),
            (Event.STATE, [State.WAIT.name]),
            (Event.STATE, [State.DIAL.name]),
            (Event.DIAL, ['1']),
            (Event.DIAL, ['2']),
            (Event.DIAL, ['3']),
            (Event.DIAL, ['4']),
            (Event.NONE, []),
            (Event.STATE, [State.DIAL_ERROR.name]),
            (Event.NONE, []),
            (Event.NONE, []),
        ]

        # cycle through the events
        def receive(self):
            time.sleep(1)
            if self.idx >= len(self.events):
                self.idx = 0
                return (Event.NONE, [])
            event = self.events[self.idx]
            if event[0] == Event.STATE:
                self.state = State[event[1][0]]
            self.idx += 1
            return event

        def get_state(self):
            return self.state

        def command_async(self, cmd: Command, params={}):
            return True

        def command(self, cmd: Command, params={}):
            return True

    return TestDriver()

# Connects to the Phonebox hardware. UI is monitoring.


def create_device_driver(verbose_level, port, model):
    config = load_model_config(model)
    if verbose_level:
        print(config)

    if not port:
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


def main():

    parser = argparse.ArgumentParser(description='Phone Demos')
    parser.add_argument(
        'demo', help="monitor, test, call, ring", default='client')
    parser.add_argument('-v', '--verbose', default=0,
                        action='count', help='verbose mode')
    parser.add_argument('-p', '--port', metavar='PORT', help='Serial port')
    parser.add_argument(
        '-m', '--model', metavar='FILE', help='Phone model file')
    # parser.add_argument(
    #    '-d', '--dummy', action='store_true', help='Dummy device')
    args = parser.parse_args()

    verbose_level = args.verbose
    server_mode = True
    if args.demo == 'test':
        driver = create_test_emulator(verbose_level, args.port, args.model)
    elif args.demo == 'monitor':
        driver = create_device_driver(verbose_level, args.port, args.model)
    elif args.demo in ['call', 'ring']:
        server_mode = False
        device = create_device_emulator(verbose_level, args.port, args.model)
    else:
        print(f'Unknown demo {args.demo}')
        exit(1)

    pygame.init()
    pygame.mouse.set_cursor(*pygame.cursors.broken_x)
    import ui.ui as ui
    if server_mode:
        ui.loop_server.running = True
        ui.loop_server(driver)
    else:
        import phone_demo
        if args.demo == 'call':
            app = phone_demo.PhoneCallDemo(device, verbose_level)
        elif args.demo == 'ring':
            app = phone_demo.PhoneRingingDemo(device, verbose_level)

        # Create thread to run the demo application
        def demo_runner():
            while ui.loop_emulation.running:
                app.loop()

        t = threading.Thread(target=demo_runner)
        ui.loop_emulation.running = True
        t.start()
        ui.loop_emulation(device)
        device.set_state(State.EXIT)  # should wake up application
        t.join()

    pygame.quit()


if __name__ == '__main__':
    main()
