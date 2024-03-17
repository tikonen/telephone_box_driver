
import argparse
import time
import threading

import pygame
from telephonebox import Event, State, Command, LineState
from basicphone import BasicPhone
from phone_util import create_device_driver, create_device_emulator


class TemplateApp(BasicPhone):

    # Phone is on-hook
    def idle(self):
        print("*** IDLE (ONHOOK)")
        self.waitInState(State.IDLE)

    # Phone is off-hook and user is not dialing a number
    def wait(self):
        print("*** WAIT (OFFHOOK)")
        # play audio?
        self.waitInState(State.WAIT)

    def dial(self):
        print("*** DIAL")
        while True:
            (ev, params, state) = self.update()
            if state == State.DIAL_ERROR:
                self.dial_error()
                break
            elif state == State.WAIT:  # dial sequence has ended
                break
            elif self.driver.get_line_state() == LineState.ON_HOOK or state == State.IDLE:
                # User hang up
                break
            if ev == Event.DIAL_BEGIN:
                print("  >> DIAL_BEGIN ")
            elif ev == Event.DIAL:
                print('  >> DIAL', params[0])

    # Some error in dialing, usually means user failed to operate the rotary dial correctly.
    # If phonebox is used user must hang up to clear the state or app must send command to
    # clear the error state.
    def dial_error(self):
        # self.driver.command(Command.RESET)
        pass


def main():

    parser = argparse.ArgumentParser(description='Phone Application Template')
    parser.add_argument('-v', '--verbose', default=0,
                        action='count', help='verbose mode')
    parser.add_argument('-p', '--port', metavar='PORT',
                        help='Device serial port')
    parser.add_argument(
        '-m', '--model', metavar='FILE', help='Phone model file')
    parser.add_argument('-d', '--device', action='store_true',
                        help='Connect to device')
    args = parser.parse_args()

    verbose_level = args.verbose

    pygame.init()
    pygame.mouse.set_cursor(*pygame.cursors.broken_x)
    import ui.ui as ui
    if args.device:
        driver = create_device_driver(verbose_level, args.port, args.model)
        app = TemplateApp(driver, verbose_level)
        try:
            while True:
                app.loop()
        except KeyboardInterrupt:
            print("Exiting...")

    else:
        device = create_device_emulator(verbose_level, args.port, args.model)
        app = TemplateApp(device, verbose_level)

        # Create thread to run the demo application
        def app_runner():
            while ui.loop_emulation.running:
                app.loop()

        t = threading.Thread(target=app_runner)
        ui.loop_emulation.running = True
        t.start()
        # Start running the emulation loop
        ui.loop_emulation(device)
        device.set_state(State.EXIT)  # should wake up application
        t.join()

    pygame.quit()


if __name__ == '__main__':
    main()
