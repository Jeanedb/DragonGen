import pygame
from pathlib import Path

from ui_pygame.core.base_screen import BaseScreen
from ui_pygame.widgets.button import Button

try:
    from core.simulation import advance_moon
except Exception:
    advance_moon = None

WIDTH, HEIGHT = 1000, 700

TEXT = (230, 230, 230)
MUTED = (180, 180, 180)
GOLD = (242, 201, 76)
GREEN = (111, 207, 151)
RED = (235, 87, 87)


class WorldDashboardScreen(BaseScreen):
    def __init__(self, world, change_screen):
        super().__init__()
        self.world = world
        self.change_screen = change_screen
        self.log_scroll = 0
        self.event_filter = "All"

        project_root = Path(__file__).resolve().parents[2]
        bg_path = project_root / "assets" / "menu" / "main_locations_bg.png"

        try:
            self.bg_image = pygame.image.load(str(bg_path)).convert()
            self.bg_image = pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT))
        except Exception:
            self.bg_image = None

    def set_event_filter(self, filter_name):
        self.event_filter = filter_name
        self.log_scroll = 0

    def get_tension_mood(self):
        tension = getattr(self.world, "tension", 0.0)

        if tension < 0.75:
            return "Mood: Calm", "The tribe feels steady."
        elif tension < 1.5:
            return "Mood: Uneasy", "Small frictions are starting to show."
        elif tension < 2.5:
            return "Mood: Strained", "Conflict is affecting daily life."
        elif tension < 3.5:
            return "Mood: Volatile", "The tribe feels close to open conflict."
        else:
            return "Mood: Crisis", "Stability is slipping."

    def draw_panel(self, screen, rect, alpha=185):
        surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        surf.fill((28, 28, 28, alpha))
        screen.blit(surf, rect.topleft)
        pygame.draw.rect(screen, (55, 55, 55), rect, width=1, border_radius=14)

    def get_dragons(self):
        return getattr(self.world, "dragons", self.world)

    def get_counts(self):
        dragons = self.get_dragons()
        living = sum(1 for d in dragons if getattr(d, "status", "") == "Alive")
        dead = sum(1 for d in dragons if getattr(d, "status", "") == "Dead")
        injured = sum(
            1 for d in dragons
            if getattr(d, "status", "") == "Alive"
            and getattr(d, "health", "Healthy") != "Healthy"
        )
        return living, injured, dead

    def get_event_lines(self):
        events = getattr(self.world, "event_log", [])
        lines = []

        for event in events[-30:]:
            if isinstance(event, dict):
                text = event.get("text", str(event))
            else:
                text = str(event)
            lines.append(f"- {text}")

        if not lines:
            return ["No events yet."]

        return lines

    def advance_week(self):
        if advance_moon:
            try:
                advance_moon(self.world)
            except Exception as e:
                print(f"Could not advance moon/week: {e}")
        else:
            if hasattr(self.world, "moon"):
                self.world.moon += 1

    def draw(self, screen):
        self.buttons.clear()

        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill((18, 18, 18))

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 130))
        screen.blit(overlay, (0, 0))

        title = self.title_font.render("Tribe Overview", True, TEXT)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 70)))

        subtitle = self.small.render(
            "Review the tribe, recent events, and advance the world.",
            True,
            MUTED
        )
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 110)))

        left = pygame.Rect(85, 150, 280, 430)
        right = pygame.Rect(395, 150, 520, 430)

        self.draw_panel(screen, left)
        self.draw_panel(screen, right)

        self.draw_text(screen, "Tribe Status", left.x + 18, left.y + 18, self.section_font, GOLD)
        self.draw_text(screen, "World Event Log", right.x + 18, right.y + 18, self.section_font, GOLD)

        living, injured, dead = self.get_counts()
        moon = getattr(self.world, "moon", 0)
        tension = getattr(self.world, "tension", 0.0)
        tension_clamped = max(0, min(5, tension))

        y = left.y + 65
        self.draw_text(screen, f"Moon: {moon}", left.x + 24, y, self.font, TEXT)
        y += 38
        self.draw_text(screen, f"Living: {living}", left.x + 24, y, self.font, GREEN)
        y += 34
        self.draw_text(screen, f"Injured: {injured}", left.x + 24, y, self.font, GOLD)
        y += 34
        self.draw_text(screen, f"Dead: {dead}", left.x + 24, y, self.font, RED)

        y += 60
        self.draw_text(screen, f"Tension: {tension_clamped:.1f} / 5.0", left.x + 24, y, self.font, TEXT)

        bar_rect = pygame.Rect(left.x + 24, y + 34, left.width - 48, 18)
        pygame.draw.rect(screen, (45, 45, 45), bar_rect, border_radius=8)

        fill_width = int(bar_rect.width * (tension_clamped / 5))
        fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, fill_width, bar_rect.height)
        pygame.draw.rect(screen, GOLD, fill_rect, border_radius=8)
        pygame.draw.rect(screen, (90, 90, 90), bar_rect, width=1, border_radius=8)

        mood_title, mood_desc = self.get_tension_mood()

        self.draw_text(screen, mood_title, left.x + 24, bar_rect.y + 35, self.font, GOLD)
        self.draw_text(screen, mood_desc, left.x + 24, bar_rect.y + 65, self.small, MUTED)

        advance_btn = Button(
            (left.x + 45, left.y + 350, 190, 42),
            "Advance Week",
            self.advance_week
        )
        self.buttons.append(advance_btn)
        advance_btn.draw(screen, self.font)

        self.draw_text(screen, "World Event Log", right.x + 18, right.y + 18, self.section_font, GOLD)

        filters = ["All", "Rumors", "Social", "Injuries", "Political"]

        x = right.x + 18
        y = right.y + 55

        for filter_name in filters:
            btn = Button(
                (x, y, 88, 28),
                filter_name,
                lambda f=filter_name: self.set_event_filter(f)
            )
            self.buttons.append(btn)
            btn.draw(screen, self.small)
            x += 96

        log_rect = pygame.Rect(right.x + 18, right.y + 95, right.width - 36, right.height - 120)
        self.draw_panel(screen, log_rect, alpha=150)

        old_clip = screen.get_clip()
        screen.set_clip(log_rect)

        y = log_rect.y + 12 + self.log_scroll
        for line in self.get_event_lines():
            self.draw_wrapped_text(
                screen,
                line,
                log_rect.x + 12,
                y,
                log_rect.width - 24,
                self.small,
                TEXT
            )
            y += 44

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

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            self.log_scroll += event.y * 25
            self.log_scroll = min(0, self.log_scroll)
            self.log_scroll = max(-800, self.log_scroll)

        for button in self.buttons:
            button.handle_event(event)