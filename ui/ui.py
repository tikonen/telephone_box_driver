
import threading
import queue

import pygame

from .widgets import *
from telephonebox import Event, State, Command, LineState
import phone_audio

# pygame setup
screen = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()

center = pygame.Vector2(screen.get_width() / 2, screen.get_height() / 2)
player_pos = pygame.Vector2(screen.get_width() / 2, screen.get_height() / 2)
sysfont = pygame.font.SysFont(pygame.font.get_default_font(), 32)
sysfont_large = pygame.font.SysFont(pygame.font.get_default_font(), 50)


##########################
# UI elements

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

# Loop for the phone device.


def loop_server(driver):
    global nondrawables

    ringbutton.disabled = True
    hookbutton.disabled = True
    hookbutton.clickable = False
    hookbutton.pressed = True
    keypad.disabled = True

    dt = 0
    FPS = 30
    q = queue.Queue()

    # Thread worker reads the driver events and queues them for the main loop
    def driver_reader():
        nonlocal driver
        while loop_server.running:
            (ev, params) = driver.receive()
            if ev != Event.NONE:
                print(ev, params)
                q.put((ev, params, driver.get_state()))

    t = threading.Thread(target=driver_reader)
    t.start()

    try:
        while loop_server.running:
            # pygame.QUIT event means the user clicked X to close your window
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    loop_server.running = False
                    break

            # Dequeue events from the driver
            if not q.empty():
                (ev, params, state) = q.get_nowait()
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
            nondrawables = [
                elem for elem in nondrawables if not elem.update(dt)]

            draw()
            # limits FPS
            # dt is delta time in seconds since last frame, used for
            # framerate-independent animation.
            dt = clock.tick(FPS) / 1000
    except KeyboardInterrupt:
        pass

    print("Exiting...")
    loop_server.running = False
    t.join()

# Loop to emulate a phone


def loop_emulation(driver):
    global nondrawables
    global number

    ringbutton.disabled = True
    ringbutton.clickable = False
    ringbutton.pressed = True
    hookbutton.disabled = False
    hookbutton.clickable = True
    hookbutton.pressed = False
    keypad.disabled = True

    dt = 0
    FPS = 30

    ringblinker = None
    dtmfplayer = phone_audio.create_dtmf_player()
    dtmfplayer.start()

    ringing = phone_audio.load_file('phone_ringing.wav')

    try:
        while loop_emulation.running:
            # pygame.QUIT event means the user clicked X to close your window
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    loop_emulation.running = False
                    break

            # Dequeue commands from the driver
            (cmd, _) = driver.receive_cmd()
            if cmd == Command.RING:
                ringbutton.highlight = True
                ringblinker = Blinker(ringbutton, 0.5, 100)
                driver.set_state(State.RING)
                phone_audio.play_audio(ringing)
            elif cmd == Command.STOP:
                ringbutton.highlight = False
                ringblinker = None
                driver.set_state(State.WAIT)
                phone_audio.stop_audio()

            if ringblinker:
                if ringblinker.update(dt):
                    ringblinker = None
                    ringbutton.highlight = False
                    driver.set_state(State.WAIT)

            for elem in drawables:
                elem.update(dt)

            if hookbutton.clicked:
                hookbutton.highlight = not hookbutton.highlight
                keypad.disabled = not hookbutton.highlight
                if hookbutton.highlight:
                    # going off-hook
                    phone_audio.stop_audio()
                    number.clear()
                    driver.set_line_state(LineState.OFF_HOOK)
                    if driver.get_state() == State.RING:
                        dtmfplayer.beep('A')  # just some sound
                        diallabel.settext(sysfont_large, 'CALL')
                    else:
                        diallabel.settext(sysfont_large, '-')
                    driver.set_state(State.WAIT)
                    ringbutton.highlight = False
                    ringblinker = None
                else:
                    # going on hook
                    driver.set_line_state(LineState.ON_HOOK)
                    driver.set_state(State.IDLE)
                    diallabel.settext(sysfont_large, 'READY')

            if keypad.clicked:
                kpbutton = keypad.clicked
                kpbutton.highlight = True
                nondrawables.append(Blinker(kpbutton, 0.1, 3))
                key = kpbutton.text
                dtmfplayer.beep(key)
                number.append(key)
                diallabel.settext(sysfont_large, ''.join(number))
                driver.set_state(State.DIAL)
                driver.put_event(Event.DIAL_BEGIN)
                driver.put_event(Event.DIAL, [key])
                driver.set_state(State.WAIT)

            # Update nondrawables and remove them from list if they are done
            nondrawables = [
                elem for elem in nondrawables if not elem.update(dt)]

            draw()
            # limits FPS
            # dt is delta time in seconds since last frame, used for
            # framerate-independent animation.
            dt = clock.tick(FPS) / 1000
    except KeyboardInterrupt:
        pass

    dtmfplayer.stop()
    print("Exiting...")
    loop_emulation.running = False
