import argparse
import threading
import time
import os
import queue

import serial.tools.list_ports
import pygame

from ui import *
from telephonebox import Event, State, Command, CommandConnection, Driver
from phone_util import load_model_config
import phone_audio

# pygame setup
pygame.init()
screen = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()

center = pygame.Vector2(screen.get_width() / 2, screen.get_height() / 2)
player_pos = pygame.Vector2(screen.get_width() / 2, screen.get_height() / 2)
sysfont = pygame.font.SysFont(pygame.font.get_default_font(), 32)
sysfont_large = pygame.font.SysFont(pygame.font.get_default_font(), 50)
pygame.mouse.set_cursor(*pygame.cursors.broken_x)

##########################
# UI elements


class Drawable():
    def __init__(self, surface):
        self.rect = surface.get_rect()
        self.surface = surface

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.blit(self.surface, self.rect)


# background = Drawable(pygame.image.load(
#    os.path.join('ui', 'wall.jpg')))
# background.rect.center = center

keypad = KeyPad(sysfont, center)

hookbutton = Button(sysfont, "ON-HOOK",
                    pygame.Rect(0, 0, keypad.rect.width, 50), 'yellow', highlighttext="OFF-HOOK")
hookbutton.rect.center = (center.x, 530)

ringbutton = Button(sysfont, "RING",
                    pygame.Rect(0, 0, keypad.rect.width, 50), 'red')
ringbutton.rect.center = (center.x, 600)

dialerrorlabel = Label(sysfont, "DIAL ERROR",
                       pygame.Rect(0, 0, keypad.rect.width + 40, 50), 'red')
dialerrorlabel.rect.midbottom = keypad.rect.midtop
dialerrorlabel.rect.move_ip(0, -30)

diallabel = Label(sysfont_large, "", dialerrorlabel.rect)

dialerrorlabel.highlight = False
dialerrorlabel.hidden = True
errorblinker = Blinker(dialerrorlabel, 0.5)
selectblinker = None

ringbutton.disabled = True
hookbutton.disabled = True
hookbutton.clickable = False
hookbutton.pressed = True
keypad.disabled = True

drawables = [
    # background,
    keypad,
    hookbutton,
    ringbutton,
    dialerrorlabel,
    diallabel
]

nondrawables = [errorblinker]


class Box:
    __init__ = lambda self, **kw: setattr(self, '__dict__', kw)


effects = Box()
phone_audio.load_audio(effects)


def draw():
    # fill the screen with a color to wipe away anything from last frame
    screen.fill("black")

    r = diallabel.rect.copy()
    r = r.inflate(100, 0)
    r.height = 550
    r.move_ip(0, -40)
    pygame.draw.rect(screen, "gray40", r)
    r.inflate_ip(10, 10)
    pygame.draw.rect(screen, "gray20", r, width=10, border_radius=10)

    for elem in drawables:
        elem.draw(screen)

    # flip() the display to put your work on screen
    pygame.display.flip()


number = []


def handle_event(ev, params, state):
    global number
    global nondrawables

    if ev == Event.STATE:
        statename = params[0]
        if state == State.IDLE:
            phone_audio.stop_audio()
            number.clear()
            diallabel.settext(sysfont_large, statename)
            hookbutton.highlight = False
            ringbutton.highlight = False
            ringbutton.disabled = False
            diallabel.hidden = False
            dialerrorlabel.hidden = True
        if state == State.WAIT and len(number) == 0:
            phone_audio.play_audio(effects.dial_tone)
            diallabel.settext(sysfont_large, statename)
            hookbutton.highlight = True
            ringbutton.highlight = False
            ringbutton.disabled = True
        if state == State.DIAL and len(number) == 0:
            phone_audio.stop_audio()
            number.clear()
            diallabel.settext(sysfont_large, '-')
        if state == State.DIAL_ERROR:
            phone_audio.play_audio(effects.low_tone)
            number.clear()
            diallabel.hidden = True
            dialerrorlabel.hidden = False
            dialerrorlabel.highlight = True
            errorblinker.reset()
        if state == State.RING:
            diallabel.settext(sysfont_large, statename)
            ringbutton.highlight = True
    if ev == Event.DIAL:
        key = params[0]
        number.insert(-1, key)
        diallabel.settext(sysfont_large, ''.join(number))
        keypadbutton = keypad.button(key)
        keypadbutton.highlight = True
        nondrawables.append(Blinker(keypadbutton, 0.1, 3))


def update(dt, event):
    global nondrawables

    if event:
        (ev, params, state) = event
        if ev != Event.NONE:
            handle_event(ev, params, state)

    for elem in drawables:
        elem.update(dt)

    if ringbutton.clicked:
        if driver.get_state() == State.RING:
            driver.command_async(Command.STOP)
        else:
            driver.command_async(Command.RING)

    # Update nondrawables and remove them from list if they are done
    nondrawables = [elem for elem in nondrawables if not elem.update(dt)]

    return True


def loop(driver):
    dt = 0
    FPS = 30
    q = queue.Queue()

    # Thread worker reads the driver events and queues them for the main loop
    def driver_reader():
        nonlocal driver
        while loop.running:
            (ev, params) = driver.receive()
            if ev != Event.NONE:
                print(ev, params)
                q.put((ev, params, driver.get_state()))

    t = threading.Thread(target=driver_reader)
    t.start()

    try:
        while loop.running:
            # pygame.QUIT event means the user clicked X to close your window
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    loop.running = False

            # Dequeue events from the driver
            ev = None
            if not q.empty():
                ev = q.get_nowait()

            if not update(dt, ev):
                break
            draw()
            # limits FPS
            # dt is delta time in seconds since last frame, used for
            # framerate-independent animation.
            dt = clock.tick(FPS) / 1000
    except KeyboardInterrupt:
        pass

    print("Exiting...")
    loop.running = False
    t.join()


def create_dummy_driver(verbose_level, port, model):

    print("Dummy device")

    class DummyDriver:
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

    return DummyDriver()


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


parser = argparse.ArgumentParser(description='Phone Demos')
parser.add_argument('-v', '--verbose', default=0,
                    action='count', help='verbose mode')
parser.add_argument('-p', '--port', metavar='PORT', help='Serial port')
parser.add_argument(
    '-m', '--model', metavar='FILE', help='Phone model file')
parser.add_argument(
    '-d', '--dummy', action='store_true', help='Dummy device')
args = parser.parse_args()

port = None
verbose_level = args.verbose

if args.dummy:
    driver = create_dummy_driver(verbose_level, args.port, args.model)
else:
    driver = create_device_driver(verbose_level, args.port, args.model)

loop.running = True
loop(driver)

pygame.quit()
