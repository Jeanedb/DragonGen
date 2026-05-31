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


class BorderRoutesScreen(BaseScreen):

    def __init__(self, world, change_screen):
        super().__init__()

        self.training_mode = "sparring"

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
            "type": "border",
        })

    def run_training(self, training_type):

        dragons = self.get_dragons()

        if len(dragons) < 2:
            return

        a = self.get_selected_dragon()

        others = [d for d in dragons if d != a]

        if not a or not others:
            return

        b = random.choice(others)

        if training_type == "scout":

            outcomes = [
                (
                    "impress",
                    f"{a.name} discovered a new travel route.",
                    f"{a.name}'s reputation improved."
                ),

                (
                    "bond",
                    f"{a.name} and {b.name} spent days scouting together.",
                    f"Their trust increased."
                ),

                (
                    "impress",
                    f"{a.name} returned with reports of distant activity.",
                    f"The leadership appreciated the information."
                ),
            ]

        elif training_type == "patrol":

            outcomes = [
                (
                    "impress",
                    f"{a.name} successfully secured the border routes.",
                    f"{a.name}'s reputation improved."
                ),

                (
                    "challenge",
                    f"{a.name} and {b.name} disagreed during patrol.",
                    f"Tension between them increased."
                ),

                (
                    "strain",
                    f"The patrol encountered signs of trouble.",
                    f"The tribe feels slightly more concerned."
                ),
            ]

        elif training_type == "expedition":

            outcomes = [
                (
                    "impress",
                    f"{a.name} returned from a distant expedition with valuable information.",
                    f"{a.name}'s reputation improved greatly."
                ),

                (
                    "strain",
                    f"{a.name} barely escaped a dangerous situation beyond the border.",
                    f"The tribe is unsettled by the report."
                ),

                (
                    "bond",
                    f"{a.name} and {b.name} relied on each other to survive a difficult journey.",
                    f"Their trust increased significantly."
                ),

                (
                    "embarrass",
                    f"{a.name}'s expedition ended in failure.",
                    f"Some dragons have lost confidence in {a.name}."
                ),
            ]

        else:
            return

        chosen = random.choice(outcomes)

        outcome_type = chosen[0]
        text = chosen[1]
        effect_text = chosen[2] if len(chosen) > 2 else self.get_training_effect_text(a, b, outcome_type)

        self.apply_training_effect(a, b, outcome_type)
        self.add_training_event(
            f"{text}\n    {effect_text}"
        )

    def get_training_effect_text(self, a, b, outcome_type):
        if outcome_type == "bond":
            return f"{a.name} and {b.name} trust each other more."

        if outcome_type == "embarrass":
            return f"{b.name} resents {a.name} more."

        if outcome_type == "strain":
            return "The tribe feels slightly more tense."

        if outcome_type == "challenge":
            return f"Tension between {a.name} and {b.name} increased."

        if outcome_type == "impress":
            return f"{a.name}'s reputation improved."

        if outcome_type == "mentor":
            return f"{a.name} gained respect as a mentor."

        return "The training left a mark."


    def apply_training_effect(self, a, b, outcome_type):

        if outcome_type == "bond":
            a.trust[b.id] = a.trust.get(b.id, 0) + 0.4
            b.trust[a.id] = b.trust.get(a.id, 0) + 0.4

        elif outcome_type == "embarrass":
            b.resentment[a.id] = b.resentment.get(a.id, 0) + 0.5
            a.reputation["harsh"] = a.reputation.get("harsh", 0) + 0.2

        elif outcome_type == "strain":
            self.world.tension += 0.08
            a.reputation["harsh"] = a.reputation.get("harsh", 0) + 0.1

        elif outcome_type == "challenge":
            a.resentment[b.id] = a.resentment.get(b.id, 0) + 0.3
            b.resentment[a.id] = b.resentment.get(a.id, 0) + 0.3

        elif outcome_type == "impress":
            a.reputation["kind"] = a.reputation.get("kind", 0) + 0.2

        elif outcome_type == "mentor":
            a.reputation["kind"] = a.reputation.get("kind", 0) + 0.3

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

        title = self.title_font.render("Border Routes", True, TEXT)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 70)))

        subtitle = self.small.render(
            "Send patrols beyond the village and watch for outside threats.",
            True,
            MUTED
        )
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 110)))

        left = pygame.Rect(80, 150, 280, 455)
        right = pygame.Rect(405, 150, 535, 455)

        self.draw_panel(screen, left)
        self.draw_panel(screen, right)

        self.draw_text(
            screen,
            "Patrol Actions",
            left.x + 18,
            left.y + 18,
            self.section_font,
            GOLD
        )

        self.draw_text(
            screen,
            "Border Log",
            right.x + 18,
            right.y + 18,
            self.section_font,
            GOLD
        )

        dragons = self.get_dragons()

        self.draw_text(
            screen,
            f"Available Dragons: {len(dragons)}",
            left.x + 22,
            left.y + 70,
            self.font,
            TEXT
        )

        selected = self.get_selected_dragon()

        if selected:
            trust_count = len([
                v for v in getattr(selected, "trust", {}).values()
                if v > 0
            ])

            rival_count = len([
                v for v in getattr(selected, "resentment", {}).values()
                if v > 0
            ])

            age = getattr(selected, "age_moons", getattr(selected, "age", "Unknown"))
            role = getattr(selected, "role", "Unknown")

            self.draw_text(screen, f"Focus: {selected.name}", left.x + 22, left.y + 100, self.small, GOLD)
            self.draw_text(screen, f"Role: {role}", left.x + 22, left.y + 120, self.small, TEXT)
            self.draw_text(screen, f"Age: {age}", left.x + 22, left.y + 140, self.small, TEXT)
            self.draw_text(screen, f"Trusted By: {trust_count}", left.x + 22, left.y + 160, self.small, TEXT)
            self.draw_text(screen, f"Rivals: {rival_count}", left.x + 22, left.y + 180, self.small, TEXT)

        list_rect = pygame.Rect(left.x + 20, left.y + 205, left.width - 40, 110)
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

                if dragon == self.selected_dragon:
                    pygame.draw.rect(screen, GOLD, btn_rect, width=2, border_radius=6)

            y += 34

        screen.set_clip(old_clip)

        buttons = [
            ("Scout Route", "scout"),
            ("Border Patrol", "patrol"),
            ("Risky Expedition", "expedition"),
        ]

        btn_y = left.y + 330

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
            right.y + 60,
            right.width - 36,
            right.height - 78
        )

        self.draw_panel(screen, log_rect, alpha=150)

        events = getattr(self.world, "event_log", [])

        hunt_events = [
            e for e in events
            if isinstance(e, dict)
            and e.get("type") == "border"
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

            dragon_list_rect = pygame.Rect(100, 355, 240, 110)

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