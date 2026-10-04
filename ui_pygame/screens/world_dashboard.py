from pathlib import Path

import pygame

from ui_pygame.core.base_screen import BaseScreen


WIDTH, HEIGHT = 1000, 700

INK = (30, 23, 19)
PANEL = (35, 27, 22)
PANEL_LIGHT = (49, 38, 30)
BRONZE = (137, 94, 52)
GOLD = (231, 190, 112)
PARCHMENT = (239, 220, 181)
TEXT = (220, 207, 184)
MUTED = (166, 151, 128)
GREEN = (117, 174, 113)
AMBER = (218, 155, 65)
RED = (190, 78, 58)


class ClickTarget:
    def __init__(self, rect, callback):
        self.rect = pygame.Rect(rect)
        self.callback = callback

    def handle_event(self, event):
        if (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        ):
            self.callback()


class FantasyButton(ClickTarget):
    def __init__(self, rect, label, callback, enabled=True):
        super().__init__(rect, callback)
        self.label = label
        self.enabled = enabled

    def handle_event(self, event):
        if self.enabled:
            super().handle_event(event)

    def draw(self, screen, font, mouse_pos):
        hovered = self.enabled and self.rect.collidepoint(mouse_pos)
        shadow = self.rect.move(0, 4)
        pygame.draw.rect(screen, (10, 7, 5), shadow, border_radius=8)

        if not self.enabled:
            edge, fill, color = (80, 70, 60), (43, 39, 35), (112, 104, 94)
        elif hovered:
            edge, fill, color = GOLD, (91, 57, 28), PARCHMENT
        else:
            edge, fill, color = BRONZE, (48, 38, 31), PARCHMENT

        pygame.draw.rect(screen, edge, self.rect, border_radius=8)
        inner = self.rect.inflate(-5, -5)
        pygame.draw.rect(screen, fill, inner, border_radius=6)
        pygame.draw.line(
            screen,
            (204, 155, 88) if self.enabled else (76, 68, 59),
            (inner.left + 8, inner.top + 3),
            (inner.right - 8, inner.top + 3),
            1,
        )
        image = font.render(self.label, True, color)
        screen.blit(image, image.get_rect(center=self.rect.center))


