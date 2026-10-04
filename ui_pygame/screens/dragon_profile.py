from pathlib import Path
import re

import pygame

from ui_pygame.core.base_screen import BaseScreen
from core.sim.relationships import get_relationships


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
    def __init__(self, rect, label, callback, selected=False):
        super().__init__(rect, callback)
        self.label = label
        self.selected = selected

    def draw(self, screen, font, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (9, 6, 5), self.rect.move(0, 3), border_radius=7)
        edge = GOLD if hovered or self.selected else BRONZE
        fill = (91, 57, 28) if hovered else ((75, 48, 28) if self.selected else (48, 38, 31))
        pygame.draw.rect(screen, edge, self.rect, border_radius=7)
        inner = self.rect.inflate(-5, -5)
        pygame.draw.rect(screen, fill, inner, border_radius=5)
        pygame.draw.line(
            screen,
            (210, 161, 92),
            (inner.left + 7, inner.top + 3),
            (inner.right - 7, inner.top + 3),
            1,
        )
        image = font.render(self.label, True, PARCHMENT)
        screen.blit(image, image.get_rect(center=self.rect.center))


class RosterEntry(ClickTarget):
    def __init__(self, rect, dragon, callback, selected=False):
        super().__init__(rect, callback)
        self.dragon = dragon
        self.selected = selected

    def draw(self, screen, name_font, detail_font, mouse_pos, health_color):
        hovered = self.rect.collidepoint(mouse_pos)
        edge = GOLD if hovered or self.selected else (91, 66, 43)
        fill = (75, 49, 29) if self.selected else ((57, 43, 33) if hovered else (43, 34, 28))

        pygame.draw.rect(screen, (10, 7, 5), self.rect.move(0, 3), border_radius=8)
        pygame.draw.rect(screen, edge, self.rect, border_radius=8)
        pygame.draw.rect(screen, fill, self.rect.inflate(-4, -4), border_radius=6)
        pygame.draw.circle(screen, health_color, (self.rect.x + 16, self.rect.centery), 5)

        name = str(getattr(self.dragon, "name", "Unknown"))
        role = str(getattr(self.dragon, "role", "Unknown"))
        rank = str(getattr(self.dragon, "rank", ""))
        location = str(getattr(self.dragon, "location", "Unknown")).replace("_", " ").title()

        if rank in ("Leader", "Deputy"):
            name = f"{name}  •  {rank}"

        if len(name) > 29:
            name = name[:27] + "…"
        if len(location) > 20:
            location = location[:18] + "…"

        screen.blit(name_font.render(name, True, PARCHMENT), (self.rect.x + 29, self.rect.y + 8))
        detail = detail_font.render(f"{role}  •  {location}", True, MUTED)
        screen.blit(detail, (self.rect.x + 29, self.rect.y + 31))


