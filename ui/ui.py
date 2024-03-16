import os
import threading
import queue

import soundfile as sf
import sounddevice as sd
import numpy as np
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

ASSET_DIR = 'assets'
DP_BASE = 'dialphone_base.png'
DP_DIAL = 'dialphone_dial.png'
DP_FINGERHOOK = 'dialphone_fingerhook.png'


def load_rotarydial_assets(obj):
    assetpath = os.path.join(os.path.dirname(__file__), ASSET_DIR)
    obj.dp_base = pygame.image.load(os.path.join(assetpath, DP_BASE))
    obj.dp_dial = pygame.image.load(os.path.join(assetpath, DP_DIAL))
    obj.dp_fingerhook = pygame.image.load(
        os.path.join(assetpath, DP_FINGERHOOK))


class StreamAudioPlayer():
    def __init__(self, samplerate, channels, dtype='float32'):
        self.samplerate = samplerate
        self.channels = channels
        self.dtype = dtype
        self.blocksize = 1024

    def start_audio(self):
        self.q = queue.Queue()

        def callback(outdata, frames, time, status):
            if not self.q.empty():
                data = self.q.get_nowait()
                outdata[:] = data
            else:
                outdata.fill(0)

        self.outs = sd.OutputStream(
            samplerate=self.samplerate, dtype=self.dtype, latency=0.1, blocksize=self.blocksize, channels=self.channels, callback=callback)
        self.outs.start()

    def queue_audio(self, sample, repeats):
        blocksize = self.blocksize
        audiodata = np.concatenate(
            [sample for _ in range(0, repeats)], dtype=self.dtype)
        audiodata = audiodata.reshape(-1, 1)
        for idx in range(blocksize, len(audiodata), blocksize):
            self.q.put(audiodata[idx-blocksize:idx])

        rem = len(audiodata) % blocksize
        if rem:
            block = np.zeros((blocksize, 1), dtype=audiodata.dtype)
            block[:rem] = audiodata[len(audiodata) - rem:]
            self.q.put(block)

    def clear_audio(self):
        self.q = queue.Queue()

##########################
# UI elements


class Box:  # Helper class
    __init__ = lambda self, **kw: setattr(self, '__dict__', kw)


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


