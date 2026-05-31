import pygame
from pathlib import Path

from ui_pygame.core.base_screen import BaseScreen
from ui_pygame.widgets.button import Button

WIDTH, HEIGHT = 1000, 700

TEXT = (230, 230, 230)
MUTED = (180, 180, 180)
GOLD = (242, 201, 76)
GREEN = (111, 207, 151)
RED = (235, 87, 87)


class DragonProfileScreen(BaseScreen):
    def __init__(self, world, change_screen):
        super().__init__()
        self.world = world
        self.change_screen = change_screen
        self.selected_dragon = self.get_dragons()[0] if self.get_dragons() else None
        self.detail_scroll = 0
        self.list_scroll = 0

        project_root = Path(__file__).resolve().parents[2]
        bg_path = project_root / "assets" / "menu" / "village_bg.png"

        try:
            self.bg_image = pygame.image.load(str(bg_path)).convert()
            self.bg_image = pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT))
        except Exception:
            self.bg_image = None

    def get_dragon_list_label(self, d):
        name = getattr(d, "name", "Unknown")
        tribe = getattr(d, "tribe", "Unknown")
        rank = getattr(d, "rank", "")

        if rank == "Leader":
            return f"{name} — Leader ({tribe})"

        if rank == "Deputy":
            return f"{name} — Deputy ({tribe})"

        return f"{name} ({tribe})"

    def get_dragons(self):
        if hasattr(self.world, "dragons"):
            dragons = list(self.world.dragons)
        else:
            dragons = list(self.world)

        # remove dead dragons
        dragons = [
            d for d in dragons
            if getattr(d, "status", "Alive") != "Dead"
        ]

        def sort_key(d):
            rank = getattr(d, "rank", "")

            if rank == "Leader":
                priority = 0
            elif rank == "Deputy":
                priority = 1
            else:
                priority = 2

            return (priority, d.name.lower())

        dragons.sort(key=sort_key)

        return dragons

    def draw_panel(self, screen, rect, alpha=185):
        surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        surf.fill((28, 28, 28, alpha))
        screen.blit(surf, rect.topleft)
        pygame.draw.rect(screen, (55, 55, 55), rect, width=1, border_radius=14)

    def get_dragon_text(self, d):
        if not d:
            return "No dragon selected."

        friends = ", ".join(str(x) for x in getattr(d, "friends", [])) or "None"
        rivals = ", ".join(str(x) for x in getattr(d, "rivals", [])) or "None"
        titles = ", ".join(getattr(d, "earned_titles", [])) or "None"
        memory_flags = list(getattr(d, "memory_flags", []))

        memory_text = ", ".join(str(m) for m in memory_flags) if memory_flags else "None"

        return (
            "=== Identity ===\n"
            f"Name: {getattr(d, 'name', 'Unknown')}\n"
            f"Tribe: {getattr(d, 'tribe', 'Unknown')}\n"
            f"Age: {getattr(d, 'age_moons', getattr(d, 'age', 'Unknown'))}\n"
            f"Role: {getattr(d, 'role', 'Unknown')}\n"
            f"Rank: {getattr(d, 'rank', 'Unknown')}\n\n"

            "=== Status ===\n"
            f"Health: {getattr(d, 'health', 'Unknown')}\n"
            f"Status: {getattr(d, 'status', 'Unknown')}\n"
            f"Location: {getattr(d, 'location', 'Unknown')}\n"
            f"Personality: {getattr(d, 'personality', 'Unknown')}\n\n"

            "=== Relationships ===\n"
            f"Friends: {friends}\n"
            f"Rivals: {rivals}\n"
            f"Titles: {titles}\n\n"

            "=== Memories ===\n"
            f"{memory_text}\n\n"

            "=== Social Perception ===\n"
            f"Trust: {len(getattr(d, 'trust', {}))} entries\n"
            f"Resentment: {len(getattr(d, 'resentment', {}))} entries\n"
            f"Perceived Reputation: {len(getattr(d, 'perceived_reputation', {}))} entries"
        )

    def draw_profile_text(self, screen, text, x, y, width):
        lines = text.split("\n")

        current_y = y

        for line in lines:

            is_header = line.startswith("===")

            if is_header:
                line = line.replace("===", "").strip()
                color = GOLD
                font = self.section_font
            else:
                color = TEXT
                font = self.small

            rendered = font.render(line, True, color)
            screen.blit(rendered, (x, current_y))

            if is_header:
                current_y += 34
            else:
                current_y += 24

    def draw(self, screen):
        self.buttons.clear()

        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill((18, 18, 18))

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 130))
        screen.blit(overlay, (0, 0))

        title = self.title_font.render("Dragon Profile", True, TEXT)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 70)))


        left = pygame.Rect(80, 130, 280, 500)
        right = pygame.Rect(390, 130, 530, 500)

        self.draw_panel(screen, left)
        self.draw_panel(screen, right)

        self.draw_text(screen, "Dragons", left.x + 18, left.y + 16, self.section_font, GOLD)
        self.draw_text(screen, "Profile", right.x + 18, right.y + 16, self.section_font, GOLD)

        portrait_rect = pygame.Rect(right.x + 24, right.y + 50, 170, 170)
        self.draw_panel(screen, portrait_rect, alpha=120)

        self.draw_text(
            screen,
            "Portrait",
            portrait_rect.x + 38,
            portrait_rect.y + 60,
            self.small,
            MUTED
        )

        d = self.selected_dragon

        if d:
            self.draw_text(screen, d.name, portrait_rect.right + 20, portrait_rect.y + 10, self.section_font, TEXT)

            self.draw_text(
                screen,
                f"{d.tribe} • {d.role}",
                portrait_rect.right + 20,
                portrait_rect.y + 55,
                self.small,
                MUTED
            )


        list_rect = pygame.Rect(left.x + 12, left.y + 55, left.width - 24, left.height - 75)

        old_clip = screen.get_clip()
        screen.set_clip(list_rect)

        y = list_rect.y + self.list_scroll

        for d in self.get_dragons():
            selected = d == self.selected_dragon

            btn_rect = pygame.Rect(left.x + 18, y, 240, 34)

            if btn_rect.bottom >= list_rect.top and btn_rect.top <= list_rect.bottom:
                btn = Button(
                    (btn_rect.x, btn_rect.y, btn_rect.width, btn_rect.height),
                    self.get_dragon_list_label(d),
                    lambda dragon=d: self.select_dragon(dragon)
                )
                self.buttons.append(btn)
                btn.draw(screen, self.small)

                if selected:
                    pygame.draw.rect(
                        screen,
                        GOLD,
                        pygame.Rect(left.x + 14, y - 3, 248, 40),
                        width=2,
                        border_radius=8
                    )

            y += 42

        screen.set_clip(old_clip)

        detail_rect = pygame.Rect(right.x + 18, right.y + 205, right.width - 36, right.height - 230)
        self.draw_panel(screen, detail_rect, alpha=150)

        old_clip = screen.get_clip()
        screen.set_clip(detail_rect)

        self.draw_profile_text(
            screen,
            self.get_dragon_text(self.selected_dragon),
            detail_rect.x + 12,
            detail_rect.y + 12 + self.detail_scroll,
            detail_rect.width - 24
        )

        screen.set_clip(old_clip)

        return_btn = Button(
            (430, 645, 140, 38),
            "Return",
            lambda: self.change_screen("locations")
        )
        self.buttons.append(return_btn)
        return_btn.draw(screen, self.font)

    def get_health_color(self, d):
        health = getattr(d, "health", "Unknown")

        if health == "Healthy":
            return GREEN
        if health == "Dead":
            return MUTED
        return RED

    def select_dragon(self, dragon):
        self.selected_dragon = dragon
        self.detail_scroll = 0

    def update(self, dt):
        pass

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            mouse_x, mouse_y = pygame.mouse.get_pos()

            left_rect = pygame.Rect(80, 130, 280, 500)
            right_detail_rect = pygame.Rect(408, 335, 494, 270)

            if left_rect.collidepoint(mouse_x, mouse_y):
                total_height = len(self.get_dragons()) * 42
                visible_height = left_rect.height - 75
                max_scroll = max(0, total_height - visible_height)

                self.list_scroll += event.y * 30
                self.list_scroll = min(0, self.list_scroll)
                self.list_scroll = max(-max_scroll, self.list_scroll)

            elif right_detail_rect.collidepoint(mouse_x, mouse_y):
                self.detail_scroll += event.y * 25
                self.detail_scroll = min(0, self.detail_scroll)
                self.detail_scroll = max(-700, self.detail_scroll)

        for button in self.buttons:
            button.handle_event(event)