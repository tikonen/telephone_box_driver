import math
import pygame


class Animation:
    def __init__(self, easing, t, onupdate, onend=None):
        self.easing = easing
        self.on_update = onupdate
        self.timer = Timer(t)
        self.next = None
        self.on_end = onend

    def update(self, dt):
        ret = self.timer.update(dt)
        self.on_update(self.easing(self.timer.progress()))
        if ret and self.on_end:
            self.on_end()
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

    @staticmethod
    def easeOutQuad(t):
        return 1 - (1 - t) * (1 - t)


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


class AbstractButton:

    mouse = (False, False, False)
    position = (0, 0)

    def __init__(self):
        self.highlight = False
        self.clicked = False
        self.hover = False
        self.pressed = False
        self.disabled = False
        self.clickable = True
        self.hidden = False
        self.drag = False
        self.dragstart = False
        self.dragend = False

    def hittest(self, pos):
        raise "Not Implemented"

    def update(self, dt):
        self.clicked = False
        if not self.clickable:
            return
        (l, _, _) = AbstractButton.mouse
        hover = self.hittest(AbstractButton.position)
        # (l, _, _) = pygame.mouse.get_pressed()
        # hover = self.hittest(pygame.mouse.get_pos())
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
        pass


class Button(AbstractButton):
    def __init__(self, font, text, rect, highlightcolor='green', highlighttext=None, disabledhighlightcolor=None):
        super().__init__()
        self.rect = rect
        self.text = text
        self.settext(font, text, highlighttext)
        self.highlightcolor = highlightcolor
        self.disabledhighlightcolor = disabledhighlightcolor if disabledhighlightcolor else self.highlightcolor

    def hittest(self, pos):
        return self.rect.collidepoint(pos)

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
    def __init__(self, timeout, onexpire=None):
        self.timer = 0
        self.disabled = False
        self.timeout = timeout
        self.on_expire = onexpire

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
            if self.on_expire:
                self.on_expire()
            return True
        return False
