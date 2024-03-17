import os
import pygame
import soundfile as sf

from .widgets import Animation, Timer, Drawable, AbstractButton
from .util import Box, StreamAudioPlayer

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


class RotaryDial:

    class RotaryDialButton(AbstractButton):
        def __init__(self, key, pos, radius):
            super().__init__()
            self.key = key
            self.pos = pos
            self.radius = radius
            self.debug = False

            size = (radius*2 + 1, radius*2 + 1)
            center = (radius, radius)
            self.surface0 = pygame.Surface(size)
            self.surface0.set_colorkey((0, 0, 0))
            self.surface0.set_alpha(200)
            pygame.draw.circle(self.surface0, 'white', center, self.radius)

            self.surface1 = pygame.Surface(size)
            self.surface1.set_colorkey((0, 0, 0))
            self.surface1.set_alpha(128)
            pygame.draw.circle(self.surface1, 'green', center, self.radius)

        def hittest(self, pos):
            return self.pos.distance_to(pos) < self.radius

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

        # samplelen = len(self.rewind) / samplerate
        samplelen = 0.1
        time = steps * samplelen
        rewindanim = Animation(
            Animation.easeLin, time, lambda t: self.rotation(angle * (1 - t)))
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

        # samplelen = len(self.rewind) / samplerate
        samplelen = 0.1
        time = 0.3 + count * samplelen
        rewindanim = Animation(
            Animation.easeLin, time, lambda t: self.rotation(-angle * (1 - t)))
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
        self.streamplayer.queue_audio(self.wind, count+1)
        # samplelen = len(self.wind) / samplerate
        samplelen = 0.05
        time = 0.2 + count * samplelen
        self.anim = Animation(Animation.easeLin, time,
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
                b.draw(surface)
