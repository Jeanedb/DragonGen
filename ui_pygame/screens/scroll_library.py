from pathlib import Path

import pygame

from ui_pygame.core.base_screen import BaseScreen

try:
    from core.sim.flavor import ensure_dragon_flavor, generate_dragon_bio, generate_legacy_text
except Exception:
    ensure_dragon_flavor = None
    generate_dragon_bio = None
    generate_legacy_text = None


WIDTH, HEIGHT = 1000, 700
TEXT = (236, 222, 196)
MUTED = (176, 158, 132)
GOLD = (227, 183, 84)
BRONZE = (133, 91, 53)
CREAM = (248, 230, 192)
RED = (196, 83, 68)
GREEN = (111, 178, 120)
PANEL = (31, 25, 20)


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def find_project_root():
    source = Path(__file__).resolve()
    candidates = [source.parent, *source.parents, Path.cwd(), *Path.cwd().parents]
    checked = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in checked:
            continue
        checked.add(candidate)
        if (candidate / "assets").is_dir():
            return candidate
    return source.parents[2]


class ClickTarget:
    def __init__(self, rect, callback, enabled=True):
        self.rect = pygame.Rect(rect)
        self.callback = callback
        self.enabled = enabled

    def handle_event(self, event):
        if (
            self.enabled
            and event.type == pygame.MOUSEBUTTONUP
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        ):
            self.callback()


class ArchiveButton(ClickTarget):
    def __init__(self, rect, label, callback, enabled=True, selected=False, primary=False):
        super().__init__(rect, callback, enabled)
        self.label = label
        self.selected = selected
        self.primary = primary

    def draw(self, screen, font, mouse_pos):
        hovered = self.enabled and self.rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (7, 5, 4), self.rect.move(0, 3), border_radius=7)
        if not self.enabled:
            edge, fill, color = (72, 65, 58), (40, 37, 34), (112, 104, 94)
        elif self.selected:
            edge, fill, color = GOLD, (92, 58, 29), CREAM
        elif self.primary:
            edge = GOLD if hovered else (177, 121, 53)
            fill = (105, 62, 30) if hovered else (73, 46, 27)
            color = CREAM
        else:
            edge = GOLD if hovered else (105, 76, 53)
            fill = (61, 45, 34) if hovered else (42, 34, 29)
            color = TEXT
        pygame.draw.rect(screen, edge, self.rect, border_radius=7)
        inner = self.rect.inflate(-5, -5)
        pygame.draw.rect(screen, fill, inner, border_radius=5)
        if self.enabled:
            pygame.draw.line(
                screen,
                (211, 165, 92),
                (inner.x + 7, inner.y + 3),
                (inner.right - 7, inner.y + 3),
                1,
            )
        image = font.render(self.label, True, color)
        screen.blit(image, image.get_rect(center=self.rect.center))


