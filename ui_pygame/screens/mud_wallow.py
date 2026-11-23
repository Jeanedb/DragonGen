import pygame

from ui_pygame.core.coordinates import canvas_mouse_position

from core.sim.mudwing import (
    rest_sibs_at_wallow, resting_sibs, sib_group_label, sib_groups, wallow_reopens_moon,
)
from ui_pygame.core.base_screen import BaseScreen
from ui_pygame.screens.locations import BRONZE, GOLD, MUTED, PARCHMENT, FantasyButton


class MudWallowScreen(BaseScreen):
    def __init__(self, world, change_screen):
        super().__init__()
        self.world = world
        self.change_screen = change_screen
        self.group_index = 0
        self.title = pygame.font.SysFont("georgia", 32, bold=True)
        self.heading = pygame.font.SysFont("georgia", 23, bold=True)
        self.body = pygame.font.SysFont("georgia", 17)
        self.button_font = pygame.font.SysFont("georgia", 15, bold=True)

    def cycle_group(self, offset, count):
        self.group_index = (self.group_index + offset) % count

    def draw_centered(self, screen, text, y, font, color):
        label = font.render(text, True, color)
        screen.blit(label, label.get_rect(midtop=(500, y)))

    def draw(self, screen):
        self.buttons.clear()
        screen.fill((28, 27, 20))
        panel = pygame.Rect(150, 62, 700, 512)
        pygame.draw.rect(screen, (41, 35, 25), panel, border_radius=16)
        pygame.draw.rect(screen, BRONZE, panel, width=2, border_radius=16)
        self.draw_centered(screen, "THE MUD WALLOW", 91, self.title, GOLD)
        self.draw_centered(
            screen, "Choose a sib group to rest together once per moon.", 151, self.body, PARCHMENT
        )
        self.draw_centered(
            screen, "Resting reduces fatigue and builds trust between participating sibs.", 180, self.body, MUTED
        )
        pygame.draw.line(screen, BRONZE, (199, 225), (801, 225))

        groups = [(key, resting_sibs(members)) for key, members in sib_groups(self.world).items()]
        groups = [(key, members) for key, members in groups if members]
        used = self.world.world_flags.get("last_wallow_moon") == self.world.moon
        reopens = wallow_reopens_moon(self.world)
        flooded = self.world.moon < reopens
        if groups:
            self.group_index %= len(groups)
            group_id, members = groups[self.group_index]
            self.draw_centered(screen, sib_group_label(group_id), 250, self.heading, GOLD)
            self.draw_wrapped_text(
                screen, ", ".join(dragon.name for dragon in members), 225, 300, 550, self.body, PARCHMENT
            )
            if len(groups) > 1:
                self.buttons.extend([
                    FantasyButton((220, 390, 145, 38), "PREVIOUS", lambda: self.cycle_group(-1, len(groups))),
                    FantasyButton((635, 390, 145, 38), "NEXT", lambda: self.cycle_group(1, len(groups))),
                ])
            if not (used or flooded) and len(members) >= 2:
                self.buttons.append(FantasyButton(
                    (405, 471, 190, 40),
                    "REST TOGETHER",
                    lambda: rest_sibs_at_wallow(self.world, group_id),
                ))
            elif not (used or flooded):
                self.draw_centered(screen, "At least two healthy sibs are needed.", 478, self.body, MUTED)
        else:
            self.draw_centered(screen, "No healthy sibs are available to rest.", 254, self.body, MUTED)

        if flooded:
            self.draw_centered(screen, f"Flooded until Moon {reopens}.", 478, self.body, PARCHMENT)
        elif used:
            self.draw_centered(screen, "The tribe has used the wallow this moon.", 478, self.body, PARCHMENT)
        self.buttons.append(FantasyButton(
            (390, 622, 220, 42), "RETURN TO MAP", lambda: self.change_screen("locations")
        ))
        mouse = canvas_mouse_position()
        for button in self.buttons:
            button.draw(screen, self.button_font, mouse)

    def handle_event(self, event):
        self.handle_button_events(event)
