import pygame
import math
from pathlib import Path
import random

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class DragonSprite:
    def __init__(self):
        asset_path = PROJECT_ROOT / "assets"

        self.body = pygame.image.load(str(asset_path / "body.png")).convert_alpha()
        self.feet = pygame.image.load(str(asset_path / "feet.png")).convert_alpha()

        self.head_closed = pygame.image.load(str(asset_path / "head_closed.png")).convert_alpha()
        self.head_half = pygame.image.load(str(asset_path / "head_half.png")).convert_alpha()
        self.head_open = pygame.image.load(str(asset_path / "head_open.png")).convert_alpha()

        self.neck = pygame.image.load(str(asset_path / "neck.png")).convert_alpha()
        self.tail = pygame.image.load(str(asset_path / "tail.png")).convert_alpha()

        self.wing_left = pygame.image.load(str(asset_path / "wing_left.png")).convert_alpha()
        self.wing_right = pygame.image.load(str(asset_path / "wing_right.png")).convert_alpha()

        self.time = 0

        self.blink_timer = random.uniform(2.0, 5.0)
        self.blink_frame = 0
        self.blinking = False

    def update(self, dt):
        self.time += dt

        self.blink_timer -= dt

        if self.blink_timer <= 0 and not self.blinking:
            self.blinking = True
            self.blink_frame = 0

        if self.blinking:
            self.blink_frame += dt * 12

            if self.blink_frame >= 3:
                self.blinking = False
                self.blink_timer = random.uniform(2.0, 5.0)

    def get_head(self):
        if not self.blinking:
            return self.head_open

        frame = int(self.blink_frame)

        if frame == 0:
            return self.head_half
        elif frame == 1:
            return self.head_closed
        else:
            return self.head_open

    def draw(self, screen, x, y):
        breathe = math.sin(self.time * 2) * 4

        screen.blit(self.tail, (x + 220, y + 120 + breathe))
        screen.blit(self.wing_left, (x + 90, y + 20 + breathe))
        screen.blit(self.wing_right, (x + 130, y + 50 + breathe))

        screen.blit(self.body, (x + 140, y + 110 + breathe))
        screen.blit(self.feet, (x + 160, y + 260 + breathe))

        screen.blit(self.neck, (x + 60, y + 70 + breathe))
        screen.blit(self.get_head(), (x, y + 20 + breathe))