class ScrollLibraryScreen(BaseScreen):
    TABS = ("Record", "Biography", "Lineage", "Legacy")

    def __init__(self, world, change_screen):
        super().__init__()
        self.world = world
        self.change_screen = change_screen
        self.active_tab = "Record"
        self.roster_filter = "All"
        self.search_text = ""
        self.search_active = False
        self.roster_scroll = 0
        self.detail_scroll = 0
        self._roster_content_height = 0
        self._detail_content_height = 0
        self._roster_rect = pygame.Rect(38, 259, 260, 350)
        self._detail_rect = pygame.Rect(335, 217, 620, 388)
        self.recolor_cache = {}

        self.title_fantasy = pygame.font.SysFont("georgia", 28, bold=True)
        self.heading = pygame.font.SysFont("georgia", 17, bold=True)
        self.body = pygame.font.SysFont("georgia", 13)
        self.body_bold = pygame.font.SysFont("georgia", 13, bold=True)
        self.small = pygame.font.SysFont("georgia", 11)
        self.tiny = pygame.font.SysFont("georgia", 10)
        self.medallion_font = pygame.font.SysFont("georgia", 12, bold=True)

        dragons = self.get_dragons()
        self.selected_dragon = dragons[0] if dragons else None

        root = find_project_root()
        tribe_slug = (
            str(getattr(world, "tribe_name", ""))
            .lower()
            .replace(" tribe", "")
            .replace(" ", "")
        )
        backgrounds = [
            root / "assets" / tribe_slug / "scroll_library_bg.png",
            root / "assets" / tribe_slug / "library_bg.png",
            root / "assets" / tribe_slug / "location_map.png",
            root / "assets" / "menu" / "village_bg.png",
        ]
        background_path = next((path for path in backgrounds if path.exists()), backgrounds[-1])
        try:
            self.bg_image = pygame.image.load(str(background_path)).convert()
            self.bg_image = pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT))
        except Exception as error:
            print(f"Could not load library background: {error}")
            self.bg_image = None

        self.sprite_parts = {}
        for name in ("tail", "wing_left", "body", "feet", "neck", "head_open", "wing_right"):
            try:
                image = pygame.image.load(str(root / "assets" / f"{name}.png")).convert_alpha()
                self.sprite_parts[name] = pygame.transform.scale_by(image, 0.22)
            except Exception as error:
                print(f"Could not load sprite part {name}: {error}")
                self.sprite_parts[name] = None

    # Archive data ---------------------------------------------------

    def get_dragons(self):
        return list(getattr(self.world, "dragons", []))

    def is_dead(self, dragon):
        return str(getattr(dragon, "status", "Alive")).lower() in {"dead", "deceased"}

    def get_dragon_by_id(self, dragon_id):
        if dragon_id is None:
            return None
        wanted = str(dragon_id)
        return next(
            (dragon for dragon in self.get_dragons() if str(getattr(dragon, "id", "")) == wanted),
            None,
        )

    def get_id_list(self, dragon, attribute):
        values = getattr(dragon, attribute, []) if dragon else []
        if values is None:
            return []
        if isinstance(values, (str, int)):
            return [values]
        return list(values)

    def get_parents(self, dragon):
        return [self.get_dragon_by_id(value) for value in self.get_id_list(dragon, "parents")[:2]]

    def get_children(self, dragon):
        explicit = [
            self.get_dragon_by_id(value)
            for value in self.get_id_list(dragon, "dragonets")
        ]
        explicit = [child for child in explicit if child]
        if explicit:
            return explicit
        own_id = str(getattr(dragon, "id", ""))
        return [
            candidate
            for candidate in self.get_dragons()
            if own_id in {str(value) for value in self.get_id_list(candidate, "parents")}
        ]

    def get_mate(self, dragon):
        return self.get_dragon_by_id(getattr(dragon, "mate_id", None))

    def names_from_ids(self, values):
        names = []
        for value in values or []:
            dragon = self.get_dragon_by_id(value)
            if dragon:
                names.append(dragon.name)
        return ", ".join(names) or "None recorded"

    def get_filtered_dragons(self):
        dragons = self.get_dragons()
        if self.roster_filter == "Living":
            dragons = [dragon for dragon in dragons if not self.is_dead(dragon)]
        elif self.roster_filter == "Dead":
            dragons = [dragon for dragon in dragons if self.is_dead(dragon)]
        query = self.search_text.strip().lower()
        if query:
            dragons = [
                dragon
                for dragon in dragons
                if query
                in " ".join(
                    str(getattr(dragon, key, ""))
                    for key in ("name", "tribe", "role", "rank")
                ).lower()
            ]
        return sorted(
            dragons,
            key=lambda dragon: (self.is_dead(dragon), str(getattr(dragon, "name", "")).lower()),
        )

    def select_dragon(self, dragon):
        self.selected_dragon = dragon
        self.detail_scroll = 0

    def set_tab(self, tab):
        self.active_tab = tab
        self.detail_scroll = 0

    def set_filter(self, value):
        self.roster_filter = value
        self.roster_scroll = 0

    def open_portrait(self):
        if self.selected_dragon:
            self.world.selected_portrait_dragon = self.selected_dragon
            self.change_screen("dragon_portrait")

    def get_dragon_events(self, dragon, limit=8):
        dragon_id = str(getattr(dragon, "id", ""))
        matches = []
        for event in getattr(self.world, "event_log", []):
            if not isinstance(event, dict):
                continue
            involved = event.get("involved_ids", event.get("dragon_ids", [])) or []
            if dragon_id in {str(value) for value in involved}:
                matches.append(event)
        return matches[-limit:]

    def natural_list(self, values):
        values = [str(value) for value in values if value not in (None, "")]
        if not values:
            return ""
        if len(values) == 1:
            return values[0]
        if len(values) == 2:
            return f"{values[0]} and {values[1]}"
        return f"{', '.join(values[:-1])}, and {values[-1]}"

    def polish_generated_biography(self, text, dragon):
        """Correct the most common role/tribe wording produced by older saves."""
        tribe = str(getattr(dragon, "tribe", "Unknown"))
        role = str(getattr(dragon, "role", "dragon"))
        text = str(text).replace(tribe.lower(), tribe)
        text = text.replace(f"{role.lower()} {tribe}", f"{tribe} {role.lower()}")
        return text

    def get_deceased_biography(self, dragon):
        """Describe the life that was lived; death and legacy remain on the Legacy tab."""
        name = str(getattr(dragon, "name", "This dragon"))
        tribe = str(getattr(dragon, "tribe", "tribal"))
        role = str(getattr(dragon, "role", "tribe member"))
        rank = str(getattr(dragon, "rank", "None"))
        personality = str(getattr(dragon, "personality", "")).strip().lower()
        age = getattr(dragon, "age_moons", getattr(dragon, "age", "an unknown number of"))
        height = getattr(dragon, "height", None)
        eyes = getattr(dragon, "eye_color", None)
        skills = list(getattr(dragon, "skills", []))
        hobbies = list(getattr(dragon, "hobbies", []))
        friends = [
            related.name
            for value in getattr(dragon, "friends", [])
            if (related := self.get_dragon_by_id(value))
        ]
        mate = self.get_mate(dragon)
        children = self.get_children(dragon)

        description = f"{name} was"
        if personality:
            description += f" a {personality}"
        else:
            description += " a"
        description += f" {tribe} who lived for {age} moons. "
        description += f"They served the tribe as {self.article_for(role)} {role.lower()}"
        if rank.lower() not in {"none", "unknown", ""} and rank.lower() != role.lower():
            description += f" and held the rank of {rank.lower()}"
        description += ". "

        physical = []
        if height not in (None, "Unknown"):
            physical.append(f"stood {height} metres tall")
        if eyes not in (None, "Unknown"):
            physical.append(f"had {eyes} eyes")
        if physical:
            description += f"They {self.natural_list(physical)}. "
        if skills:
            description += f"They were known for {self.natural_list(skills)}. "
        if hobbies:
            description += f"Away from their duties, they were drawn to {self.natural_list(hobbies)}. "
        if friends:
            description += f"They formed meaningful bonds with {self.natural_list(friends)}. "
        if mate:
            description += f"They shared their life with {mate.name}. "
        if children:
            description += f"Their children were {self.natural_list(child.name for child in children)}. "
        description += (
            "The events below preserve the course of their life; the circumstances of their "
            "death and the legacy they left behind are sealed in the Legacy record."
        )
        return description

    def article_for(self, word):
        return "an" if str(word).strip().lower()[:1] in "aeiou" else "a"

    def get_biography(self, dragon):
        if ensure_dragon_flavor:
            ensure_dragon_flavor(dragon)
        if self.is_dead(dragon):
            return self.get_deceased_biography(dragon)
        if generate_dragon_bio:
            return self.polish_generated_biography(generate_dragon_bio(dragon, self.world), dragon)
        return "No biography has been recorded yet."

    def get_saved_obituary(self, dragon):
        if not hasattr(self.world, "world_flags") or self.world.world_flags is None:
            self.world.world_flags = {}
        records = self.world.world_flags.setdefault("sealed_obituaries", {})
        key = str(getattr(dragon, "id", getattr(dragon, "name", "unknown")))
        if records.get(key):
            return records[key]

        parents = [parent.name for parent in self.get_parents(dragon) if parent]
        children = [child.name for child in self.get_children(dragon)]
        titles = list(getattr(dragon, "earned_titles", []))
        cause = (
            getattr(dragon, "cause_of_death", None)
            or getattr(dragon, "death_cause", None)
            or getattr(dragon, "cause", None)
            or "an unrecorded cause"
        )
        age = getattr(dragon, "age_moons", getattr(dragon, "age", "an unknown age"))
        role = str(getattr(dragon, "role", "tribe member")).lower()
        text = (
            f"{dragon.name}, a {getattr(dragon, 'tribe', 'tribal')} {role}, "
            f"died at {age} moons from {cause}. "
        )
        if parents:
            text += f"They were descended from {' and '.join(parents)}. "
        if children:
            text += f"Their line continued through {', '.join(children)}. "
        if titles:
            text += f"They carried the titles {', '.join(str(title) for title in titles)}. "
        if generate_legacy_text:
            generated = generate_legacy_text(dragon, self.world)
            if generated:
                text += generated.strip()
        records[key] = text.strip()
        return records[key]

    # General drawing ------------------------------------------------

    def draw_text_line(self, screen, text, x, y, font, color=TEXT, center=False):
        image = font.render(str(text), True, color)
        rect = image.get_rect()
        if center:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        screen.blit(image, rect)
        return rect

    def wrap_lines(self, text, font, width):
        lines = []
        for paragraph in str(text).split("\n"):
            words = paragraph.split()
            if not words:
                lines.append("")
                continue
            current = words[0]
            for word in words[1:]:
                candidate = f"{current} {word}"
                if font.size(candidate)[0] <= width:
                    current = candidate
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
        return lines

    def draw_wrapped(self, screen, text, rect, font, color=TEXT, line_height=17):
        y = rect.y
        for line in self.wrap_lines(text, font, rect.width):
            self.draw_text_line(screen, line, rect.x, y, font, color)
            y += line_height
        return y

    def draw_panel(self, screen, rect, title=None, alpha=228):
        shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (5, 3, 2, 190), shadow.get_rect(), border_radius=12)
        screen.blit(shadow, (rect.x + 5, rect.y + 6))
        panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(panel, (*PANEL, alpha), panel.get_rect(), border_radius=12)
        screen.blit(panel, rect.topleft)
        pygame.draw.rect(screen, BRONZE, rect, 2, border_radius=12)
        pygame.draw.rect(screen, (61, 42, 31), rect.inflate(-8, -8), 1, border_radius=9)
        if title:
            self.draw_text_line(screen, title, rect.x + 16, rect.y + 13, self.heading, GOLD)

    def fit_text(self, text, font, max_width):
        text = str(text)
        if font.size(text)[0] <= max_width:
            return text
        while text and font.size(text + "…")[0] > max_width:
            text = text[:-1]
        return text + "…"

    def initials(self, name):
        words = str(name).split()
        return ("".join(word[0] for word in words[:2]) if len(words) > 1 else str(name)[:2]).upper()

    def draw_medallion(self, screen, center, text, selected=False, dead=False):
        edge = GOLD if selected else ((90, 82, 73) if dead else BRONZE)
        fill = (54, 49, 45) if dead else (76, 50, 34)
        pygame.draw.circle(screen, (8, 5, 4), (center[0] + 2, center[1] + 3), 17)
        pygame.draw.circle(screen, edge, center, 16)
        pygame.draw.circle(screen, fill, center, 13)
        image = self.medallion_font.render(text, True, MUTED if dead else CREAM)
        screen.blit(image, image.get_rect(center=center))

    # Sprite drawing -------------------------------------------------

    def clamp_rgb(self, value):
        return max(0, min(255, int(value)))

    def get_tribe_color_ramp(self, tribe):
        ramps = {
            "MudWing": ((60, 40, 28), (110, 79, 58), (160, 125, 95)),
            "NightWing": ((20, 18, 28), (45, 40, 65), (90, 85, 120)),
            "SkyWing": ((90, 25, 18), (150, 55, 35), (220, 120, 70)),
            "IceWing": ((120, 160, 180), (170, 210, 230), (230, 245, 255)),
            "SandWing": ((120, 90, 40), (180, 145, 80), (235, 210, 150)),
            "SeaWing": ((10, 40, 55), (40, 130, 170), (140, 220, 240)),
            "RainWing": ((30, 90, 45), (60, 160, 80), (140, 230, 120)),
            "LeafWing": ((30, 80, 35), (60, 130, 60), (130, 200, 110)),
            "HiveWing": ((80, 50, 10), (190, 115, 20), (245, 190, 60)),
            "SilkWing": ((70, 25, 80), (155, 70, 175), (230, 160, 240)),
        }
        return ramps.get(tribe, ((50, 50, 50), (130, 130, 130), (220, 220, 220)))

    def individualized_ramp(self, dragon):
        dark, middle, light = self.get_tribe_color_ramp(getattr(dragon, "tribe", "Unknown"))
        raw_id = getattr(dragon, "id", 0)
        try:
            dragon_id = int(raw_id)
        except (TypeError, ValueError):
            dragon_id = sum(ord(character) for character in str(raw_id))
        shift_r = ((dragon_id % 5) - 2) * 6
        shift_g = (((dragon_id // 3) % 5) - 2) * 6
        shift_b = -((dragon_id % 5) - 2) * 4
        brightness = 1.0 + ((((dragon_id // 7) % 5) - 2) * 0.04)

        def vary(rgb):
            return tuple(
                self.clamp_rgb((channel + shift) * brightness)
                for channel, shift in zip(rgb, (shift_r, shift_g, shift_b))
            )
        return vary(dark), vary(middle), vary(light)

    def recolor_surface(self, surface, dragon):
        dark, middle, light = self.individualized_ramp(dragon)
        recolored = surface.copy()
        for x in range(recolored.get_width()):
            for y in range(recolored.get_height()):
                red, green, blue, alpha = recolored.get_at((x, y))
                if not alpha:
                    continue
                brightness = (red + green + blue) / 765
                if brightness < 0.5:
                    blend = brightness / 0.5
                    low, high = dark, middle
                else:
                    blend = (brightness - 0.5) / 0.5
                    low, high = middle, light
                recolored.set_at(
                    (x, y),
                    tuple(self.clamp_rgb(low[i] * (1 - blend) + high[i] * blend) for i in range(3)) + (alpha,),
                )
        return recolored

    def draw_sprite_preview(self, screen, rect, dragon):
        if not dragon:
            self.draw_text_line(screen, "No dragon selected", rect.centerx, rect.centery, self.body, MUTED, center=True)
            return
        center_x, center_y = rect.centerx + 22, rect.centery + 12
        body_x, body_y = center_x - 120, center_y - 20
        anchors = {
            "body": (body_x, body_y),
            "tail": (body_x + 115, body_y - 15),
            "feet": (body_x + 15, body_y + 36),
            "neck": (body_x + 8, body_y - 50),
            "head_open": (body_x + 1, body_y - 55),
            "wing_left": (body_x + 26, body_y - 51),
            "wing_right": (body_x + 30, body_y - 47),
        }
        shadow_rect = pygame.Rect(center_x - 150, center_y + 63, 260, 22)
        shadow = pygame.Surface(shadow_rect.size, pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 110), shadow.get_rect())
        screen.blit(shadow, shadow_rect.topleft)
        order = ("wing_left", "tail", "body", "feet", "neck", "head_open", "wing_right")
        for name in order:
            image = self.sprite_parts.get(name)
            if not image:
                continue
            key = (name, str(getattr(dragon, "id", 0)), str(getattr(dragon, "tribe", "Unknown")))
            if key not in self.recolor_cache:
                self.recolor_cache[key] = self.recolor_surface(image, dragon)
            screen.blit(self.recolor_cache[key], anchors[name])

    # Archive index --------------------------------------------------

    def draw_roster(self, screen, rect, mouse_pos):
        self.draw_panel(screen, rect, title="Archive Index")
        all_dragons = self.get_dragons()
        living = sum(not self.is_dead(dragon) for dragon in all_dragons)
        self.draw_text_line(
            screen,
            f"{len(all_dragons)} RECORDS  •  {living} LIVING  •  {len(all_dragons) - living} DECEASED",
            rect.x + 16,
            rect.y + 44,
            self.tiny,
            MUTED,
        )
        filter_y = rect.y + 65
        for index, label in enumerate(("All", "Living", "Dead")):
            button = ArchiveButton(
                pygame.Rect(rect.x + 12 + index * 82, filter_y, 76, 27),
                label.upper(),
                lambda value=label: self.set_filter(value),
                selected=self.roster_filter == label,
            )
            self.buttons.append(button)
            button.draw(screen, self.tiny, mouse_pos)

        search_rect = pygame.Rect(rect.x + 12, rect.y + 101, rect.width - 24, 31)
        pygame.draw.rect(screen, (49, 39, 32) if self.search_active else (34, 29, 25), search_rect, border_radius=7)
        pygame.draw.rect(screen, GOLD if self.search_active else (88, 63, 44), search_rect, 1, border_radius=7)
        search_label = self.search_text or "Search name, tribe, or role…"
        self.draw_text_line(
            screen,
            self.fit_text(search_label, self.small, search_rect.width - 20),
            search_rect.x + 10,
            search_rect.y + 8,
            self.small,
            TEXT if self.search_text else MUTED,
        )
        self.buttons.append(ClickTarget(search_rect, lambda: setattr(self, "search_active", True)))

        list_rect = pygame.Rect(rect.x + 10, rect.y + 141, rect.width - 20, rect.height - 154)
        self._roster_rect = list_rect
        dragons = self.get_filtered_dragons()
        self._roster_content_height = len(dragons) * 48
        old_clip = screen.get_clip()
        screen.set_clip(list_rect)
        y = list_rect.y + self.roster_scroll
        if not dragons:
            self.draw_text_line(screen, "No matching records.", list_rect.x + 12, y + 10, self.small, MUTED)
        for dragon in dragons:
            row = pygame.Rect(list_rect.x + 3, y + 3, list_rect.width - 6, 42)
            selected = dragon is self.selected_dragon
            dead = self.is_dead(dragon)
            hovered = row.collidepoint(mouse_pos)
            if row.bottom >= list_rect.top and row.top <= list_rect.bottom:
                fill = (70, 49, 32) if hovered else ((35, 32, 29) if dead else (40, 32, 27))
                edge = GOLD if selected else ((145, 101, 56) if hovered else (73, 54, 40))
                pygame.draw.rect(screen, fill, row, border_radius=8)
                pygame.draw.rect(screen, edge, row, 2 if selected else 1, border_radius=8)
                self.draw_medallion(screen, (row.x + 22, row.centery), self.initials(dragon.name), selected, dead)
                name = ("† " if dead else "") + str(getattr(dragon, "name", "Unknown"))
                self.draw_text_line(screen, name, row.x + 43, row.y + 5, self.body_bold, MUTED if dead else CREAM)
                descriptor = f"{getattr(dragon, 'tribe', 'Unknown')} • {getattr(dragon, 'role', 'Unknown')}"
                self.draw_text_line(screen, descriptor, row.x + 43, row.y + 23, self.tiny, MUTED)
                self.buttons.append(ClickTarget(row, lambda value=dragon: self.select_dragon(value)))
            y += 48
        screen.set_clip(old_clip)

    # Record tabs ----------------------------------------------------

    def draw_tabs(self, screen, rect, mouse_pos):
        tab_width = (rect.width - 28) // 4
        for index, tab in enumerate(self.TABS):
            button = ArchiveButton(
                pygame.Rect(rect.x + 14 + index * tab_width, rect.y + 53, tab_width - 6, 31),
                tab.upper(),
                lambda value=tab: self.set_tab(value),
                selected=self.active_tab == tab,
            )
            self.buttons.append(button)
            button.draw(screen, self.tiny, mouse_pos)

    def draw_record_tab(self, screen, rect, mouse_pos):
        dragon = self.selected_dragon
        portrait = pygame.Rect(rect.x + 8, rect.y + 6, 270, rect.height - 12)
        details = pygame.Rect(rect.x + 290, rect.y + 6, rect.width - 298, rect.height - 12)
        self.draw_panel(screen, portrait, alpha=205)
        self.draw_panel(screen, details, alpha=205)
        self.draw_text_line(screen, "ARCHIVED PORTRAIT", portrait.x + 14, portrait.y + 13, self.tiny, GOLD)
        self.draw_sprite_preview(screen, pygame.Rect(portrait.x + 7, portrait.y + 35, portrait.width - 14, 220), dragon)
        portrait_button = ArchiveButton(
            pygame.Rect(portrait.x + 55, portrait.bottom - 47, 160, 29),
            "VIEW PORTRAIT",
            self.open_portrait,
            enabled=dragon is not None,
            primary=True,
        )
        self.buttons.append(portrait_button)
        portrait_button.draw(screen, self.tiny, mouse_pos)
        if not dragon:
            return
        if ensure_dragon_flavor:
            ensure_dragon_flavor(dragon)
        sections = (
            ("ARCHIVE RECORD", (
                ("Name", dragon.name),
                ("Tribe", getattr(dragon, "tribe", "Unknown")),
                ("Age", f"{getattr(dragon, 'age_moons', getattr(dragon, 'age', 'Unknown'))} moons"),
                ("Role", getattr(dragon, "role", "Unknown")),
                ("Rank", getattr(dragon, "rank", "None")),
                ("Status", getattr(dragon, "status", "Unknown")),
                ("Health", getattr(dragon, "health", "Unknown")),
            )),
            ("VISUAL DETAILS", (
                ("Height", getattr(dragon, "height", "Unknown")),
                ("Eyes", getattr(dragon, "eye_color", "Unknown")),
                ("Horns", getattr(dragon, "horn_type", "Unknown")),
                ("Head", getattr(dragon, "head_type", "Unknown")),
                ("Snout", getattr(dragon, "snout_type", "Unknown")),
                ("Tail", getattr(dragon, "tail_type", "Unknown")),
                ("Wings", getattr(dragon, "wing_type", "Unknown")),
                ("Body", getattr(dragon, "body_type", "Unknown")),
                ("Markings", getattr(dragon, "marking_type", "Unknown")),
            )),
        )
        y = details.y + 13
        for heading, rows in sections:
            self.draw_text_line(screen, heading, details.x + 14, y, self.body_bold, GOLD)
            y += 23
            for label, value in rows:
                self.draw_text_line(screen, f"{label}:", details.x + 14, y, self.small, MUTED)
                self.draw_text_line(screen, self.fit_text(value, self.small, details.width - 100), details.x + 83, y, self.small, TEXT)
                y += 17
            y += 8

    def draw_biography_tab(self, screen, rect):
        dragon = self.selected_dragon
        life = pygame.Rect(rect.x + 8, rect.y + 6, 210, rect.height - 12)
        biography = pygame.Rect(rect.x + 230, rect.y + 6, rect.width - 238, rect.height - 12)
        self.draw_panel(screen, life, title="Life Details", alpha=205)
        biography_title = "Life Biography" if dragon and self.is_dead(dragon) else "Biography"
        self.draw_panel(screen, biography, title=biography_title, alpha=205)
        self._detail_rect = biography
        if not dragon:
            return
        if ensure_dragon_flavor:
            ensure_dragon_flavor(dragon)
        mate = self.get_mate(dragon)
        children = self.get_children(dragon)
        rows = (
            ("Titles", ", ".join(map(str, getattr(dragon, "earned_titles", []))) or "None recorded"),
            ("Skills", ", ".join(map(str, getattr(dragon, "skills", []))) or "None recorded"),
            ("Hobbies", ", ".join(map(str, getattr(dragon, "hobbies", []))) or "None recorded"),
            ("Scars", ", ".join(map(str, getattr(dragon, "scars", []))) or "None recorded"),
            ("Friends", self.names_from_ids(getattr(dragon, "friends", []))),
            ("Rivals", self.names_from_ids(getattr(dragon, "rivals", []))),
            ("Mate", mate.name if mate else "None recorded"),
            ("Children", ", ".join(child.name for child in children) or "None recorded"),
        )
        y = life.y + 47
        for label, value in rows:
            self.draw_text_line(screen, label.upper(), life.x + 14, y, self.tiny, GOLD)
            y += 14
            y = self.draw_wrapped(screen, value, pygame.Rect(life.x + 14, y, life.width - 28, 100), self.small, TEXT, 15)
            y += 8

        events = self.get_dragon_events(dragon)
        sections = [(False, self.get_biography(dragon)), (True, "NOTABLE CHRONICLE")]
        if events:
            sections.extend(
                (False, f"• {'Moon ' + str(event.get('moon')) + ': ' if event.get('moon') is not None else ''}{event.get('text', '')}")
                for event in events
            )
        else:
            sections.append((False, "No major events have been entered into this record yet."))
        content = pygame.Rect(biography.x + 14, biography.y + 47, biography.width - 28, biography.height - 60)
        old_clip = screen.get_clip()
        screen.set_clip(content)
        y = content.y + self.detail_scroll
        total = 0
        for is_heading, paragraph in sections:
            font, color = (self.body_bold, GOLD) if is_heading else (self.small, TEXT)
            end_y = self.draw_wrapped(screen, paragraph, pygame.Rect(content.x, y, content.width, 1000), font, color, 17)
            used = max(23 if is_heading else 17, end_y - y + 7)
            y += used
            total += used
        self._detail_content_height = total
        screen.set_clip(old_clip)

    def lineage_node(self, screen, center, size, dragon=None, label="Unknown Record", relation="", selected=False):
        rect = pygame.Rect(0, 0, *size)
        rect.center = center
        dead = dragon is not None and self.is_dead(dragon)
        hovered = dragon is not None and rect.collidepoint(pygame.mouse.get_pos())
        fill = (77, 51, 32) if selected else ((40, 37, 34) if dead else (42, 34, 29))
        edge = GOLD if selected or hovered else ((88, 79, 70) if dead else BRONZE)
        pygame.draw.rect(screen, (7, 5, 4), rect.move(0, 3), border_radius=8)
        pygame.draw.rect(screen, fill, rect, border_radius=8)
        pygame.draw.rect(screen, edge, rect, 2 if selected else 1, border_radius=8)
        relation_label = self.fit_text(relation.upper(), self.tiny, rect.width - 10)
        self.draw_text_line(screen, relation_label, rect.centerx, rect.y + 10, self.tiny, MUTED, center=True)
        if dragon:
            name = ("† " if dead else "") + dragon.name
            self.draw_text_line(screen, self.fit_text(name, self.body_bold, rect.width - 12), rect.centerx, rect.y + 28, self.body_bold, MUTED if dead else CREAM, center=True)
            if rect.height >= 54:
                self.draw_text_line(screen, getattr(dragon, "tribe", "Unknown"), rect.centerx, rect.y + 44, self.tiny, MUTED, center=True)
            self.buttons.append(ClickTarget(rect, lambda value=dragon: self.select_dragon(value)))
        else:
            self.draw_text_line(screen, self.fit_text(label, self.small, rect.width - 12), rect.centerx, rect.y + 29, self.small, MUTED, center=True)
        return rect

    def draw_lineage_tab(self, screen, rect):
        self.draw_panel(screen, rect, alpha=205)
        dragon = self.selected_dragon
        if not dragon:
            return
        self.draw_text_line(screen, "ANCESTRAL LINE", rect.x + 16, rect.y + 12, self.body_bold, GOLD)
        self.draw_text_line(screen, "Click a relative to centre their record.", rect.x + 330, rect.y + 14, self.tiny, MUTED)
        recorded_parent_ids = self.get_id_list(dragon, "parents")
        parents = self.get_parents(dragon)
        while len(parents) < 2:
            parents.append(None)
        grandparents = []
        for parent in parents:
            ancestors = self.get_parents(parent) if parent else []
            while len(ancestors) < 2:
                ancestors.append(None)
            grandparents.extend(ancestors[:2])

        left, top = rect.x, rect.y
        grand_centers = [(left + 73, top + 77), (left + 213, top + 77), (left + 405, top + 77), (left + 545, top + 77)]
        parent_centers = [(left + 145, top + 161), (left + 475, top + 161)]
        selected_center, mate_center = (left + 255, top + 260), (left + 493, top + 260)
        connector = (110, 78, 51)
        for index, parent_center in enumerate(parent_centers):
            for grand_center in grand_centers[index * 2:index * 2 + 2]:
                pygame.draw.line(screen, connector, (grand_center[0], grand_center[1] + 24), (parent_center[0], parent_center[1] - 27), 2)
            pygame.draw.line(screen, connector, (parent_center[0], parent_center[1] + 27), (selected_center[0], selected_center[1] - 31), 2)

        mate = self.get_mate(dragon)
        if mate:
            pygame.draw.line(screen, GOLD, (selected_center[0] + 84, selected_center[1]), (mate_center[0] - 69, mate_center[1]), 2)
        children = self.get_children(dragon)
        visible_children = children[:4]
        child_centers = []
        if visible_children:
            step = 545 / len(visible_children)
            child_centers = [(int(left + 47 + step * (index + 0.5)), top + 355) for index in range(len(visible_children))]
            junction_y = top + 310
            pygame.draw.line(screen, connector, (selected_center[0], selected_center[1] + 31), (selected_center[0], junction_y), 2)
            if mate:
                pygame.draw.line(screen, connector, (mate_center[0], mate_center[1] + 31), (mate_center[0], junction_y), 2)
            pygame.draw.line(screen, connector, (min(c[0] for c in child_centers), junction_y), (max(c[0] for c in child_centers), junction_y), 2)
            for child_center in child_centers:
                pygame.draw.line(screen, connector, (child_center[0], junction_y), (child_center[0], child_center[1] - 25), 2)

        for index, center in enumerate(grand_centers):
            parent = parents[index // 2]
            if parent:
                label = "Unknown Record" if self.get_id_list(parent, "parents") else "No Earlier Record"
            else:
                label = "Unknown Record" if recorded_parent_ids else "No Earlier Record"
            grandparent = grandparents[index]
            relation = "Grandparent • Founding" if grandparent and not self.get_id_list(grandparent, "parents") else "Grandparent"
            self.lineage_node(screen, center, (124, 48), grandparent, label, relation)
        for index, center in enumerate(parent_centers):
            parent = parents[index]
            label = "Unknown Record" if recorded_parent_ids else "No Earlier Record"
            relation = "Parent • Founding" if parent and not self.get_id_list(parent, "parents") else "Parent"
            self.lineage_node(screen, center, (145, 54), parent, label, relation)
        selected_relation = "Selected • Founding" if not recorded_parent_ids else "Selected"
        self.lineage_node(screen, selected_center, (170, 62), dragon, relation=selected_relation, selected=True)
        self.lineage_node(screen, mate_center, (138, 58), mate, "None recorded", "Mate")
        for child, center in zip(visible_children, child_centers):
            self.lineage_node(screen, center, (126, 50), child, relation="Child")
        if len(children) > 4:
            self.draw_text_line(screen, f"+{len(children) - 4} more descendants", rect.right - 150, rect.bottom - 18, self.tiny, MUTED)
        elif not children:
            self.draw_text_line(screen, "No descendants recorded.", rect.centerx, rect.bottom - 18, self.tiny, MUTED, center=True)

    def draw_legacy_tab(self, screen, rect):
        self.draw_panel(screen, rect, alpha=205)
        self._detail_rect = rect
        dragon = self.selected_dragon
        if not dragon:
            return
        dead = self.is_dead(dragon)
        self.draw_text_line(screen, "SEALED OBITUARY" if dead else "AN OPEN RECORD", rect.centerx, rect.y + 34, self.heading, MUTED if dead else GOLD, center=True)
        pygame.draw.line(screen, BRONZE, (rect.x + 90, rect.y + 57), (rect.right - 90, rect.y + 57), 1)
        if dead:
            body = self.get_saved_obituary(dragon)
            events = self.get_dragon_events(dragon, 4)
            if events:
                body += "\n\nREMEMBERED DEEDS\n" + "\n".join(f"• {event.get('text', '')}" for event in events)
        else:
            titles = list(getattr(dragon, "earned_titles", []))
            children = self.get_children(dragon)
            body = (
                f"{dragon.name}'s story is still being written. The archive will seal a permanent obituary "
                "when their life ends; until then, it records the shape of the legacy they are building.\n\n"
                f"CURRENT ROLE\n{getattr(dragon, 'role', 'Unknown')}\n\n"
                f"EARNED TITLES\n{', '.join(map(str, titles)) or 'None recorded'}\n\n"
                f"DESCENDANTS\n{', '.join(child.name for child in children) or 'None recorded'}\n\n"
                f"MAJOR RECORDED EVENTS\n{len(self.get_dragon_events(dragon))}"
            )
        content = pygame.Rect(rect.x + 65, rect.y + 78, rect.width - 130, rect.height - 95)
        old_clip = screen.get_clip()
        screen.set_clip(content)
        y = content.y + self.detail_scroll
        total = 0
        for paragraph in body.split("\n"):
            heading = paragraph.isupper() and len(paragraph) < 40
            end_y = self.draw_wrapped(screen, paragraph, pygame.Rect(content.x, y, content.width, 1000), self.body_bold if heading else self.small, GOLD if heading else TEXT, 18)
            used = max(18, end_y - y + 5)
            y += used
            total += used
        self._detail_content_height = total
        screen.set_clip(old_clip)

    def draw_archive_record(self, screen, rect, mouse_pos):
        self.draw_panel(screen, rect)
        dragon = self.selected_dragon
        name = getattr(dragon, "name", "No Record Selected") if dragon else "No Record Selected"
        descriptor = (
            f"{getattr(dragon, 'tribe', 'Unknown')}  •  {getattr(dragon, 'role', 'Unknown')}  •  {getattr(dragon, 'status', 'Unknown')}"
            if dragon else "Choose a dragon from the archive index."
        )
        self.draw_text_line(screen, str(name).upper(), rect.x + 18, rect.y + 13, self.heading, CREAM)
        self.draw_text_line(screen, descriptor, rect.x + 290, rect.y + 17, self.tiny, MUTED)
        self.draw_tabs(screen, rect, mouse_pos)
        content = pygame.Rect(rect.x + 12, rect.y + 91, rect.width - 24, rect.height - 103)
        self._detail_rect = content
        if self.active_tab == "Record":
            self.draw_record_tab(screen, content, mouse_pos)
        elif self.active_tab == "Biography":
            self.draw_biography_tab(screen, content)
        elif self.active_tab == "Lineage":
            self.draw_lineage_tab(screen, content)
        else:
            self.draw_legacy_tab(screen, content)

    # Main screen ----------------------------------------------------

    def draw(self, screen):
        self.buttons.clear()
        mouse_pos = pygame.mouse.get_pos()
        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill((22, 18, 15))
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((10, 7, 5, 148))
        screen.blit(veil, (0, 0))

        pygame.draw.rect(screen, (25, 17, 12), (18, 18, 964, 624), border_radius=18)
        pygame.draw.rect(screen, BRONZE, (18, 18, 964, 624), 3, border_radius=18)
        pygame.draw.rect(screen, (73, 49, 34), (27, 27, 946, 606), 1, border_radius=15)

        header = pygame.Rect(306, 28, 388, 76)
        self.draw_panel(screen, header, alpha=240)
        self.draw_text_line(screen, "SCROLL LIBRARY", header.centerx, header.y + 27, self.title_fantasy, CREAM, center=True)
        self.draw_text_line(screen, "The tribe's memory, preserved in ink.", header.centerx, header.y + 53, self.small, MUTED, center=True)

        dragons = self.get_dragons()
        living = sum(not self.is_dead(dragon) for dragon in dragons)
        badges = (
            (pygame.Rect(48, 38, 225, 58), "ARCHIVED LIVES", str(len(dragons)), f"{living} living • {len(dragons) - living} deceased"),
            (pygame.Rect(727, 38, 225, 58), "CURRENT MOON", str(getattr(self.world, "moon", 0)), str(getattr(self.world, "tribe_name", "Tribal archive"))),
        )
        for badge, heading, value, detail in badges:
            self.draw_panel(screen, badge, alpha=235)
            self.draw_text_line(screen, heading, badge.x + 15, badge.y + 9, self.tiny, MUTED)
            self.draw_text_line(screen, value, badge.x + 15, badge.y + 28, self.heading, GOLD)
            self.draw_text_line(screen, self.fit_text(detail, self.tiny, 140), badge.x + 66, badge.y + 33, self.tiny, MUTED)

        self.draw_roster(screen, pygame.Rect(28, 118, 280, 505), mouse_pos)
        self.draw_archive_record(screen, pygame.Rect(323, 118, 649, 505), mouse_pos)
        return_button = ArchiveButton(
            pygame.Rect(422, 651, 156, 36),
            "RETURN TO MAP",
            lambda: self.change_screen("locations"),
        )
        self.buttons.append(return_button)
        return_button.draw(screen, self.small, mouse_pos)

    def update(self, dt):
        pass

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and self.search_active:
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                self.search_active = False
            elif event.key == pygame.K_BACKSPACE:
                self.search_text = self.search_text[:-1]
                self.roster_scroll = 0
            elif event.unicode and event.unicode.isprintable() and len(self.search_text) < 28:
                self.search_text += event.unicode
                self.roster_scroll = 0

        if event.type == pygame.MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()
            if self._roster_rect.collidepoint(mouse_pos):
                maximum = max(0, self._roster_content_height - self._roster_rect.height)
                self.roster_scroll = clamp(self.roster_scroll + event.y * 28, -maximum, 0)
            elif self._detail_rect.collidepoint(mouse_pos) and self.active_tab in {"Biography", "Legacy"}:
                maximum = max(0, self._detail_content_height - self._detail_rect.height + 70)
                self.detail_scroll = clamp(self.detail_scroll + event.y * 28, -maximum, 0)

        for button in self.buttons:
            button.handle_event(event)
