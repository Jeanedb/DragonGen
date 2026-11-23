"""Translate window input to the game's fixed drawing canvas."""

import pygame

CANVAS_SIZE = (1000, 700)


def canvas_position(position):
    window = pygame.display.get_surface()
    if window is None:
        return position
    width, height = window.get_size()
    if width <= 0 or height <= 0:
        return position
    x, y = position
    canvas_width, canvas_height = CANVAS_SIZE
    return x * canvas_width // width, y * canvas_height // height


def canvas_mouse_position():
    return canvas_position(pygame.mouse.get_pos())


def canvas_event(event):
    if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
        attributes = {**event.dict, "pos": canvas_position(event.pos)}
        return pygame.event.Event(event.type, attributes)
    return event