class DragonProfileScreen(BaseScreen):
    """Searchable tribe roster with focused Overview, Bonds, and History tabs."""

    STATUS_FILTERS = ["Living", "Fallen", "All"]
    ATTENTION_FILTERS = ["All", "Attention", "Leaders"]
    SORT_MODES = ["Rank", "Name", "Age", "Location"]
    PROFILE_TABS = ["Overview", "Bonds", "History"]
    HISTORY_MODES = ["Key Memories", "Full Chronicle"]

    def __init__(self, world, change_screen):
        super().__init__()
        self.world = world
        self.change_screen = change_screen
        self.status_filter = "Living"
        self.attention_filter = "All"
        self.sort_mode = "Rank"
        self.profile_tab = "Overview"
        self.history_mode = "Key Memories"
        self.search_text = ""
        self.search_active = False
        self.list_scroll = 0
        self.detail_scroll = 0
        self.detail_content_height = 0
        self.detail_view_height = 0
        self.search_rect = pygame.Rect(48, 156, 286, 34)
        self.list_view_rect = pygame.Rect(48, 275, 286, 309)

        self.title = pygame.font.SysFont("georgia", 30, bold=True)
        self.heading = pygame.font.SysFont("georgia", 18, bold=True)
        self.name_font = pygame.font.SysFont("georgia", 23, bold=True)
        self.body = pygame.font.SysFont("georgia", 15)
        self.body_bold = pygame.font.SysFont("georgia", 15, bold=True)
        self.small_text = pygame.font.SysFont("georgia", 13)
        self.small_bold = pygame.font.SysFont("georgia", 13, bold=True)
        self.tiny = pygame.font.SysFont("georgia", 11)

        dragons = self.get_filtered_dragons()
        self.selected_dragon = dragons[0] if dragons else None

        project_root = Path(__file__).resolve().parents[2]
        tribe = str(getattr(world, "tribe_name", "MudWing Tribe"))
        tribe_key = tribe.lower().replace(" tribe", "").replace(" ", "")
        choices = [
            project_root / "assets" / tribe_key / "profile_bg.png",
            project_root / "assets" / tribe_key / "location_map.png",
            project_root / "assets" / "menu" / "village_bg.png",
        ]
        bg_path = next((path for path in choices if path.exists()), choices[-1])

        try:
            self.bg_image = pygame.image.load(str(bg_path)).convert()
            self.bg_image = pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT))
        except Exception as error:
            print(f"Could not load dragon roster background: {error}")
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

    def get_all_dragons(self):
        if hasattr(self.world, "dragons"):
            return list(self.world.dragons)
        try:
            return list(self.world)
        except TypeError:
            return []

    def needs_attention(self, dragon):
        health = str(getattr(dragon, "health", "Healthy")).lower()
        status = str(getattr(dragon, "status", "Alive")).lower()
        return health != "healthy" or status not in ("alive", "healthy")

    def get_health_color(self, dragon):
        status = str(getattr(dragon, "status", "Alive")).lower()
        health = str(getattr(dragon, "health", "Healthy")).lower()
        if status == "dead":
            return MUTED
        if health == "healthy":
            return GREEN
        if "recover" in health or "minor" in health:
            return AMBER
        return RED

    def get_filtered_dragons(self):
        dragons = self.get_all_dragons()

        if self.status_filter == "Living":
            dragons = [d for d in dragons if str(getattr(d, "status", "Alive")).lower() != "dead"]
        elif self.status_filter == "Fallen":
            dragons = [d for d in dragons if str(getattr(d, "status", "Alive")).lower() == "dead"]

        if self.attention_filter == "Attention":
            dragons = [d for d in dragons if self.needs_attention(d)]
        elif self.attention_filter == "Leaders":
            dragons = [d for d in dragons if getattr(d, "rank", "") in ("Leader", "Deputy")]

        query = self.search_text.strip().lower()
        if query:
            dragons = [
                d
                for d in dragons
                if query in str(getattr(d, "name", "")).lower()
                or query in str(getattr(d, "role", "")).lower()
                or query in str(getattr(d, "location", "")).lower()
                or query in str(getattr(d, "tribe", "")).lower()
            ]

        def rank_priority(dragon):
            return {"Leader": 0, "Deputy": 1}.get(getattr(dragon, "rank", ""), 2)

        if self.sort_mode == "Name":
            dragons.sort(key=lambda d: str(getattr(d, "name", "")).lower())
        elif self.sort_mode == "Age":
            dragons.sort(
                key=lambda d: int(getattr(d, "age_moons", getattr(d, "age", 0)) or 0),
                reverse=True,
            )
        elif self.sort_mode == "Location":
            dragons.sort(
                key=lambda d: (
                    str(getattr(d, "location", "")).lower(),
                    str(getattr(d, "name", "")).lower(),
                )
            )
        else:
            dragons.sort(
                key=lambda d: (rank_priority(d), str(getattr(d, "name", "")).lower())
            )

        return dragons

    def get_dragon_name_by_id(self, dragon_id):
        for dragon in self.get_all_dragons():
            if getattr(dragon, "id", None) == dragon_id:
                return str(getattr(dragon, "name", f"Dragon {dragon_id}"))
        return f"Dragon {dragon_id}"

    def format_names(self, values):
        names = [self.get_dragon_name_by_id(value) for value in (values or [])]
        return ", ".join(names) if names else "None"

    def select_dragon(self, dragon):
        self.selected_dragon = dragon
        self.detail_scroll = 0

    def set_status_filter(self, status):
        self.status_filter = status
        self.list_scroll = 0
        self.ensure_valid_selection()

    def cycle_attention_filter(self):
        index = self.ATTENTION_FILTERS.index(self.attention_filter)
        self.attention_filter = self.ATTENTION_FILTERS[(index + 1) % len(self.ATTENTION_FILTERS)]
        self.list_scroll = 0
        self.ensure_valid_selection()

    def cycle_sort(self):
        index = self.SORT_MODES.index(self.sort_mode)
        self.sort_mode = self.SORT_MODES[(index + 1) % len(self.SORT_MODES)]
        self.list_scroll = 0

    def set_profile_tab(self, tab):
        self.profile_tab = tab
        self.detail_scroll = 0

    def set_history_mode(self, mode):
        self.history_mode = mode
        self.detail_scroll = 0

    def ensure_valid_selection(self):
        dragons = self.get_filtered_dragons()
        if self.selected_dragon not in dragons:
            self.selected_dragon = dragons[0] if dragons else None
        self.detail_scroll = 0

    def draw_search_box(self, screen):
        edge = GOLD if self.search_active else (102, 73, 47)
        pygame.draw.rect(screen, edge, self.search_rect, border_radius=7)
        pygame.draw.rect(screen, (27, 21, 18), self.search_rect.inflate(-4, -4), border_radius=5)
        shown = self.search_text if self.search_text else "Search name, role, or location…"
        color = PARCHMENT if self.search_text else MUTED
        if len(shown) > 34:
            shown = "…" + shown[-33:]
        screen.blit(self.small_text.render(shown, True, color), (self.search_rect.x + 12, self.search_rect.y + 9))

    def draw_roster(self, screen, rect, mouse_pos):
        rect = pygame.Rect(rect)
        self.draw_beveled_panel(screen, rect, fill=PANEL, edge=BRONZE)
        screen.blit(self.heading.render("DRAGON ROSTER", True, PARCHMENT), (rect.x + 18, rect.y + 16))

        dragons = self.get_filtered_dragons()
        count_text = self.small_text.render(f"{len(dragons)} shown", True, MUTED)
        screen.blit(count_text, count_text.get_rect(topright=(rect.right - 18, rect.y + 21)))

        self.draw_search_box(screen)

        tab_width = 88
        for index, status in enumerate(self.STATUS_FILTERS):
            button = FantasyButton(
                (rect.x + 16 + index * 94, rect.y + 93, tab_width, 30),
                status.upper(),
                lambda value=status: self.set_status_filter(value),
                selected=self.status_filter == status,
            )
            self.buttons.append(button)
            button.draw(screen, self.tiny, mouse_pos)

        filter_button = FantasyButton(
            (rect.x + 16, rect.y + 130, 134, 29),
            f"SHOW: {self.attention_filter.upper()}",
            self.cycle_attention_filter,
        )
        sort_button = FantasyButton(
            (rect.x + 157, rect.y + 130, 134, 29),
            f"SORT: {self.sort_mode.upper()}",
            self.cycle_sort,
        )
        for button in (filter_button, sort_button):
            self.buttons.append(button)
            button.draw(screen, self.tiny, mouse_pos)

        old_clip = screen.get_clip()
        screen.set_clip(self.list_view_rect)
        y = self.list_view_rect.y + self.list_scroll
        for dragon in dragons:
            entry_rect = pygame.Rect(self.list_view_rect.x, y, self.list_view_rect.width, 54)
            if entry_rect.bottom >= self.list_view_rect.top and entry_rect.top <= self.list_view_rect.bottom:
                entry = RosterEntry(
                    entry_rect,
                    dragon,
                    lambda chosen=dragon: self.select_dragon(chosen),
                    selected=dragon == self.selected_dragon,
                )
                self.buttons.append(entry)
                entry.draw(
                    screen,
                    self.small_bold,
                    self.tiny,
                    mouse_pos,
                    self.get_health_color(dragon),
                )
            y += 61
        screen.set_clip(old_clip)

        if not dragons:
            message = self.body.render("No dragons match these filters.", True, MUTED)
            screen.blit(message, message.get_rect(center=self.list_view_rect.center))
        elif len(dragons) * 61 > self.list_view_rect.height:
            hint = self.tiny.render("SCROLL ROSTER", True, MUTED)
            screen.blit(hint, hint.get_rect(bottomright=(rect.right - 17, rect.bottom - 12)))

    def draw_portrait(self, screen, rect, dragon):
        rect = pygame.Rect(rect)
        pygame.draw.rect(screen, (11, 8, 6), rect.move(0, 4), border_radius=12)
        pygame.draw.rect(screen, BRONZE, rect, border_radius=12)
        pygame.draw.rect(screen, (42, 32, 26), rect.inflate(-5, -5), border_radius=9)
        center = rect.center
        pygame.draw.circle(screen, (76, 55, 39), center, 50)
        pygame.draw.circle(screen, GOLD, center, 50, 3)
        initials = "?"
        if dragon:
            name = str(getattr(dragon, "name", "?"))
            initials = "".join(word[0] for word in name.split()[:2]).upper() or "?"
        initials_image = self.name_font.render(initials, True, PARCHMENT)
        screen.blit(initials_image, initials_image.get_rect(center=center))
        caption = self.tiny.render("PORTRAIT", True, MUTED)
        screen.blit(caption, caption.get_rect(center=(center[0], rect.bottom - 13)))

    def draw_tag(self, screen, x, y, text, color=BRONZE):
        image = self.small_bold.render(text.upper(), True, PARCHMENT)
        rect = pygame.Rect(x, y, image.get_width() + 20, 27)
        pygame.draw.rect(screen, color, rect, border_radius=13)
        pygame.draw.rect(screen, (55, 40, 30), rect.inflate(-3, -3), border_radius=11)
        screen.blit(image, image.get_rect(center=rect.center))
        return rect.right + 7

    def draw_field(self, screen, x, y, label, value, value_color=TEXT):
        screen.blit(self.small_bold.render(label.upper(), True, MUTED), (x, y))
        screen.blit(self.body.render(str(value), True, value_color), (x, y + 21))

    def draw_overview(self, screen, rect, dragon):
        x, y = rect.x + 18, rect.y + 15
        age = getattr(dragon, "age_moons", getattr(dragon, "age", "Unknown"))
        health = getattr(dragon, "health", "Unknown")
        health_color = self.get_health_color(dragon)
        fields = [
            ("Tribe", getattr(dragon, "tribe", "Unknown")),
            ("Age", f"{age} moons" if isinstance(age, int) else age),
            ("Role", getattr(dragon, "role", "Unknown")),
            ("Rank", getattr(dragon, "rank", "None") or "None"),
            ("Health", health),
            ("Status", getattr(dragon, "status", "Unknown")),
            ("Location", str(getattr(dragon, "location", "Unknown")).replace("_", " ").title()),
            ("Personality", str(getattr(dragon, "personality", "Unknown")).title()),
        ]

        for index, (label, value) in enumerate(fields):
            column = index % 2
            row = index // 2
            color = health_color if label == "Health" else TEXT
            self.draw_field(screen, x + column * 245, y + row * 52, label, value, color)

        titles = ", ".join(getattr(dragon, "earned_titles", []) or []) or "None earned"
        divider_y = y + 197
        pygame.draw.line(screen, (91, 65, 43), (x, divider_y), (rect.right - 18, divider_y), 1)
        screen.blit(self.small_bold.render("TITLES & DISTINCTIONS", True, GOLD), (x, divider_y + 15))
        self.draw_wrapped_text(screen, titles, x, divider_y + 40, rect.width - 36, self.body, TEXT)
        self.detail_content_height = rect.height

    def get_relationship_entries(self, dragon):
        try:
            relationships = list(get_relationships(dragon))
        except Exception:
            relationships = []
        relationships.sort(key=lambda item: abs(float(getattr(item, "strength", 0))), reverse=True)
        return relationships

    def draw_bonds(self, screen, rect, dragon):
        old_clip = screen.get_clip()
        screen.set_clip(rect)
        x = rect.x + 18
        y = rect.y + 14 + self.detail_scroll
        start_y = y

        groups = [
            ("FRIENDS", self.format_names(getattr(dragon, "friends", [])), GREEN),
            ("RIVALS", self.format_names(getattr(dragon, "rivals", [])), RED),
            ("MATES", self.format_names(getattr(dragon, "mates", [])), GOLD),
        ]
        for label, value, color in groups:
            screen.blit(self.small_bold.render(label, True, color), (x, y))
            y = self.draw_wrapped_text(screen, value, x, y + 22, rect.width - 36, self.body, TEXT) + 16

        pygame.draw.line(screen, (91, 65, 43), (x, y), (rect.right - 18, y), 1)
        y += 15
        screen.blit(self.small_bold.render("SOCIAL CONNECTIONS", True, GOLD), (x, y))
        y += 28

        relationships = self.get_relationship_entries(dragon)
        if not relationships:
            screen.blit(self.body.render("No developed social connections yet.", True, MUTED), (x, y))
            y += 28
        else:
            for relationship in relationships:
                try:
                    label = relationship.display_name()
                except Exception:
                    label = "Connection"
                other = self.get_dragon_name_by_id(getattr(relationship, "other_id", "?"))
                strength = float(getattr(relationship, "strength", 0) or 0)
                line = f"{label}: {other}"
                screen.blit(self.body.render(line, True, TEXT), (x, y))
                strength_text = self.small_text.render(f"Strength {strength:.1f}", True, MUTED)
                screen.blit(strength_text, strength_text.get_rect(topright=(rect.right - 20, y + 2)))
                y += 27

        self.detail_content_height = max(rect.height, y - start_y + 16)
        self.detail_view_height = rect.height
        screen.set_clip(old_clip)

    def get_memory_lines(self, dragon):
        lines = []
        for memory in reversed(list(getattr(dragon, "memories", []) or [])):
            memory_type = str(getattr(memory, "type", "memory")).replace("_", " ").title()
            other_id = getattr(memory, "other_id", None)
            moon = getattr(memory, "moon", None)
            text = memory_type
            if other_id is not None:
                text += f" — {self.get_dragon_name_by_id(other_id)}"
            if moon is not None:
                text += f"  •  Moon {moon}"
            lines.append(text)

        for flag in reversed(list(getattr(dragon, "memory_flags", []) or [])):
            if not isinstance(flag, (tuple, list)) or not flag:
                continue
            text = str(flag[0]).replace("_", " ").title()
            if len(flag) >= 2 and isinstance(flag[1], int):
                text += f" — {self.get_dragon_name_by_id(flag[1])}"
            if len(flag) >= 3 and isinstance(flag[2], int):
                text += f"  •  Moon {flag[2]}"
            lines.append(text)
        return lines

    def event_involves_dragon(self, event, dragon):
        if not isinstance(event, dict):
            return False

        dragon_id = getattr(dragon, "id", None)
        involved_ids = event.get("involved_ids", event.get("dragon_ids", [])) or []

        if involved_ids:
            return any(str(involved_id) == str(dragon_id) for involved_id in involved_ids)

        # Legacy saves created before events stored participant IDs can only be
        # recovered from their prose. Word boundaries avoid matching one
        # dragon's name inside another dragon's longer name.
        name = str(getattr(dragon, "name", "")).strip()
        text = str(event.get("text", ""))
        if not name:
            return False
        pattern = rf"(?<!\w){re.escape(name)}(?!\w)"
        return re.search(pattern, text, flags=re.IGNORECASE) is not None

    def get_dragon_events(self, dragon):
        events = getattr(self.world, "event_log", []) or []
        return [
            event
            for event in reversed(events)
            if self.event_involves_dragon(event, dragon)
        ]

    def get_event_color(self, event_type):
        lowered = str(event_type).lower()
        if any(word in lowered for word in ("injur", "death", "rival", "fail")):
            return RED
        if any(word in lowered for word in ("friend", "heal", "recover", "bond")):
            return GREEN
        if any(word in lowered for word in ("leader", "training", "hunt", "border")):
            return GOLD
        return BRONZE

    def draw_history(self, screen, rect, dragon, mouse_pos):
        mode_width = 248
        for index, mode in enumerate(self.HISTORY_MODES):
            button = FantasyButton(
                (rect.x + 18 + index * 260, rect.y + 10, mode_width, 31),
                mode.upper(),
                lambda value=mode: self.set_history_mode(value),
                selected=self.history_mode == mode,
            )
            self.buttons.append(button)
            button.draw(screen, self.tiny, mouse_pos)

        history_rect = pygame.Rect(rect.x, rect.y + 49, rect.width, rect.height - 49)
        old_clip = screen.get_clip()
        screen.set_clip(history_rect)
        x = history_rect.x + 18
        y = history_rect.y + 10 + self.detail_scroll
        start_y = y

        if self.history_mode == "Key Memories":
            screen.blit(self.small_bold.render("IMPORTANT LIFE MOMENTS", True, GOLD), (x, y))
            y += 30
            lines = self.get_memory_lines(dragon)
            if not lines:
                screen.blit(self.body.render("No key memories have been recorded yet.", True, MUTED), (x, y))
                y += 30
            else:
                for line in lines:
                    pygame.draw.circle(screen, GOLD, (x + 5, y + 8), 4)
                    y = self.draw_wrapped_text(
                        screen,
                        line,
                        x + 18,
                        y,
                        history_rect.width - 54,
                        self.body,
                        TEXT,
                    )
                    y += 12
                    pygame.draw.line(
                        screen,
                        (67, 50, 39),
                        (x + 18, y - 5),
                        (history_rect.right - 18, y - 5),
                        1,
                    )
        else:
            events = self.get_dragon_events(dragon)
            screen.blit(self.small_bold.render("COMPLETE PERSONAL RECORD", True, GOLD), (x, y))
            count = self.small_text.render(f"{len(events)} attributed events", True, MUTED)
            screen.blit(count, count.get_rect(topright=(history_rect.right - 18, y + 1)))
            y += 30

            if not events:
                screen.blit(self.body.render("No attributed events have been recorded yet.", True, MUTED), (x, y))
                y += 30
            else:
                for event in events:
                    event_type = str(event.get("type", "general"))
                    moon = event.get("moon")
                    importance = event.get("importance")
                    meta_parts = []
                    if moon is not None:
                        meta_parts.append(f"MOON {moon}")
                    meta_parts.append(event_type.replace("_", " ").upper())
                    if importance is not None:
                        meta_parts.append(f"IMPORTANCE {importance}")

                    color = self.get_event_color(event_type)
                    pygame.draw.circle(screen, color, (x + 5, y + 7), 4)
                    screen.blit(self.tiny.render("  •  ".join(meta_parts), True, color), (x + 18, y))
                    y += 21

                    text = str(event.get("text", "Unknown event"))
                    y = self.draw_wrapped_text(
                        screen,
                        text,
                        x + 18,
                        y,
                        history_rect.width - 54,
                        self.body,
                        TEXT,
                    )

                    cause = event.get("cause")
                    if cause:
                        y = self.draw_wrapped_text(
                            screen,
                            f"Cause: {cause}",
                            x + 18,
                            y + 2,
                            history_rect.width - 54,
                            self.small_text,
                            MUTED,
                        )

                    y += 13
                    pygame.draw.line(
                        screen,
                        (67, 50, 39),
                        (x + 18, y - 5),
                        (history_rect.right - 18, y - 5),
                        1,
                    )

        self.detail_content_height = max(history_rect.height, y - start_y + 16)
        self.detail_view_height = history_rect.height
        screen.set_clip(old_clip)

    def draw_profile(self, screen, rect, mouse_pos):
        rect = pygame.Rect(rect)
        self.draw_beveled_panel(screen, rect, fill=PANEL, edge=BRONZE)
        dragon = self.selected_dragon

        if not dragon:
            message = self.heading.render("NO DRAGON SELECTED", True, MUTED)
            screen.blit(message, message.get_rect(center=rect.center))
            return

        self.draw_portrait(screen, (rect.x + 20, rect.y + 20, 142, 142), dragon)
        name = str(getattr(dragon, "name", "Unknown"))
        screen.blit(self.name_font.render(name, True, PARCHMENT), (rect.x + 182, rect.y + 24))

        role = str(getattr(dragon, "role", "Unknown"))
        tribe = str(getattr(dragon, "tribe", "Unknown"))
        screen.blit(self.body.render(f"{tribe}  •  {role}", True, MUTED), (rect.x + 183, rect.y + 59))

        tag_x = rect.x + 182
        rank = str(getattr(dragon, "rank", ""))
        if rank:
            tag_x = self.draw_tag(screen, tag_x, rect.y + 88, rank, GOLD)
        health = str(getattr(dragon, "health", "Unknown"))
        tag_x = self.draw_tag(screen, tag_x, rect.y + 88, health, self.get_health_color(dragon))

        location = str(getattr(dragon, "location", "Unknown")).replace("_", " ").title()
        screen.blit(self.small_text.render(f"Currently at: {location}", True, TEXT), (rect.x + 183, rect.y + 127))

        tab_y = rect.y + 177
        tab_width = 158
        for index, tab in enumerate(self.PROFILE_TABS):
            button = FantasyButton(
                (rect.x + 20 + index * 166, tab_y, tab_width, 34),
                tab.upper(),
                lambda value=tab: self.set_profile_tab(value),
                selected=self.profile_tab == tab,
            )
            self.buttons.append(button)
            button.draw(screen, self.small_bold, mouse_pos)

        content_rect = pygame.Rect(rect.x + 20, rect.y + 224, rect.width - 40, rect.height - 244)
        pygame.draw.rect(screen, (22, 17, 14), content_rect, border_radius=9)
        pygame.draw.rect(screen, (92, 66, 43), content_rect, width=1, border_radius=9)

        if self.profile_tab == "Overview":
            self.detail_scroll = 0
            self.draw_overview(screen, content_rect, dragon)
        elif self.profile_tab == "Bonds":
            self.draw_bonds(screen, content_rect, dragon)
        else:
            self.draw_history(screen, content_rect, dragon, mouse_pos)

        if self.profile_tab != "Overview" and self.detail_content_height > self.detail_view_height:
            hint = self.tiny.render("SCROLL FOR MORE", True, MUTED)
            screen.blit(hint, hint.get_rect(bottomright=(content_rect.right - 12, content_rect.bottom - 8)))

    def draw(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        self.buttons.clear()

        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill((28, 20, 16))

        wash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        wash.fill((15, 9, 6, 158))
        screen.blit(wash, (0, 0))

        pygame.draw.rect(screen, (110, 77, 47), (18, 16, 964, 668), width=3, border_radius=18)
        pygame.draw.rect(screen, (35, 27, 22), (25, 23, 950, 654), width=2, border_radius=15)

        self.draw_beveled_panel(screen, (300, 18, 400, 70), fill=INK, edge=BRONZE)
        title_image = self.title.render("TRIBE ROSTER", True, PARCHMENT)
        screen.blit(title_image, title_image.get_rect(center=(500, 44)))
        tribe_name = str(getattr(self.world, "tribe_name", "Your Tribe"))
        subtitle = self.small_text.render(
            f"{tribe_name.upper()}  •  INDIVIDUAL RECORDS",
            True,
            MUTED,
        )
        screen.blit(subtitle, subtitle.get_rect(center=(500, 70)))

        self.draw_roster(screen, (32, 106, 318, 518), mouse_pos)
        self.draw_profile(screen, (368, 106, 600, 518), mouse_pos)

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
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.search_active = self.search_rect.collidepoint(event.pos)

        if event.type == pygame.KEYDOWN and self.search_active:
            if event.key == pygame.K_BACKSPACE:
                self.search_text = self.search_text[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                self.search_active = False
            elif event.unicode and event.unicode.isprintable() and len(self.search_text) < 30:
                self.search_text += event.unicode
            self.list_scroll = 0
            self.ensure_valid_selection()

        if event.type == pygame.MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()
            if self.list_view_rect.collidepoint(mouse_pos):
                total_height = len(self.get_filtered_dragons()) * 61
                max_scroll = max(0, total_height - self.list_view_rect.height)
                self.list_scroll += event.y * 34
                self.list_scroll = min(0, self.list_scroll)
                self.list_scroll = max(-max_scroll, self.list_scroll)
            elif pygame.Rect(388, 330, 560, 274).collidepoint(mouse_pos):
                max_scroll = max(0, self.detail_content_height - self.detail_view_height)
                self.detail_scroll += event.y * 28
                self.detail_scroll = min(0, self.detail_scroll)
                self.detail_scroll = max(-max_scroll, self.detail_scroll)

        for button in self.buttons:
            button.handle_event(event)
