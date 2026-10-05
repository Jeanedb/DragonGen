import pygame
from pathlib import Path

from ui_pygame.core.base_screen import BaseScreen
from ui_pygame.widgets.button import Button

try:
    from core.sim.conversations import (
        build_conversation,
        apply_conversation_choice,
        get_available_conversation_topics,
    )
except Exception:
    build_conversation = None
    apply_conversation_choice = None
    get_available_conversation_topics = None

WIDTH, HEIGHT = 1000, 700

BG = (18, 18, 18)
TEXT = (230, 230, 230)
MUTED = (180, 180, 180)
GOLD = (242, 201, 76)
GREEN = (111, 207, 151)


class VillageCenterScreen(BaseScreen):
    def __init__(self, world, change_screen):
        super().__init__()
        self.world = world
        self.change_screen = change_screen
        self.convo_scroll = 0

        self.selected_a = None
        self.selected_b = None
        self.current_convo = None
        self.message = "Select two dragons to begin a conversation."
        self.option_buttons = []

        PROJECT_ROOT = Path(__file__).resolve().parents[2]
        bg_path = PROJECT_ROOT / "assets" / "menu" / "village_bg.png"

        try:
            self.bg_image = pygame.image.load(str(bg_path)).convert()
            self.bg_image = pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT))
        except Exception:
            self.bg_image = None

    def get_dragons(self):
        if hasattr(self.world, "dragons"):
            return [d for d in self.world.dragons if getattr(d, "status", "") == "Alive"]
        return [d for d in self.world if getattr(d, "status", "") == "Alive"]

    def draw_panel(self, screen, rect, alpha=185):
        surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        surf.fill((28, 28, 28, alpha))
        screen.blit(surf, rect.topleft)
        pygame.draw.rect(screen, (55, 55, 55), rect, width=1, border_radius=14)

    def update(self, dt):
        pass

    def get_dragons_at_village(self):
        dragons = getattr(self.world, "dragons", self.world)

        return [
            d for d in dragons
            if getattr(d, "location", None) in [
                "village",
                "village_center",
                "Village Center"
            ]
        ]

    def get_dragons_at_village(self):
        dragons = getattr(self.world, "dragons", self.world)

        return [
            d for d in dragons
            if getattr(d, "location", None) in [
                "village",
                "village_center",
                "Village Center"
            ]
        ]

    def draw(self, screen):
        self.buttons.clear()

        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill(BG)

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 125))
        screen.blit(overlay, (0, 0))

        title = self.title_font.render("Village Center", True, TEXT)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 75)))

        subtitle = self.small.render(
            "Choose two dragons and guide their conversation.",
            True,
            MUTED
        )
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 115)))

        village_dragons = self.get_dragons_at_village()

        self.draw_text(
            screen,
            "Here:",
            55,
            40,
            self.small,
            GOLD
        )

        y = 60
        if not village_dragons:
            self.draw_text(screen, "No dragons here", 55, y, self.small, MUTED)
        else:
            for d in village_dragons[:5]:
                self.draw_text(
                    screen,
                    f"{d.name} ({getattr(d, 'role', 'Unknown')})",
                    55,
                    y,
                    self.small,
                    MUTED
                )
                y += 15

            if len(village_dragons) > 5:
                self.draw_text(
                    screen,
                    f"+{len(village_dragons) - 5} more",
                    55,
                    y,
                    self.small,
                    MUTED
                )

        left = pygame.Rect(85, 155, 260, 390)
        right = pygame.Rect(675, 155, 260, 390)
        center = pygame.Rect(370, 155, 280, 490)

        self.draw_panel(screen, left)
        self.draw_panel(screen, right)
        self.draw_panel(screen, center)

        self.draw_text(screen, "Dragon A", left.x + 18, left.y + 14, self.section_font, GOLD)
        self.draw_text(screen, "Dragon B", right.x + 18, right.y + 14, self.section_font, GOLD)
        self.draw_text(screen, "Conversation", center.x + 18, center.y + 14, self.section_font, GOLD)

        dragons = self.get_dragons()

        y = left.y + 55
        for d in dragons[:8]:
            selected = self.selected_a == d
            label = f"{d.name} ({getattr(d, 'tribe', 'Unknown')})"
            btn = Button((left.x + 18, y, 220, 32), label, lambda dragon=d: self.select_a(dragon))
            self.buttons.append(btn)
            btn.draw(screen, self.small)
            if selected:
                pygame.draw.rect(screen, GOLD, pygame.Rect(left.x + 14, y - 3, 228, 38), width=2, border_radius=8)
            y += 40

        y = right.y + 55
        for d in dragons[:8]:
            selected = self.selected_b == d
            label = f"{d.name} ({getattr(d, 'tribe', 'Unknown')})"
            btn = Button((right.x + 18, y, 220, 32), label, lambda dragon=d: self.select_b(dragon))
            self.buttons.append(btn)
            btn.draw(screen, self.small)
            if selected:
                pygame.draw.rect(screen, GOLD, pygame.Rect(right.x + 14, y - 3, 228, 38), width=2, border_radius=8)
            y += 40

        text_rect = pygame.Rect(center.x + 16, center.y + 60, center.width - 32, 260)
        self.draw_panel(screen, text_rect, alpha=160)
        old_clip = screen.get_clip()
        screen.set_clip(text_rect)

        self.draw_wrapped_text(
            screen,
            self.message,
            text_rect.x + 10,
            text_rect.y + 10 + self.convo_scroll,
            text_rect.width - 20,
            self.small,
            TEXT
        )

        screen.set_clip(old_clip)

        if not self.option_buttons:
            start_btn = Button(
                (center.x + 45, center.y + 295, 170, 36),
                "Start Conversation",
                self.start_conversation,
                enabled=self.selected_a is not None and self.selected_b is not None
            )
            self.buttons.append(start_btn)
            start_btn.draw(screen, self.small)

        self.draw_option_buttons(screen, center.x + 15, center.y + 335)

        return_btn = Button(
            (430, 655, 140, 38),
            "Return",
            lambda: self.change_screen("locations")
        )
        self.buttons.append(return_btn)
        return_btn.draw(screen, self.font)

    def draw_option_buttons(self, screen, x, y):
        for label, callback in self.option_buttons:
            btn = Button((x - 10, y, 270, 44), label, callback)
            self.buttons.append(btn)
            btn.draw(screen, self.small)
            y += 52

    def select_a(self, dragon):
        self.selected_a = dragon

    def select_b(self, dragon):
        self.selected_b = dragon

    def start_conversation(self):
        if not self.selected_a or not self.selected_b:
            self.message = "Choose two dragons first."
            return

        if self.selected_a == self.selected_b:
            self.message = "Choose two different dragons."
            return

        if not get_available_conversation_topics:
            self.message = f"{self.selected_a.name} speaks with {self.selected_b.name}."
            return

        topics = get_available_conversation_topics(self.world, self.selected_a, self.selected_b)
        self.message = "Choose a conversation topic."
        self.option_buttons = [
            (topic["text"], lambda tid=topic["id"]: self.start_topic(tid))
            for topic in topics
        ]

    def start_topic(self, topic_id):
        if not build_conversation:
            self.message = "Conversation backend not available."
            return

        convo = build_conversation(self.world, self.selected_a, self.selected_b, topic=topic_id)
        self.current_convo = convo
        self.message = convo["text"]

        self.option_buttons = [
            (option["text"], lambda oid=option["id"]: self.resolve_conversation(oid))
            for option in convo["options"]
        ]

    def resolve_conversation(self, option_id):
        if not apply_conversation_choice or not self.current_convo:
            return

        try:
            player_line, reply_line, result_text = apply_conversation_choice(
                self.world,
                self.selected_a,
                self.selected_b,
                self.current_convo["type"],
                option_id
            )

            self.message = (
                f"You: {player_line}\n\n"
                f"{self.selected_b.name}: {reply_line}\n\n"
                f"{result_text}"
            )

        except Exception as e:
            self.message = (
                "The conversation UI works, but the test world is missing real game data.\n\n"
                f"Backend error:\n{e}"
            )

        self.option_buttons = []

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            self.convo_scroll += event.y * 25
            self.convo_scroll = min(0, self.convo_scroll)
            self.convo_scroll = max(-500, self.convo_scroll)
        for button in self.buttons:
            button.handle_event(event)