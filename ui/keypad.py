import pygame

from .widgets import Button


class KeyPad:
    def __init__(self, font, center):
        SPACING = 10  # spacing
        WIDTH = HEIGHT = 50
        rect = pygame.Rect(0, 0, WIDTH, HEIGHT)
        # DTMF supported keys
        all_keys = [['1', '2', '3', 'A'],
                    ['4', '5', '6', 'B'],
                    ['7', '8', '9', 'C'],
                    ['*', '0', '#', 'D']]
        standard_keys = [['1', '2', '3'],
                         ['4', '5', '6'],
                         ['7', '8', '9'],
                         ['*', '0', '#']]
        buttons = [Button(font, key, rect.move(c*(WIDTH+SPACING), r*(HEIGHT+SPACING)))
                   for (r, row) in enumerate(standard_keys) for (c, key) in enumerate(row)]

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
