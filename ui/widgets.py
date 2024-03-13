import math
import pygame


class Animation:
    def __init__(self, easing, t, callback):
        self.easing = easing
        self.callback = callback
        self.timer = Timer(t)
        self.next = None

    def update(self, dt):
        ret = self.timer.update(dt)
        self.callback(self.easing(self.timer.progress()))
        return ret

    @staticmethod
    def easeOutExpo(t):
        return 1 - math.pow(2, -10 * t)

    @staticmethod
    def easeOutCirc(t):
        return math.sqrt(1 - math.pow(t - 1, 2))

    @staticmethod
    def easeInQuint(t):
        return t * t * t

    @staticmethod
    def easeLin(t):
        return t


class Drawable():
    def __init__(self, surface):
        self.rect = surface.get_rect()
        self.surface = surface
        self.rotation = 0

    def update(self, dt):
        pass

    def draw(self, screen):
        if self.rotation:
            surface = pygame.transform.rotate(self.surface, self.rotation)
            rect = surface.get_rect()
            rect.center = self.rect.center
            screen.blit(surface, rect)
        else:
            screen.blit(self.surface, self.rect)


class Button:
    def __init__(self, font, text, rect, highlightcolor='green', highlighttext=None, disabledhighlightcolor=None):
        self.text = text
        self.settext(font, text, highlighttext)
        self.rect = rect
        self.highlight = False
        self.clicked = False
        self.hover = False
        self.pressed = False
        self.highlightcolor = highlightcolor
        self.disabledhighlightcolor = disabledhighlightcolor if disabledhighlightcolor else self.highlightcolor
        self.disabled = False
        self.clickable = True
        self.hidden = False

    def update(self, dt):
        self.clicked = False
        if not self.clickable:
            return
        r = self.rect
        (l, _, _) = pygame.mouse.get_pressed()
        hover = r.collidepoint(pygame.mouse.get_pos())
        if hover and not self.hover and not l:
            self.hover = hover
        elif not hover:
            self.hover = hover
        self.clicked = self.pressed and not l and not self.disabled
        self.pressed = self.hover and l and not self.disabled

    def draw(self, screen):
        if self.hidden:
            return
        r = self.rect

        # Render outlines and container
        if self.pressed:
            r = pygame.Rect(
                r.left - 5, r.top + 5, r.width, r.height)
        else:
            pygame.draw.rect(screen, "lightgrey" if self.disabled else 'lightgreen', pygame.Rect(
                r.left - 5, r.top + 5, r.width + 5, r.height), width=0, border_radius=5)

        pygame.draw.rect(screen, "black", r, width=0, border_radius=5)
        if self.highlight:
            hcolor = self.disabledhighlightcolor if self.disabled else self.highlightcolor
            pygame.draw.rect(screen, hcolor, r.inflate(-15, -15),
                             width=0, border_radius=5)

        # button outline
        pygame.draw.rect(
            screen, "grey" if (self.pressed or self.disabled) else "green", r, width=2, border_radius=5)

        # Render the text
        r2 = self.surface_std.get_rect()
        r2.center = r.center
        if self.highlight:
            screen.blit(self.surface_hilit, r2)
        else:
            screen.blit(
                self.surface_dis if self.disabled else self.surface_std, r2)

    def settext(self, font, text, highlighttext=None):
        self.surface_std = font.render(text, False, 'green')
        self.surface_hilit = font.render(
            highlighttext if highlighttext else text, False, "black")
        self.surface_dis = font.render(text, False, "grey")


class Label(Button):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.clickable = False
        self.pressed = True
        self.disabled = False

#    def draw(self, screen):
#        r = self.rect
#
#        pygame.draw.rect(screen, "black", r, width=0, border_radius=5)
#        if self.highlight:
#            hcolor = self.disabledhighlightcolor if self.disabled else self.highlightcolor
#            pygame.draw.rect(screen, hcolor, r.inflate(-15, -15),
#                             width=0, border_radius=5)
#
#        pygame.draw.rect(screen, "grey", r, width=2, border_radius=5)
#
#        r2 = self.surface0.get_rect()
#        r2.center = r.center
#        screen.blit(self.surface1 if self.highlight else self.surface2, r2)


class Blinker:
    def __init__(self, item, cycle=1.0, count=-1):
        self.item = item
        self.timer = 0
        self.disabled = False
        self.cycle = cycle
        self.count = count

    def reset(self):
        self.timer = 0

    def update(self, dt):
        if self.disabled:
            return True
        if self.count != 0:
            self.timer += dt
            if self.timer >= self.cycle:
                self.item.highlight = not self.item.highlight
                self.timer %= self.cycle
                self.count -= 1
            return False
        return True


class Timer:
    def __init__(self, timeout, callback=None):
        self.timer = 0
        self.disabled = False
        self.timeout = timeout
        self.callback = callback

    def reset(self):
        self.timer = 0

    def progress(self):
        return self.timer / self.timeout

    def update(self, dt):
        if self.disabled:
            return True

        self.timer += dt
        if self.timer >= self.timeout:
            self.timer = self.timeout
            self.disabled = True
            if self.callback:
                self.callback()
            return True
        return False


class KeyPad:
    def __init__(self, font, center):
        s = 10  # spacing
        w = h = 50
        r = pygame.Rect(0, 0, w, h)
        buttons = [
            Button(font, "1", r.move(0*(w+s), 0*(w+s)),
                   disabledhighlightcolor='green'),
            Button(font, "2", r.move(1*(w+s), 0*(w+s)),
                   disabledhighlightcolor='green'),
            Button(font, "3", r.move(2*(w+s), 0*(w+s)),
                   disabledhighlightcolor='green'),

            Button(font, "4", r.move(0*(w+s), 1*(w+s)),
                   disabledhighlightcolor='green'),
            Button(font, "5", r.move(1*(w+s), 1*(w+s)),
                   disabledhighlightcolor='green'),
            Button(font, "6", r.move(2*(w+s), 1*(w+s)),
                   disabledhighlightcolor='green'),

            Button(font, "7", r.move(0*(w+s), 2*(w+s)),
                   disabledhighlightcolor='green'),
            Button(font, "8", r.move(1*(w+s), 2*(w+s)),
                   disabledhighlightcolor='green'),
            Button(font, "9", r.move(2*(w+s), 2*(w+s)),
                   disabledhighlightcolor='green'),

            Button(font, "*", r.move(0*(w+s), 3*(w+s)),
                   disabledhighlightcolor='green'),
            Button(font, "0", r.move(1*(w+s), 3*(w+s)),
                   disabledhighlightcolor='green'),
            Button(font, "#", r.move(2*(w+s), 3*(w+s)),
                   disabledhighlightcolor='green'),
        ]
        self.rect = pygame.Rect(0, 0, 0, 0).unionall(
            [button.rect for button in buttons])
        self.rect.center = center
        for button in buttons:
            button.rect.move_ip(self.rect.left, self.rect.top)
        self.buttons = buttons
        self.disabled = False

    def button(self, key):
        return next((b for b in self.buttons if b.text == key), None)

    def update(self, dt):
        self.clicked = None
        for b in self.buttons:
            b.disabled = self.disabled
            b.update(dt)
            if b.clicked:
                self.clicked = b
        return self.clicked

    def draw(self, screen):
        for b in self.buttons:
            b.draw(screen)
