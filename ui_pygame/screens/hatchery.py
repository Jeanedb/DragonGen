import random
import pygame
from pathlib import Path

from ui_pygame.core.base_screen import BaseScreen
from ui_pygame.widgets.button import Button

WIDTH, HEIGHT = 1000, 700

TEXT = (230, 230, 230)
MUTED = (180, 180, 180)
GOLD = (242, 201, 76)
RED = (235, 87, 87)


class HatcheryScreen(BaseScreen):

    def __init__(self, world, change_screen):
        super().__init__()

        self.selected_egg_index = 0
        self.egg_scroll = 0

        self.world = world
        self.change_screen = change_screen
        self.log_scroll = 0

        self.selected_dragon = None

        self.list_scroll = 0

        project_root = Path(__file__).resolve().parents[2]
        bg_path = project_root / "assets" / "menu" / "training_bg.png"

        try:
            self.bg_image = pygame.image.load(str(bg_path)).convert()
            self.bg_image = pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT))
        except Exception:
            self.bg_image = None

        egg_path = project_root / "assets" / "hatchery" / "egg.png"

        try:
            self.egg_image = pygame.image.load(str(egg_path)).convert_alpha()
            self.egg_image = pygame.transform.smoothscale(
                self.egg_image,
                (90, 90)
            )
        except Exception:
            self.egg_image = None

    def get_selected_egg(self):
        eggs = getattr(self.world, "eggs", [])

        if not eggs:
            return None

        self.selected_egg_index %= len(eggs)
        return eggs[self.selected_egg_index]

    def select_egg(self, index):
        self.selected_egg_index = index

    def get_selected_dragon(self):
        dragons = self.get_dragons()

        if self.selected_dragon in dragons:
            return self.selected_dragon

        if dragons:
            self.selected_dragon = dragons[0]
            return self.selected_dragon

        return None

    def get_dragons(self):
        return [
            d for d in getattr(self.world, "dragons", [])
            if getattr(d, "status", "") == "Alive"
        ]

    def add_training_event(self, text):
        if not hasattr(self.world, "event_log"):
            self.world.event_log = []

        self.world.event_log.append({
            "text": text,
            "type": "hatchery",
        })



    def run_training(self, action):
        if not hasattr(self.world, "eggs"):
            self.world.eggs = []

        eggs = self.world.eggs

        if not eggs:
            self.add_training_event("There are no eggs in the hatchery.")
            return

        egg = eggs[self.selected_egg_index % len(eggs)]

        if action == "inspect":
            self.add_training_event(
                f"The egg of {egg.get('mother', 'Unknown')} and {egg.get('father', 'Unknown')} was inspected. "
                f"It appears {egg.get('size', 'ordinary')} with a {egg.get('shell_color', 'plain')} shell. "
                f"It {egg.get('movement', 'rests quietly')}."
            )

        elif action == "caretaker":
            selected = self.get_selected_dragon()
            if not selected:
                return
            
            if egg.get("caretaker") == selected.name:
                return

            egg["caretaker"] = selected.name
            self.add_training_event(
                f"{selected.name} was assigned to care for the egg of "
                f"{egg.get('mother', 'Unknown')} and {egg.get('father', 'Unknown')}."
            )            
        



    def draw_panel(self, screen, rect, alpha=185):
        surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        surf.fill((28, 28, 28, alpha))
        screen.blit(surf, rect.topleft)

        pygame.draw.rect(
            screen,
            (55, 55, 55),
            rect,
            width=1,
            border_radius=14
        )

    def draw(self, screen):

        self.buttons.clear()

        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill((18, 18, 18))

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 130))
        screen.blit(overlay, (0, 0))

        title = self.title_font.render("Hatchery", True, TEXT)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 70)))

        subtitle = self.small.render(
            "Choose parents and tend the tribe's future generation.",
            True,
            MUTED
        )
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 110)))

        left = pygame.Rect(70, 150, 300, 500)
        right = pygame.Rect(400, 150, 560, 455)

        self.draw_panel(screen, left)
        self.draw_panel(screen, right)

        self.draw_text(
            screen,
            "Hatchery Actions",
            left.x + 18,
            left.y + 18,
            self.section_font,
            GOLD
        )

        self.draw_text(
            screen,
            "Hatchery Log",
            right.x + 18,
            right.y + 18,
            self.section_font,
            GOLD
        )

        egg = self.get_selected_egg()

        profile_rect = pygame.Rect(right.x + 18, right.y + 55, right.width - 36, 145)
        self.draw_panel(screen, profile_rect, alpha=130)

        if egg:

            sprite_rect = pygame.Rect(
                profile_rect.x + 15,
                profile_rect.y + 20,
                90,
                90
            )

            if self.egg_image:
                screen.blit(self.egg_image, sprite_rect.topleft)

            pygame.draw.rect(
                screen,
                GOLD,
                sprite_rect,
                width=2,
                border_radius=8
            )
        

        if egg:
            lines = [
                "Selected Egg",
                f"Egg of {egg.get('mother', 'Unknown')} & {egg.get('father', 'Unknown')}",
                f"Age: {egg.get('age', 0)} / {egg.get('hatch_time', '?')} moons",
                f"Shell: {egg.get('shell_color', 'plain')}",
                f"Size: {egg.get('size', 'ordinary')}",
                f"Movement: {egg.get('movement', 'quiet')}",
                f"Condition: {egg.get('condition', 'unknown')}",
                f"Caretaker: {egg.get('caretaker') or 'None'}",
            ]

            y = profile_rect.y + 12
            for i, line in enumerate(lines):
                color = GOLD if i in [0, 7] else TEXT
                self.draw_text(screen, line, profile_rect.x + 125, y, self.small, color)
                y += 17
        else:
            self.draw_text(
                screen,
                "No eggs in the hatchery.",
                profile_rect.x + 125,
                profile_rect.y + 40,
                self.small,
                MUTED
            )

        dragons = self.get_dragons()

        egg_count = len(getattr(self.world, "eggs", []))

        self.draw_text(
            screen,
            f"Eggs Incubating: {egg_count}",
            left.x + 22,
            left.y + 70,
            self.small,
            GOLD
        )

        egg = self.get_selected_egg()

        eggs = getattr(self.world, "eggs", [])

        egg_list_rect = pygame.Rect(left.x + 20, left.y + 105, left.width - 40, 85)
        self.draw_panel(screen, egg_list_rect, alpha=120)

        old_clip = screen.get_clip()
        screen.set_clip(egg_list_rect)

        y = egg_list_rect.y + 8 + self.egg_scroll

        for i, egg in enumerate(eggs):
            label = f"Egg of {egg.get('mother', '?')} & {egg.get('father', '?')}"

            btn_rect = pygame.Rect(egg_list_rect.x + 8, y, egg_list_rect.width - 16, 28)

            if btn_rect.bottom >= egg_list_rect.top and btn_rect.top <= egg_list_rect.bottom:
                btn = Button(
                    (btn_rect.x, btn_rect.y, btn_rect.width, btn_rect.height),
                    label,
                    lambda idx=i: self.select_egg(idx)
                )
                self.buttons.append(btn)
                btn.draw(screen, self.small)



            y += 34

        screen.set_clip(old_clip)


        self.draw_text(
            screen,
            "Caretaker",
            left.x + 22,
            left.y + 215,
            self.small,
            GOLD
        )



        list_rect = pygame.Rect(left.x + 20, left.y + 235, left.width - 40, 140)
        self.draw_panel(screen, list_rect, alpha=120)

        old_clip = screen.get_clip()
        screen.set_clip(list_rect)

        y = list_rect.y + 8 + self.list_scroll

        for dragon in self.get_dragons():
            btn_rect = pygame.Rect(list_rect.x + 8, y, list_rect.width - 16, 28)

            if btn_rect.bottom >= list_rect.top and btn_rect.top <= list_rect.bottom:
                btn = Button(
                    (btn_rect.x, btn_rect.y, btn_rect.width, btn_rect.height),
                    dragon.name,
                    lambda d=dragon: self.select_dragon(d)
                )
                self.buttons.append(btn)
                btn.draw(screen, self.small)

            selected_egg = self.get_selected_egg()
            current_caretaker = selected_egg.get("caretaker") if selected_egg else None

            if dragon == self.selected_dragon:
                pygame.draw.rect(screen, GOLD, btn_rect, width=2, border_radius=6)

            if dragon.name == current_caretaker:
                pygame.draw.rect(screen, RED, btn_rect, width=2, border_radius=6)

            y += 34

        screen.set_clip(old_clip)

        buttons = [
            ("Assign Caretaker", "caretaker"),
        ]

        btn_y = left.y + 420

        for label, training_type in buttons:
            btn = Button(
                (left.x + 45, btn_y, 190, 42),
                label,
                lambda t=training_type: self.run_training(t)
            )

            self.buttons.append(btn)
            btn.draw(screen, self.font)

            btn_y += 55

        log_rect = pygame.Rect(
            right.x + 18,
            right.y + 215,
            right.width - 36,
            right.height - 235
        )

        self.draw_panel(screen, log_rect, alpha=150)

        events = getattr(self.world, "event_log", [])

        hunt_events = [
            e for e in events
            if isinstance(e, dict)
            and e.get("type") == "hatchery"
        ]

        old_clip = screen.get_clip()
        screen.set_clip(log_rect)

        y = log_rect.y + 12 + self.log_scroll

        for event in reversed(hunt_events[-25:]):

            text = f"- {event.get('text', '')}"

            self.draw_wrapped_text(
                screen,
                text,
                log_rect.x + 12,
                y,
                log_rect.width - 24,
                self.small,
                TEXT
            )

            y += 70

        screen.set_clip(old_clip)

        return_btn = Button(
            (430, 645, 140, 38),
            "Return",
            lambda: self.change_screen("locations")
        )

        self.buttons.append(return_btn)
        return_btn.draw(screen, self.font)

    def update(self, dt):
        pass

    def select_dragon(self, dragon):
        self.selected_dragon = dragon

    def handle_event(self, event):

        if event.type == pygame.MOUSEWHEEL:
            mouse_x, mouse_y = pygame.mouse.get_pos()

            egg_list_rect = pygame.Rect(90, 255, 260, 85)

            if egg_list_rect.collidepoint(mouse_x, mouse_y):
                eggs = getattr(self.world, "eggs", [])
                total_height = len(eggs) * 34
                visible_height = egg_list_rect.height
                max_scroll = max(0, total_height - visible_height)

                self.egg_scroll += event.y * 25
                self.egg_scroll = min(0, self.egg_scroll)
                self.egg_scroll = max(-max_scroll, self.egg_scroll)
                return

            dragon_list_rect = pygame.Rect(90, 385, 260, 140)

            if dragon_list_rect.collidepoint(mouse_x, mouse_y):
                total_height = len(self.get_dragons()) * 34
                visible_height = dragon_list_rect.height
                max_scroll = max(0, total_height - visible_height)

                self.list_scroll += event.y * 25
                self.list_scroll = min(0, self.list_scroll)
                self.list_scroll = max(-max_scroll, self.list_scroll)

            else:
                self.log_scroll += event.y * 25
                self.log_scroll = min(0, self.log_scroll)
                self.log_scroll = max(-800, self.log_scroll)

        for button in self.buttons:
            button.handle_event(event)