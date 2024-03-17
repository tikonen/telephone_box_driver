
import argparse
import time
import threading

import pygame
from telephonebox import Event, State, Command
from phone_util import create_device_driver, create_device_emulator

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
