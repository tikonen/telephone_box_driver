import threading
import queue

import pygame

from .widgets import *
from .util import *
from .rotarydial import RotaryDial
from .keypad import KeyPad
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

rotarydial = RotaryDial((230, center.y))

drawables = [
    keypad,
    hookbutton,
    ringbutton,
    dialerrorlabel,
    diallabel,
    rotarydial
]

tasks = [errorblinker]

effects = Box()
phone_audio.load_audio(effects)


def draw_base():
    pygame.draw.rect(screen, "gray40", draw_base.r)
    pygame.draw.rect(screen, "gray20", draw_base.r.inflate(
        10, 10), width=10, border_radius=10)


draw_base.r = diallabel.rect.copy()
draw_base.r.inflate_ip(100, 0)
draw_base.r.height = 550
draw_base.r.move_ip(0, -40)


def draw():
    # fill the screen with a color to wipe away anything from last frame
    screen.fill("midnightblue")
    draw_base()

    for elem in drawables:
        elem.draw(screen)

    # flip() the display to put your work on screen
    pygame.display.flip()


number = []

# Process events from the Phonebox


def handle_event(ev, params, state):
    global number
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
        number.append(key)
        number = number[-9:]
        diallabel.settext(sysfont_large, ''.join(number))
        keypadbutton = keypad.button(key)
        keypadbutton.highlight = True
        tasks.append(Blinker(keypadbutton, 0.1, 3))

# Loop for the phonebox device.


def loop_server(driver):
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

            AbstractButton.mouse = pygame.mouse.get_pressed()
            AbstractButton.position = pygame.mouse.get_pos()

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
                elif driver.get_state() == State.IDLE:
                    driver.command_async(Command.RING)

            # Update tasks and remove them from list if they are done
            tasks[:] = [
                elem for elem in tasks if not elem.update(dt)]

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
    number = []

    ringbutton.disabled = True
    ringbutton.clickable = False
    ringbutton.pressed = True
    hookbutton.disabled = False
    hookbutton.clickable = True
    hookbutton.pressed = False
    keypad.disabled = True
    diallabel.settext(sysfont_large, 'READY')

    dt = 0
    FPS = 30

    dtmfplayer = phone_audio.create_dtmf_player()
    dtmfplayer.start()

    ringing = phone_audio.load_file('phone_ringing.wav')

    ringing_tasks = []

    KEYMAP = {
        pygame.K_0: 0,
        pygame.K_1: 1,
        pygame.K_2: 2,
        pygame.K_3: 3,
        pygame.K_4: 4,
        pygame.K_5: 5,
        pygame.K_6: 6,
        pygame.K_7: 7,
        pygame.K_8: 8,
        pygame.K_9: 9,
        pygame.K_HASH: '#',
        pygame.K_ASTERISK: '*',

        # keypad
        #
        pygame.K_KP0: 0,
        pygame.K_KP1: 1,
        pygame.K_KP2: 2,
        pygame.K_KP3: 3,
        pygame.K_KP4: 4,
        pygame.K_KP5: 5,
        pygame.K_KP6: 6,
        pygame.K_KP7: 7,
        pygame.K_KP8: 8,
        pygame.K_KP9: 9,
        pygame.K_KP_DIVIDE: '#',
        pygame.K_KP_MULTIPLY: '*'

    }

    def check_key_event(event):
        if event.type in (pygame.KEYDOWN, pygame.KEYUP):
            if event.key in KEYMAP:
                return (True, KEYMAP[event.key])
        return (False, None)

    def on_keypad_clicked(kpbutton):
        kpbutton.highlight = True
        tasks.append(Blinker(kpbutton, 0.1, 3))
        key = kpbutton.text
        dtmfplayer.beep(key)
        number.append(key)
        number[:] = number[-9:]  # keep last 9 numbers
        diallabel.settext(sysfont_large, ''.join(number))
        driver.set_state(State.DIAL)
        driver.put_event(Event.DIAL_BEGIN)
        driver.put_event(Event.DIAL, [key])
        driver.set_state(State.WAIT)

    def toggle_hook_state():
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
            ringing_tasks.clear()
        else:
            # going on hook
            driver.set_line_state(LineState.ON_HOOK)
            driver.set_state(State.IDLE)
            diallabel.settext(sysfont_large, 'READY')

    try:
        while loop_emulation.running:
            # pygame.QUIT event means the user clicked X to close your window
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    loop_emulation.running = False
                    break
                else:
                    (match, key) = check_key_event(event)
                    if match:
                        if False:
                            if event.type == pygame.KEYDOWN:
                                if type(key) is int:
                                    rotarydial.dial_wind(key)
                                    if driver.get_state() == State.WAIT:
                                        driver.set_state(State.DIAL)
                                        driver.put_event(Event.DIAL_BEGIN)
                            elif event.type == pygame.KEYUP:
                                rotarydial.dial_rewind(key)
                        elif driver.get_state() == State.WAIT:
                            if event.type == pygame.KEYDOWN:
                                on_keypad_clicked(keypad.button(str(key)))
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        toggle_hook_state()

            AbstractButton.mouse = pygame.mouse.get_pressed()
            AbstractButton.position = pygame.mouse.get_pos()

            # Dequeue commands from the driver
            (cmd, _) = driver.receive_cmd()
            if cmd == Command.RING:
                ringbutton.highlight = True
                ringing_tasks.append(Blinker(ringbutton, 0.3))
                # ring expiration timer
                ringing_tasks.append(Timer(
                    30, lambda: driver.command(Command.STOP)))
                driver.set_state(State.RING)
                phone_audio.play_audio(ringing)
            elif cmd == Command.STOP and driver.get_state() == State.RING:
                ringbutton.highlight = False
                ringing_tasks.clear()
                driver.set_state(State.IDLE)
                phone_audio.stop_audio()

            for elem in drawables:
                elem.update(dt)

            if rotarydial.clicked:
                b = rotarydial.clicked
                if b.dragstart:
                    rotarydial.dial_wind(int(b.key))
                    if driver.get_state() == State.WAIT:
                        driver.set_state(State.DIAL)
                        driver.put_event(Event.DIAL_BEGIN)
                elif b.dragend:
                    rotarydial.dial_rewind(int(b.key))
            if rotarydial.dialed is not None:
                key = rotarydial.dialed
                print("ROTARY: ", key)
                if driver.get_state() == State.DIAL:
                    if key >= 0:
                        number.append(str(key))
                        number = number[-9:]  # keep last 9 numbers
                        diallabel.settext(sysfont_large, ''.join(number))
                        driver.put_event(Event.DIAL, [str(key)])
                    driver.set_state(State.WAIT)

            if hookbutton.clicked:
                toggle_hook_state()

            if keypad.clicked:
                on_keypad_clicked(keypad.clicked)

            # Update tasks and remove them from list if they are done
            tasks[:] = [
                elem for elem in tasks if not elem.update(dt)]
            ringing_tasks[:] = [
                elem for elem in ringing_tasks if not elem.update(dt)]

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