class WorldDashboardScreen(BaseScreen):
    """A strategic report: current tribe health plus the recent chronicle."""

    FILTERS = [
        "All",
        "Social",
        "Recovery",
        "Injuries",
        "Leadership",
        "Politics",
        "Rumors",
    ]

    FILTER_TYPES = {
        "Rumors": {"rumor"},
        "Social": {
            "social",
            "friend_event",
            "rival_event",
            "grief_event",
            "rivalry_escalation",
            "rivalry_crisis",
            "rivalry_break",
        },
        "Recovery": {
            "recovery_visit",
            "recovery_neglect",
            "healed",
            "natural_healing",
        },
        "Injuries": {"injury", "rivalry_injury", "injury_strain"},
        "Leadership": {"leader", "leadership", "leader_event"},
        "Politics": {"politics", "diplomacy", "border", "relations"},
    }

    LOCATION_SCREENS = {
        "relations": "relations",
        "village": "village",
        "healer_den": "healer_den",
        "training": "training_grounds",
        "hunting": "hunting_grounds",
        "border": "border_routes",
        "library": "scroll_library",
        "hatchery": "hatchery",
    }

    def __init__(self, world, change_screen):
        super().__init__()
        self.world = world
        self.change_screen = change_screen
        self.log_scroll = 0
        self.log_content_height = 0
        self.log_view_height = 0
        self.event_filter = "All"

        self.title = pygame.font.SysFont("georgia", 30, bold=True)
        self.heading = pygame.font.SysFont("georgia", 18, bold=True)
        self.stat_value = pygame.font.SysFont("georgia", 24, bold=True)
        self.body = pygame.font.SysFont("georgia", 15)
        self.body_bold = pygame.font.SysFont("georgia", 15, bold=True)
        self.small_text = pygame.font.SysFont("georgia", 13)
        self.small_bold = pygame.font.SysFont("georgia", 13, bold=True)

        project_root = Path(__file__).resolve().parents[2]
        tribe = str(getattr(world, "tribe_name", "MudWing Tribe"))
        tribe_key = tribe.lower().replace(" tribe", "").replace(" ", "")
        bg_path = project_root / "assets" / tribe_key / "location_map.png"
        if not bg_path.exists():
            bg_path = project_root / "assets" / "menu" / "main_locations_bg.png"

        try:
            self.bg_image = pygame.image.load(str(bg_path)).convert()
            self.bg_image = pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT))
        except Exception as error:
            print(f"Could not load overview background: {error}")
            self.bg_image = None

    def draw_beveled_panel(self, screen, rect, fill=PANEL, edge=BRONZE, cut=12):
        rect = pygame.Rect(rect)
        x, y, w, h = rect
        points = [
            (x + cut, y),
            (x + w - cut, y),
            (x + w, y + cut),
            (x + w, y + h - cut),
            (x + w - cut, y + h),
            (x + cut, y + h),
            (x, y + h - cut),
            (x, y + cut),
        ]
        pygame.draw.polygon(screen, (9, 6, 5), [(px, py + 5) for px, py in points])
        pygame.draw.polygon(screen, edge, points)

        inner = rect.inflate(-6, -6)
        ix, iy, iw, ih = inner
        inner_cut = max(4, cut - 3)
        inner_points = [
            (ix + inner_cut, iy),
            (ix + iw - inner_cut, iy),
            (ix + iw, iy + inner_cut),
            (ix + iw, iy + ih - inner_cut),
            (ix + iw - inner_cut, iy + ih),
            (ix + inner_cut, iy + ih),
            (ix, iy + ih - inner_cut),
            (ix, iy + inner_cut),
        ]
        pygame.draw.polygon(screen, fill, inner_points)
        pygame.draw.lines(screen, (207, 157, 89), False, inner_points[:3], 1)

    def get_dragons(self):
        dragons = getattr(self.world, "dragons", self.world)
        try:
            return list(dragons)
        except TypeError:
            return []

    def get_counts(self):
        dragons = self.get_dragons()
        living = [d for d in dragons if getattr(d, "status", "Alive") == "Alive"]
        injured = [
            d
            for d in living
            if getattr(d, "health", "Healthy") not in ("Healthy", "healthy", None)
        ]
        dead = [d for d in dragons if getattr(d, "status", "Alive") == "Dead"]
        return len(living), len(injured), len(dead)

    def dragon_name(self, dragon_id, fallback="Unassigned"):
        if dragon_id is None:
            return fallback
        for dragon in self.get_dragons():
            if getattr(dragon, "id", None) == dragon_id:
                return getattr(dragon, "name", fallback)
        return fallback

    def get_tension_mood(self):
        tension = float(getattr(self.world, "tension", 0.0) or 0.0)
        if tension < 0.75:
            return "CALM", GREEN
        if tension < 1.5:
            return "UNEASY", AMBER
        if tension < 2.5:
            return "STRAINED", AMBER
        if tension < 3.5:
            return "VOLATILE", RED
        return "CRISIS", RED

    def get_alerts(self):
        living, injured, _ = self.get_counts()
        food = int(getattr(self.world, "food_stores", 0) or 0)
        tension = float(getattr(self.world, "tension", 0.0) or 0.0)
        eggs = len(getattr(self.world, "eggs", []) or [])
        choice = getattr(self.world, "pending_choice", None)
        alerts = []

        if choice:
            alerts.append(("!", "A decision requires your attention.", GOLD))
        if injured:
            alerts.append(("+", f"{injured} injured dragon{'s' if injured != 1 else ''} need care.", RED))
        if living and food < living:
            alerts.append(("!", "Food stores are critically low.", RED))
        elif living and food < living * 3:
            alerts.append(("!", "Food stores should be watched.", AMBER))
        if tension >= 2.5:
            alerts.append(("!", "Tribal tension is dangerously high.", RED))
        if eggs:
            alerts.append(("o", f"{eggs} egg{'s' if eggs != 1 else ''} rest in the hatchery.", GOLD))
        if not alerts:
            alerts.append(("✓", "No urgent concerns this moon.", GREEN))

        limit = 3 if choice else 4
        return alerts[:limit]

    def get_event_entries(self):
        allowed_types = self.FILTER_TYPES.get(self.event_filter)
        entries = []
        for event in reversed((getattr(self.world, "event_log", []) or [])[-100:]):
            if isinstance(event, dict):
                event_type = str(event.get("type", ""))
                text = str(event.get("text", event))
            else:
                event_type = ""
                text = str(event)

            if allowed_types and not any(key in event_type for key in allowed_types):
                continue
            entries.append((event_type, text))

        if not entries:
            entries.append(("empty", f"No {self.event_filter.lower()} entries yet."))
        return entries

    def event_color(self, event_type):
        lowered = event_type.lower()
        if "injur" in lowered or "crisis" in lowered or "death" in lowered:
            return RED
        if "heal" in lowered or "recover" in lowered or "friend" in lowered:
            return GREEN
        if "leader" in lowered or "polit" in lowered or "relation" in lowered:
            return GOLD
        return BRONZE

    def cycle_event_filter(self):
        index = self.FILTERS.index(self.event_filter)
        self.event_filter = self.FILTERS[(index + 1) % len(self.FILTERS)]
        self.log_scroll = 0

    def review_pending_choice(self):
        choice = getattr(self.world, "pending_choice", None)
        if not isinstance(choice, dict):
            return
        location = choice.get("location", "relations")
        destination = self.LOCATION_SCREENS.get(location, "relations")
        self.change_screen(destination)

    def draw_stat_card(self, screen, rect, label, value, accent=GOLD):
        rect = pygame.Rect(rect)
        pygame.draw.rect(screen, (17, 13, 11), rect.move(0, 3), border_radius=8)
        pygame.draw.rect(screen, (92, 66, 43), rect, border_radius=8)
        pygame.draw.rect(screen, PANEL_LIGHT, rect.inflate(-3, -3), border_radius=6)
        pygame.draw.rect(screen, accent, (rect.x + 5, rect.y + 5, 4, rect.height - 10), border_radius=2)
        label_image = self.small_bold.render(label, True, MUTED)
        value_image = self.stat_value.render(str(value), True, PARCHMENT)
        screen.blit(label_image, (rect.x + 17, rect.y + 9))
        screen.blit(value_image, (rect.x + 17, rect.y + 26))

    def draw_watch(self, screen, rect, mouse_pos):
        rect = pygame.Rect(rect)
        self.draw_beveled_panel(screen, rect, fill=(42, 32, 26), edge=(108, 76, 47))
        screen.blit(self.small_bold.render("CURRENT WATCH", True, GOLD), (rect.x + 16, rect.y + 12))

        for index, (icon, text, color) in enumerate(self.get_alerts()):
            y = rect.y + 39 + index * 22
            icon_image = self.small_bold.render(icon, True, color)
            text_image = self.small_text.render(text, True, TEXT)
            screen.blit(icon_image, (rect.x + 17, y))
            screen.blit(text_image, (rect.x + 37, y))

        if getattr(self.world, "pending_choice", None):
            button = FantasyButton(
                (rect.right - 112, rect.bottom - 35, 94, 27),
                "REVIEW",
                self.review_pending_choice,
            )
            self.buttons.append(button)
            button.draw(screen, self.small_bold, mouse_pos)

    def draw_chronicle(self, screen, rect, mouse_pos):
        rect = pygame.Rect(rect)
        self.draw_beveled_panel(screen, rect, fill=PANEL, edge=BRONZE)
        screen.blit(self.heading.render("RECENT CHRONICLE", True, PARCHMENT), (rect.x + 22, rect.y + 20))

        count = len(getattr(self.world, "event_log", []) or [])
        count_image = self.small_text.render(f"{count} recorded events", True, MUTED)
        screen.blit(count_image, (rect.x + 23, rect.y + 49))

        filter_button = FantasyButton(
            (rect.right - 157, rect.y + 18, 132, 34),
            f"{self.event_filter.upper()}  >",
            self.cycle_event_filter,
        )
        self.buttons.append(filter_button)
        filter_button.draw(screen, self.small_bold, mouse_pos)

        divider_y = rect.y + 72
        pygame.draw.line(screen, (91, 65, 43), (rect.x + 22, divider_y), (rect.right - 22, divider_y), 1)

        log_rect = pygame.Rect(rect.x + 18, rect.y + 82, rect.width - 36, rect.height - 104)
        old_clip = screen.get_clip()
        screen.set_clip(log_rect)
        content_top = log_rect.y + self.log_scroll
        y = content_top

        for event_type, text in self.get_event_entries():
            marker_color = self.event_color(event_type)
            pygame.draw.circle(screen, marker_color, (log_rect.x + 8, y + 8), 4)
            y = self.draw_wrapped_text(
                screen,
                text,
                log_rect.x + 22,
                y,
                log_rect.width - 32,
                self.body,
                TEXT,
            )
            y += 13
            pygame.draw.line(
                screen,
                (63, 49, 39),
                (log_rect.x + 22, y - 5),
                (log_rect.right - 8, y - 5),
                1,
            )

        self.log_content_height = max(0, y - content_top)
        self.log_view_height = log_rect.height
        screen.set_clip(old_clip)

        if self.log_content_height > self.log_view_height:
            hint = self.small_text.render("SCROLL TO READ MORE", True, MUTED)
            screen.blit(hint, hint.get_rect(bottomright=(rect.right - 22, rect.bottom - 12)))

    def draw(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        self.buttons.clear()

        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill((28, 20, 16))

        wash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        wash.fill((15, 9, 6, 168))
        screen.blit(wash, (0, 0))

        pygame.draw.rect(screen, (110, 77, 47), (18, 16, 964, 668), width=3, border_radius=18)
        pygame.draw.rect(screen, (35, 27, 22), (25, 23, 950, 654), width=2, border_radius=15)

        self.draw_beveled_panel(screen, (300, 18, 400, 70), fill=INK, edge=BRONZE)
        title_image = self.title.render("TRIBE OVERVIEW", True, PARCHMENT)
        screen.blit(title_image, title_image.get_rect(center=(500, 45)))
        tribe_name = str(getattr(self.world, "tribe_name", "Your Tribe"))
        subtitle = self.small_text.render(f"{tribe_name.upper()}  •  STRATEGIC REPORT", True, MUTED)
        screen.blit(subtitle, subtitle.get_rect(center=(500, 70)))

        left = pygame.Rect(42, 106, 370, 515)
        right = pygame.Rect(430, 106, 528, 515)
        self.draw_beveled_panel(screen, left, fill=PANEL, edge=BRONZE)

        screen.blit(self.heading.render("TRIBE AT A GLANCE", True, PARCHMENT), (left.x + 22, left.y + 20))
        pygame.draw.line(screen, (91, 65, 43), (left.x + 22, left.y + 52), (left.right - 22, left.y + 52), 1)

        leader = self.dragon_name(getattr(self.world, "leader_id", None))
        deputy = self.dragon_name(getattr(self.world, "deputy_id", None))
        screen.blit(self.small_bold.render("LEADER", True, MUTED), (left.x + 22, left.y + 66))
        screen.blit(self.body_bold.render(leader, True, PARCHMENT), (left.x + 90, left.y + 64))
        screen.blit(self.small_bold.render("DEPUTY", True, MUTED), (left.x + 205, left.y + 66))
        screen.blit(self.body_bold.render(deputy, True, PARCHMENT), (left.x + 275, left.y + 64))

        living, injured, dead = self.get_counts()
        moon = getattr(self.world, "moon", 0)
        food = getattr(self.world, "food_stores", 0)
        eggs = len(getattr(self.world, "eggs", []) or [])
        card_y = left.y + 103
        self.draw_stat_card(screen, (left.x + 20, card_y, 157, 66), "MOON", moon)
        self.draw_stat_card(screen, (left.x + 193, card_y, 157, 66), "LIVING", living, GREEN)
        self.draw_stat_card(screen, (left.x + 20, card_y + 78, 157, 66), "FOOD", food, AMBER)
        self.draw_stat_card(screen, (left.x + 193, card_y + 78, 157, 66), "EGGS", eggs, GOLD)

        detail_y = left.y + 265
        screen.blit(self.body.render(f"Injured:  {injured}", True, RED if injured else TEXT), (left.x + 23, detail_y))
        screen.blit(self.body.render(f"Remembered dead:  {dead}", True, MUTED), (left.x + 190, detail_y))

        tension = max(0.0, min(5.0, float(getattr(self.world, "tension", 0.0) or 0.0)))
        mood, mood_color = self.get_tension_mood()
        tension_y = left.y + 304
        screen.blit(self.small_bold.render("TRIBAL TENSION", True, MUTED), (left.x + 22, tension_y))
        mood_image = self.small_bold.render(mood, True, mood_color)
        screen.blit(mood_image, mood_image.get_rect(topright=(left.right - 22, tension_y)))
        bar = pygame.Rect(left.x + 22, tension_y + 25, left.width - 44, 15)
        pygame.draw.rect(screen, (18, 14, 12), bar, border_radius=7)
        fill_width = int(bar.width * tension / 5.0)
        if fill_width:
            pygame.draw.rect(screen, mood_color, (bar.x, bar.y, fill_width, bar.height), border_radius=7)
        pygame.draw.rect(screen, (100, 72, 46), bar, width=1, border_radius=7)

        self.draw_watch(screen, (left.x + 20, left.y + 367, left.width - 40, 132), mouse_pos)
        self.draw_chronicle(screen, right, mouse_pos)

        return_button = FantasyButton(
            (390, 640, 220, 40),
            "RETURN TO MAP",
            lambda: self.change_screen("locations"),
        )
        self.buttons.append(return_button)
        return_button.draw(screen, self.body_bold, mouse_pos)

    def update(self, dt):
        pass

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            self.log_scroll += event.y * 28
            max_scroll = max(0, self.log_content_height - self.log_view_height)
            self.log_scroll = min(0, self.log_scroll)
            self.log_scroll = max(-max_scroll, self.log_scroll)

        for button in self.buttons:
            button.handle_event(event)