class RotaryDial:

    class RotaryDialButton:
        def __init__(self, key, pos, radius):
            self.key = key
            self.pos = pos
            self.radius = radius
            self.hover = False
            self.clicked = False
            self.pressed = False
            self.clickable = True
            self.disabled = False
            self.drag = False
            self.dragstart = False
            self.dragend = False
            self.debug = False

            radius = 25
            self.surface0 = pygame.Surface((radius*2+1, radius*2+1))
            self.surface0.set_colorkey((0, 0, 0))
            self.surface0.set_alpha(200)
            pygame.draw.circle(self.surface0, 'white',
                               (radius, radius), self.radius)

            self.surface1 = pygame.Surface((radius*2+1, radius*2+1))
            self.surface1.set_colorkey((0, 0, 0))
            self.surface1.set_alpha(128)
            pygame.draw.circle(self.surface1, 'green',
                               (radius, radius), self.radius)

        def update(self, dt):
            self.clicked = False
            if not self.clickable:
                return
            (l, _, _) = pygame.mouse.get_pressed()
            hover = self.pos.distance_to(pygame.mouse.get_pos()) < self.radius

            if hover and not self.hover and not l:
                self.hover = hover
            elif not hover:
                self.hover = hover
            self.clicked = self.pressed and not l and not self.disabled
            drag = l and (self.drag or (self.pressed and not hover))
            self.dragstart = not self.drag and drag
            self.dragend = self.drag and not drag
            self.drag = drag
            self.pressed = self.hover and l and not self.disabled

        def draw(self, screen):
            self.surface0.blit(screen, self.pos)
            r = self.surface0.get_rect()
            r.center = self.pos
            if self.hover:
                screen.blit(
                    self.surface1 if self.pressed else self.surface0, r)

            if self.debug:
                color = 'green' if self.drag else (
                    'blue' if self.pressed else 'red')
                pygame.draw.circle(screen, color, self.pos, self.radius)

    def __init__(self, center):
        self.anim = None
        self.in_winding = False
        self.in_hold = False
        self.dialed = None
        self.clicked = None
        assets = Box()
        load_rotarydial_assets(assets)

        self.dp_base = Drawable(assets.dp_base)
        self.dp_base.rect.center = center
        self.dp_dial = Drawable(assets.dp_dial)
        self.dp_fingerhook = Drawable(assets.dp_fingerhook)
        self.dp_dial.rect.center = self.dp_base.rect.center
        self.dp_fingerhook.rect.center = self.dp_base.rect.center
        self.dp_fingerhook.rect.move_ip(68, 125)

        self.buttons = []
        pos = pygame.math.Vector2(0, 120)
        nums = [0] + list(range(9, 0, -1))
        for n in range(0, 10):
            bpos = pos.rotate(
                n * (360/13)) + self.dp_dial.rect.center
            button = RotaryDial.RotaryDialButton(str(nums[n]), bpos, 25)
            self.buttons.append(button)

        assetpath = os.path.join(os.path.dirname(__file__), ASSET_DIR)
        (self.wind, samplerate) = sf.read(
            os.path.join(assetpath, 'phone_wind.wav'), dtype='float32')
        (self.rewind, samplerate) = sf.read(
            os.path.join(assetpath, 'phone_rewind.wav'), dtype='float32')

        self.streamplayer = StreamAudioPlayer(
            samplerate=samplerate, channels=1, dtype=self.wind.dtype)
        self.streamplayer.start_audio()

    def rotation(self, angle):
        self.dp_dial.rotation = angle

    def _winding_end(self):
        self.in_hold = True

    def _rewinding_end(self, dialed):
        self.in_winding = False
        self.dialed = dialed
        self.rotation(0)

    def dial_cancel(self):
        # winding is canceled. Dial returns to starting position from the current position
        if not self.in_winding:
            return

        self.streamplayer.clear_audio()

        angle = self.dp_dial.rotation
        steps = abs(angle / (360/13))

        rewindanim = Animation(
            Animation.easeLin, steps * 0.1, lambda t: self.rotation(angle * (1 - t)))
        steps = round(steps) - 1
        if steps > 0:
            self.streamplayer.queue_audio(self.rewind, round(steps))

        # rewindanim.onend = lambda: self._rewinding_end(-1)
        steps -= 1
        if steps <= 0:
            steps = -1
        rewindanim.on_end = lambda: self._rewinding_end(steps)
        self.anim = rewindanim

    def dial_rewind(self, n, cancel=True):
        # dial is released and starts rewinding back to the starting position
        if not self.in_winding:
            return
        if cancel and not self.in_hold:
            self.dial_cancel()
            return
        self.in_hold = False
        count = n if n != 0 else 10
        angle = (count + 2) * (360/13)
        angle -= 5  # tweak angle to fit assets better

        rewindanim = Animation(
            Animation.easeLin, 0.3 + count * 0.1, lambda t: self.rotation(-angle * (1 - t)))
        rewindanim.on_end = lambda: self._rewinding_end(n)

        if self.anim:
            # Pause
            self.anim.next = Timer(
                0.2, lambda: self.streamplayer.queue_audio(self.rewind, count + 2))
            # Rewind
            self.anim.next.next = rewindanim
        else:
            # Rewind
            self.streamplayer.queue_audio(self.rewind, count + 2)
            self.anim = rewindanim

    def dial_wind(self, n):
        # dial winds the selected number position back until it reaches the stop (fingerguard)
        if self.in_winding:
            return
        self.in_winding = True
        count = n if n != 0 else 10
        angle = (count + 2) * (360/13)
        angle -= 5  # tweak angle to fit assets better

        # Setup animation and effects
        self.streamplayer.queue_audio(self.wind, count+2)
        self.anim = Animation(Animation.easeLin, 0.3 + count*0.1,
                              lambda t: self.rotation(-angle * t))
        self.anim.on_end = lambda: self._winding_end()

    def update(self, dt):
        self.clicked = None
        self.dialed = None
        if self.anim and self.anim.update(dt):
            self.anim = self.anim.next

        for b in self.buttons:
            b.update(dt)
            if not self.in_winding and b.clicked or b.dragstart or b.dragend:
                self.clicked = b

    def draw(self, surface):
        self.dp_base.draw(surface)
        self.dp_dial.draw(surface)
        self.dp_fingerhook.draw(surface)

        if not self.in_winding:
            for b in self.buttons:
                b.draw(screen)


rotarydial = RotaryDial((230, center.y))

drawables = [
    # background,
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


def draw():
    # fill the screen with a color to wipe away anything from last frame
    screen.fill("midnightblue")

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
    global tasks
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
            tasks = [
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
    global tasks
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

    try:
        while loop_emulation.running:
            # pygame.QUIT event means the user clicked X to close your window
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    loop_emulation.running = False
                    break
                elif event.type == pygame.KEYDOWN:
                    if event.key >= pygame.K_0 and event.key <= pygame.K_9:
                        rotarydial.dial_wind(event.key - pygame.K_0)
                elif event.type == pygame.KEYUP:
                    if event.key >= pygame.K_0 and event.key <= pygame.K_9:
                        rotarydial.dial_rewind(event.key - pygame.K_0)

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
                elif b.dragend:
                    rotarydial.dial_rewind(int(b.key))
            if rotarydial.dialed is not None:
                key = rotarydial.dialed
                print("ROTARY: ", key)
                if key >= 0:
                    number.append(str(key))
                    number = number[-9:]  # keep last 9 numbers
                    diallabel.settext(sysfont_large, ''.join(number))

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
                    ringing_tasks.clear()
                else:
                    # going on hook
                    driver.set_line_state(LineState.ON_HOOK)
                    driver.set_state(State.IDLE)
                    diallabel.settext(sysfont_large, 'READY')

            if keypad.clicked:
                kpbutton = keypad.clicked
                kpbutton.highlight = True
                tasks.append(Blinker(kpbutton, 0.1, 3))
                key = kpbutton.text
                dtmfplayer.beep(key)
                number.append(key)
                number = number[-9:]  # keep last 9 numbers
                diallabel.settext(sysfont_large, ''.join(number))
                driver.set_state(State.DIAL)
                driver.put_event(Event.DIAL_BEGIN)
                driver.put_event(Event.DIAL, [key])
                driver.set_state(State.WAIT)

            # Update tasks and remove them from list if they are done
            tasks = [
                elem for elem in tasks if not elem.update(dt)]
            ringing_tasks = [
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
