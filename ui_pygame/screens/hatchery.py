import math
import pygame
from pathlib import Path

from core.sim.logging import log_event
from ui_pygame.core.base_screen import BaseScreen


WIDTH, HEIGHT = 1000, 700

TEXT = (236, 222, 196)
MUTED = (176, 158, 132)
GOLD = (227, 183, 84)
BRONZE = (133, 91, 53)
CREAM = (248, 230, 192)
RED = (205, 82, 66)
GREEN = (111, 178, 120)


def find_project_root():
    """Find the project folder without depending on this file's depth."""
    file_path = Path(__file__).resolve()
    candidates = [file_path.parent, *file_path.parents, Path.cwd(), *Path.cwd().parents]
    checked = set()

    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in checked:
            continue
        checked.add(candidate)
        if (candidate / "assets").is_dir():
            return candidate

    return file_path.parents[2]


class ClickTarget:
    def __init__(self, rect, callback):
        self.rect = pygame.Rect(rect)
        self.callback = callback

    def handle_event(self, event):
        if (
            event.type == pygame.MOUSEBUTTONUP
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        ):
            self.callback()


class HatcheryButton(ClickTarget):
    def __init__(
        self,
        rect,
        label,
        callback,
        enabled=True,
        primary=False,
        selected=False,
    ):
        super().__init__(rect, callback)
        self.label = label
        self.enabled = enabled
        self.primary = primary
        self.selected = selected

    def handle_event(self, event):
        if self.enabled:
            super().handle_event(event)

    def draw(self, screen, font, mouse_pos):
        hovered = self.enabled and self.rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (8, 5, 4), self.rect.move(0, 4), border_radius=8)

        if not self.enabled:
            edge, fill, text_color = (76, 69, 61), (42, 39, 35), (118, 109, 97)
        elif self.selected:
            edge, fill, text_color = GOLD, (90, 57, 29), CREAM
        elif self.primary:
            edge = GOLD if hovered else (177, 121, 53)
            fill = (107, 63, 29) if hovered else (76, 48, 28)
            text_color = CREAM
        else:
            edge = GOLD if hovered else (111, 80, 55)
            fill = (65, 48, 36) if hovered else (43, 36, 32)
            text_color = TEXT

        pygame.draw.rect(screen, edge, self.rect, border_radius=8)
        inner = self.rect.inflate(-5, -5)
        pygame.draw.rect(screen, fill, inner, border_radius=6)
        pygame.draw.line(
            screen,
            (213, 167, 94) if self.enabled else (74, 68, 60),
            (inner.left + 8, inner.top + 3),
            (inner.right - 8, inner.top + 3),
            1,
        )
        image = font.render(self.label, True, text_color)
        screen.blit(image, image.get_rect(center=self.rect.center))


class HatcheryScreen(BaseScreen):
    def __init__(self, world, change_screen):
        super().__init__()

        self.world = world
        self.change_screen = change_screen
        self.selected_egg_index = 0
        self.selected_dragon = None
        self.egg_scroll = 0
        self.list_scroll = 0
        self.log_scroll = 0

        self.fantasy_title = pygame.font.SysFont("georgia", 30, bold=True)
        self.fantasy_heading = pygame.font.SysFont("georgia", 18, bold=True)
        self.fantasy_body = pygame.font.SysFont("georgia", 14)
        self.fantasy_body_bold = pygame.font.SysFont("georgia", 14, bold=True)
        self.fantasy_small = pygame.font.SysFont("georgia", 12)
        self.fantasy_tiny = pygame.font.SysFont("georgia", 11)
        self.medallion_font = pygame.font.SysFont("georgia", 16, bold=True)

        project_root = find_project_root()
        tribe_slug = (
            str(getattr(self.world, "tribe_name", ""))
            .lower()
            .replace(" tribe", "")
            .replace(" ", "")
        )
        candidates = [
            project_root / "assets" / tribe_slug / "hatchery_bg.png",
            project_root / "assets" / "menu" / "hatchery_bg.png",
            project_root / "assets" / "menu" / "training_bg.png",
        ]
        bg_path = next((path for path in candidates if path.exists()), candidates[-1])

        try:
            self.bg_image = pygame.image.load(str(bg_path)).convert()
            self.bg_image = pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT))
        except Exception as error:
            print(f"Could not load hatchery background: {error}")
            self.bg_image = None

        egg_path = project_root / "assets" / "hatchery" / "egg.png"
        try:
            self.egg_image = pygame.image.load(str(egg_path)).convert_alpha()
            self.egg_image = pygame.transform.smoothscale(self.egg_image, (150, 150))
        except Exception as error:
            print(f"Could not load hatchery egg image: {error}")
            self.egg_image = None

    def update(self, dt):
        pass

    def get_eggs(self):
        eggs = getattr(self.world, "eggs", [])
        for egg in eggs:
            self.ensure_egg_state(egg)
        return eggs

    def ensure_egg_state(self, egg):
        if not hasattr(self.world, "world_flags") or self.world.world_flags is None:
            self.world.world_flags = {}

        if "egg_id" not in egg:
            existing_ids = [
                existing.get("egg_id", 0)
                for existing in getattr(self.world, "eggs", [])
                if isinstance(existing, dict)
            ]
            next_id = max(
                int(self.world.world_flags.get("next_egg_id", 1)),
                max(existing_ids, default=0) + 1,
            )
            egg["egg_id"] = next_id
            self.world.world_flags["next_egg_id"] = next_id + 1

        starting_condition = {
            "healthy": 86,
            "stable": 72,
            "good": 78,
            "concerning": 48,
            "fragile": 42,
            "critical": 28,
            "unknown": 68,
        }.get(str(egg.get("condition", "stable")).lower(), 70)
        egg.setdefault("condition_score", starting_condition)
        egg.setdefault("last_inspected_moon", -1)
        egg.setdefault("last_tended_moon", -1)
        egg.setdefault("last_healer_check_moon", -1)
        egg.setdefault("reinforced_until_moon", -1)
        egg.setdefault("incident_cooldown_until", -1)
        egg.setdefault("pending_incident", False)
        egg.setdefault("care_actions_received", 0)
        egg["condition_score"] = max(0, min(100, int(egg["condition_score"])))
        egg["condition"] = self.condition_label(egg["condition_score"])
        return egg

    def condition_label(self, score):
        if score >= 80:
            return "Healthy"
        if score >= 60:
            return "Stable"
        if score >= 40:
            return "Concerning"
        return "Critical"

    def reset_action_counter_if_needed(self):
        if not hasattr(self.world, "world_flags") or self.world.world_flags is None:
            self.world.world_flags = {}
        moon = getattr(self.world, "moon", 0)
        if self.world.world_flags.get("hatchery_action_moon") != moon:
            self.world.world_flags["hatchery_action_moon"] = moon
            self.world.world_flags["hatchery_actions_used"] = 0

    def get_actions_remaining(self):
        self.reset_action_counter_if_needed()
        used = int(self.world.world_flags.get("hatchery_actions_used", 0))
        return max(0, 2 - used)

    def spend_hatchery_action(self):
        if self.get_actions_remaining() <= 0:
            return False
        self.world.world_flags["hatchery_actions_used"] = (
            int(self.world.world_flags.get("hatchery_actions_used", 0)) + 1
        )
        return True

    def get_hatching_reveal(self):
        flags = getattr(self.world, "world_flags", {}) or {}
        reveals = flags.get("hatching_reveals", [])
        return reveals[0] if reveals else None

    def dismiss_hatching_reveal(self):
        flags = getattr(self.world, "world_flags", {}) or {}
        reveals = flags.get("hatching_reveals", [])
        if reveals:
            reveals.pop(0)
        flags["hatching_reveals"] = reveals

    def get_healers(self):
        return [
            dragon
            for dragon in self.get_dragons()
            if str(getattr(dragon, "role", "")).lower() == "healer"
        ]

    def caretaker_suitability(self, dragon, egg):
        if dragon is None or egg is None:
            return 0

        score = 50
        role = str(getattr(dragon, "role", "")).lower()
        score += {
            "healer": 23,
            "elder": 18,
            "hunter": 7,
            "scout": 5,
            "warrior": 3,
            "deputy": 6,
            "leader": 6,
            "queen": 8,
            "dragonet": -35,
        }.get(role, 0)

        if str(getattr(dragon, "health", "Healthy")).lower() != "healthy":
            score -= 22

        mood = str(getattr(dragon, "mood", "")).lower()
        if any(word in mood for word in ("angry", "stressed", "strained", "grieving")):
            score -= 10
        elif any(word in mood for word in ("calm", "content", "hopeful")):
            score += 5

        personality = str(getattr(dragon, "personality", "")).lower()
        if any(word in personality for word in ("patient", "gentle", "loyal", "protective", "caring")):
            score += 10
        if any(word in personality for word in ("aggressive", "impulsive", "selfish", "cruel", "reckless")):
            score -= 12

        parent_names = {egg.get("mother"), egg.get("father")}
        parents = [candidate for candidate in self.get_dragons() if candidate.name in parent_names]
        if dragon in parents:
            score += 15

        trust = getattr(dragon, "trust", {})
        if isinstance(trust, dict) and parents:
            parent_trust = sum(float(trust.get(parent.id, 0)) for parent in parents) / len(parents)
            score += int(max(-10, min(10, parent_trust * 3)))

        workload = sum(
            1
            for candidate in self.get_eggs()
            if candidate.get("caretaker") == getattr(dragon, "name", None)
        )
        score -= max(0, workload - 1) * 13
        return max(10, min(95, int(score)))

    def suitability_label(self, score):
        if score >= 78:
            return "Excellent", GREEN
        if score >= 62:
            return "Good", GOLD
        if score >= 48:
            return "Capable", TEXT
        return "Risky", RED

    def get_selected_egg(self):
        eggs = self.get_eggs()
        if not eggs:
            self.selected_egg_index = 0
            return None
        self.selected_egg_index %= len(eggs)
        return eggs[self.selected_egg_index]

    def get_dragons(self):
        return [
            dragon
            for dragon in getattr(self.world, "dragons", [])
            if getattr(dragon, "status", "") == "Alive"
            and str(getattr(dragon, "role", "")).lower() != "dragonet"
        ]

    def get_selected_dragon(self):
        dragons = self.get_dragons()
        if self.selected_dragon in dragons:
            return self.selected_dragon
        if dragons:
            self.selected_dragon = dragons[0]
            return self.selected_dragon
        self.selected_dragon = None
        return None

    def select_egg(self, index):
        self.selected_egg_index = index
        self.log_scroll = 0

    def select_dragon(self, dragon):
        self.selected_dragon = dragon

    def dragon_id(self, dragon):
        return getattr(dragon, "id", getattr(dragon, "dragon_id", None))

    def egg_involved_ids(self, egg, extra_dragon=None):
        names = {
            egg.get("mother"),
            egg.get("father"),
            egg.get("caretaker"),
        }
        ids = []
        for dragon in self.get_dragons():
            if getattr(dragon, "name", None) in names:
                dragon_id = self.dragon_id(dragon)
                if dragon_id is not None:
                    ids.append(dragon_id)
        if extra_dragon is not None:
            dragon_id = self.dragon_id(extra_dragon)
            if dragon_id is not None:
                ids.append(dragon_id)
        return list(dict.fromkeys(ids))

    def add_hatchery_event(self, text, egg=None, extra_dragon=None, importance=1):
        involved_ids = self.egg_involved_ids(egg, extra_dragon) if egg else []
        log_event(
            self.world,
            text,
            involved_ids=involved_ids,
            event_type="hatchery",
            importance=importance,
        )

    def run_action(self, action):
        egg = self.get_selected_egg()
        if egg is None:
            self.add_hatchery_event("There are no eggs in the hatchery.")
            return

        if action == "inspect":
            current_moon = getattr(self.world, "moon", 0)
            if egg.get("last_inspected_moon") == current_moon:
                return
            egg["last_inspected_moon"] = current_moon
            self.add_hatchery_event(
                f"The egg of {egg.get('mother', 'Unknown')} and "
                f"{egg.get('father', 'Unknown')} was inspected. It appears "
                f"{egg.get('size', 'ordinary')} with a "
                f"{egg.get('shell_color', 'plain')} shell. It "
                f"{egg.get('movement', 'rests quietly')}.",
                egg=egg,
            )
            self.log_scroll = 0

        elif action == "tend":
            current_moon = getattr(self.world, "moon", 0)
            if egg.get("last_tended_moon") == current_moon:
                return
            if not self.spend_hatchery_action():
                return
            egg["condition_score"] = min(100, egg.get("condition_score", 70) + 10)
            egg["condition"] = self.condition_label(egg["condition_score"])
            egg["last_tended_moon"] = current_moon
            egg["reinforced_until_moon"] = current_moon + 1
            egg["care_actions_received"] = egg.get("care_actions_received", 0) + 1
            self.add_hatchery_event(
                f"The nest holding the egg of {egg.get('mother', 'Unknown')} and "
                f"{egg.get('father', 'Unknown')} was warmed and reinforced.",
                egg=egg,
                importance=2,
            )
            self.log_scroll = 0

        elif action == "healer":
            current_moon = getattr(self.world, "moon", 0)
            healers = self.get_healers()
            if not healers or egg.get("last_healer_check_moon") == current_moon:
                return
            if not self.spend_hatchery_action():
                return
            healer = max(
                healers,
                key=lambda dragon: float(getattr(dragon, "healer_skill", 1.0)),
            )
            improvement = 14 + int(max(0, float(getattr(healer, "healer_skill", 1.0)) - 1.0) * 3)
            egg["condition_score"] = min(100, egg.get("condition_score", 70) + improvement)
            egg["condition"] = self.condition_label(egg["condition_score"])
            egg["last_healer_check_moon"] = current_moon
            egg["care_actions_received"] = egg.get("care_actions_received", 0) + 1
            self.add_hatchery_event(
                f"{healer.name} examined the egg of {egg.get('mother', 'Unknown')} and "
                f"{egg.get('father', 'Unknown')}; its condition improved.",
                egg=egg,
                extra_dragon=healer,
                importance=3,
            )
            self.log_scroll = 0

        elif action == "caretaker":
            selected = self.get_selected_dragon()
            if selected is None:
                return
            if egg.get("caretaker") == selected.name:
                return

            egg["caretaker"] = selected.name
            suitability = self.caretaker_suitability(selected, egg)
            egg["caretaker_suitability"] = suitability
            rating, _ = self.suitability_label(suitability)
            self.add_hatchery_event(
                f"{selected.name} was assigned to care for the egg of "
                f"{egg.get('mother', 'Unknown')} and {egg.get('father', 'Unknown')}. "
                f"They appear to be a {rating.lower()} match for the nest.",
                egg=egg,
                extra_dragon=selected,
                importance=2,
            )
            self.log_scroll = 0

    def draw_beveled_panel(
        self,
        screen,
        rect,
        fill=(28, 23, 20, 218),
        edge=BRONZE,
        cut=12,
    ):
        rect = pygame.Rect(rect)
        x, y, width, height = rect
        points = [
            (x + cut, y),
            (x + width - cut, y),
            (x + width, y + cut),
            (x + width, y + height - cut),
            (x + width - cut, y + height),
            (x + cut, y + height),
            (x, y + height - cut),
            (x, y + cut),
        ]
        pygame.draw.polygon(screen, (8, 5, 4), [(px, py + 5) for px, py in points])
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        local_points = [(px - x, py - y) for px, py in points]
        pygame.draw.polygon(panel, fill, local_points)
        screen.blit(panel, rect.topleft)
        pygame.draw.lines(screen, edge, True, points, 2)
        pygame.draw.line(
            screen,
            (208, 163, 94),
            (x + cut + 8, y + 5),
            (x + width - cut - 8, y + 5),
            1,
        )

    def draw_divider(self, screen, x1, x2, y):
        pygame.draw.line(screen, (76, 52, 37), (x1, y), (x2, y), 2)
        pygame.draw.circle(screen, GOLD, ((x1 + x2) // 2, y), 3)

    def draw_scroll_track(self, screen, rect, scroll, content_height, visible_height):
        if content_height <= visible_height:
            return
        track = pygame.Rect(rect.right - 6, rect.y + 4, 3, rect.height - 8)
        pygame.draw.rect(screen, (72, 57, 44), track, border_radius=2)
        thumb_height = max(22, int(track.height * visible_height / content_height))
        max_scroll = max(1, content_height - visible_height)
        travel = track.height - thumb_height
        thumb_y = track.y + int((-scroll / max_scroll) * travel)
        pygame.draw.rect(screen, GOLD, (track.x, thumb_y, 3, thumb_height), border_radius=2)

    def draw_medallion(self, screen, center, label, color, selected=False, radius=20):
        pygame.draw.circle(screen, (8, 5, 4), (center[0], center[1] + 3), radius + 5)
        pygame.draw.circle(screen, GOLD if selected else (112, 81, 55), center, radius + 4)
        pygame.draw.circle(screen, (34, 28, 24), center, radius)
        pygame.draw.circle(screen, color, center, radius - 5)
        image = self.medallion_font.render(label[:2].upper(), True, CREAM)
        screen.blit(image, image.get_rect(center=center))

    def wrap_lines(self, text, font, width):
        words = str(text).split()
        if not words:
            return []
        lines = []
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            if font.size(trial)[0] <= width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def fit_text(self, text, font, width):
        value = str(text)
        if font.size(value)[0] <= width:
            return value
        while len(value) > 3 and font.size(value + "...")[0] > width:
            value = value[:-1]
        return value.rstrip() + "..."

    def egg_progress(self, egg):
        try:
            age = float(egg.get("age", 0))
            hatch_time = max(1.0, float(egg.get("hatch_time", 1)))
            return max(0.0, min(1.0, age / hatch_time))
        except (TypeError, ValueError):
            return 0.0

    def egg_status(self, egg):
        progress = self.egg_progress(egg)
        condition = str(egg.get("condition", "Stable")).strip() or "Stable"
        if progress >= 0.9:
            return "Hatching soon", GOLD
        if condition.lower() not in {"stable", "healthy", "good", "unknown"}:
            return condition.title(), RED
        if progress >= 0.55:
            return "Developing", GREEN
        return condition.title(), MUTED

    def draw_egg_icon(self, screen, center, scale=1.0, selected=False):
        width = int(38 * scale)
        height = int(50 * scale)
        shadow = pygame.Rect(0, 0, int(width * 1.15), int(height * 0.28))
        shadow.center = (center[0], center[1] + int(height * 0.43))
        pygame.draw.ellipse(screen, (12, 8, 5), shadow)
        egg_rect = pygame.Rect(0, 0, width, height)
        egg_rect.center = center
        pygame.draw.ellipse(screen, GOLD if selected else (119, 86, 57), egg_rect.inflate(6, 6))
        pygame.draw.ellipse(screen, (213, 192, 151), egg_rect)
        shine = pygame.Rect(
            egg_rect.x + int(width * 0.20),
            egg_rect.y + int(height * 0.16),
            max(3, int(width * 0.16)),
            max(6, int(height * 0.28)),
        )
        pygame.draw.ellipse(screen, (244, 229, 193), shine)

    def draw_egg_roster(self, screen, rect, mouse_pos):
        self.draw_beveled_panel(screen, rect, fill=(27, 23, 20, 220), edge=(111, 76, 50))
        title = self.fantasy_heading.render("INCUBATING EGGS", True, CREAM)
        screen.blit(title, (rect.x + 18, rect.y + 17))
        count = self.fantasy_small.render(f"{len(self.get_eggs())} nests under watch", True, GOLD)
        screen.blit(count, (rect.x + 18, rect.y + 44))
        self.draw_divider(screen, rect.x + 17, rect.right - 17, rect.y + 68)

        list_rect = pygame.Rect(rect.x + 10, rect.y + 78, rect.width - 20, rect.height - 91)
        eggs = self.get_eggs()
        row_height = 78
        content_height = len(eggs) * row_height
        visible_height = list_rect.height
        max_scroll = max(0, content_height - visible_height)
        self.egg_scroll = max(-max_scroll, min(0, self.egg_scroll))

        old_clip = screen.get_clip()
        screen.set_clip(list_rect)

        if not eggs:
            empty = self.fantasy_body.render("The nests are quiet.", True, MUTED)
            screen.blit(empty, empty.get_rect(center=(list_rect.centerx, list_rect.y + 65)))
            hint_lines = self.wrap_lines(
                "New eggs will appear here when the tribe's next generation begins.",
                self.fantasy_small,
                list_rect.width - 34,
            )
            for index, line in enumerate(hint_lines):
                image = self.fantasy_small.render(line, True, MUTED)
                screen.blit(image, image.get_rect(center=(list_rect.centerx, list_rect.y + 94 + index * 16)))

        for index, egg in enumerate(eggs):
            row = pygame.Rect(list_rect.x + 4, list_rect.y + index * row_height + self.egg_scroll, list_rect.width - 12, 68)
            if row.bottom < list_rect.top or row.top > list_rect.bottom:
                continue

            selected = index == self.selected_egg_index
            hovered = row.collidepoint(mouse_pos)
            fill = (77, 52, 31) if selected else ((54, 43, 34) if hovered else (39, 33, 29))
            edge = GOLD if selected else ((137, 94, 55) if hovered else (73, 57, 45))
            pygame.draw.rect(screen, fill, row, border_radius=8)
            pygame.draw.rect(screen, edge, row, width=2 if selected else 1, border_radius=8)
            self.draw_egg_icon(screen, (row.x + 30, row.centery), 0.72, selected)

            mother = egg.get("mother", "Unknown")
            father = egg.get("father", "Unknown")
            parent_label = self.fit_text(
                f"{mother} & {father}",
                self.fantasy_body_bold,
                row.width - 68,
            )
            parent_text = self.fantasy_body_bold.render(parent_label, True, CREAM)
            screen.blit(parent_text, (row.x + 58, row.y + 10))
            status, status_color = self.egg_status(egg)
            status_text = self.fantasy_small.render(status, True, status_color)
            screen.blit(status_text, (row.x + 58, row.y + 34))

            progress = self.egg_progress(egg)
            bar = pygame.Rect(row.x + 58, row.bottom - 15, row.width - 70, 5)
            pygame.draw.rect(screen, (26, 21, 18), bar, border_radius=3)
            if progress > 0:
                pygame.draw.rect(
                    screen,
                    GOLD,
                    (bar.x, bar.y, max(3, int(bar.width * progress)), bar.height),
                    border_radius=3,
                )
            self.buttons.append(ClickTarget(row, lambda idx=index: self.select_egg(idx)))

        screen.set_clip(old_clip)
        self.draw_scroll_track(screen, list_rect, self.egg_scroll, content_height, visible_height)
        self.egg_list_rect = list_rect

    def draw_nest(self, screen, rect, mouse_pos):
        self.draw_beveled_panel(screen, rect, fill=(28, 23, 20, 204), edge=(128, 86, 48), cut=14)
        title = self.fantasy_heading.render("THE SELECTED NEST", True, CREAM)
        screen.blit(title, title.get_rect(center=(rect.centerx, rect.y + 27)))
        self.draw_divider(screen, rect.x + 22, rect.right - 22, rect.y + 52)

        egg = self.get_selected_egg()
        stage = pygame.Rect(rect.x + 16, rect.y + 62, rect.width - 32, 170)
        glow = pygame.Surface((stage.width, stage.height), pygame.SRCALPHA)
        for radius, alpha in ((80, 18), (62, 26), (45, 35)):
            pygame.draw.circle(glow, (231, 164, 68, alpha), (stage.width // 2, 76), radius)
        screen.blit(glow, stage.topleft)

        nest_center = (stage.centerx, stage.y + 132)
        pygame.draw.ellipse(screen, (19, 13, 9), (nest_center[0] - 93, nest_center[1] - 20, 186, 46))
        for offset, color in ((0, (91, 58, 31)), (6, (126, 79, 37)), (12, (77, 49, 29))):
            pygame.draw.arc(
                screen,
                color,
                (nest_center[0] - 89 + offset // 2, nest_center[1] - 34 + offset // 3, 178 - offset, 54),
                math.radians(8),
                math.radians(172),
                4,
            )
            pygame.draw.arc(
                screen,
                color,
                (nest_center[0] - 89 + offset // 2, nest_center[1] - 20 + offset // 3, 178 - offset, 42),
                math.radians(188),
                math.radians(352),
                3,
            )

        if egg:
            if self.egg_image:
                egg_rect = self.egg_image.get_rect(center=(stage.centerx, stage.y + 92))
                screen.blit(self.egg_image, egg_rect)
            else:
                self.draw_egg_icon(screen, (stage.centerx, stage.y + 88), 2.55, True)
        else:
            empty = self.fantasy_body.render("No egg currently rests here.", True, MUTED)
            screen.blit(empty, empty.get_rect(center=(stage.centerx, stage.y + 88)))

        details = pygame.Rect(rect.x + 18, rect.y + 240, rect.width - 36, 134)
        pygame.draw.rect(screen, (29, 24, 21, 185), details, border_radius=8)
        pygame.draw.rect(screen, (91, 64, 43), details, 1, border_radius=8)

        if egg:
            parent_name = self.fit_text(
                f"{egg.get('mother', 'Unknown')} & {egg.get('father', 'Unknown')}",
                self.fantasy_heading,
                details.width - 24,
            )
            parent_image = self.fantasy_heading.render(parent_name, True, GOLD)
            screen.blit(parent_image, parent_image.get_rect(center=(details.centerx, details.y + 21)))

            age = egg.get("age", 0)
            hatch_time = egg.get("hatch_time", "?")
            left_lines = [
                ("Age", f"{age} / {hatch_time} moons"),
                ("Shell", str(egg.get("shell_color", "Plain")).title()),
                ("Size", str(egg.get("size", "Ordinary")).title()),
            ]
            right_lines = [
                ("Movement", str(egg.get("movement", "Quiet")).capitalize()),
                ("Condition", str(egg.get("condition", "Unknown")).title()),
                ("Caretaker", str(egg.get("caretaker") or "Unassigned")),
            ]
            for column_x, lines in ((details.x + 15, left_lines), (details.x + 196, right_lines)):
                for index, (label, value) in enumerate(lines):
                    y = details.y + 49 + index * 25
                    label_image = self.fantasy_small.render(f"{label}:", True, MUTED)
                    screen.blit(label_image, (column_x, y))
                    max_width = 150 if column_x < details.centerx else 142
                    value_text = self.fit_text(value, self.fantasy_small, max_width)
                    value_image = self.fantasy_small.render(value_text, True, TEXT)
                    screen.blit(value_image, (column_x + 68, y))
        else:
            empty = self.fantasy_body.render("The hatchery has no incubating eggs.", True, MUTED)
            screen.blit(empty, empty.get_rect(center=details.center))

        current_moon = getattr(self.world, "moon", 0)
        actions_remaining = self.get_actions_remaining()
        action_status = self.fantasy_tiny.render(
            f"CARE ACTIONS REMAINING THIS MOON: {actions_remaining}/2",
            True,
            GOLD if actions_remaining else MUTED,
        )
        screen.blit(action_status, action_status.get_rect(center=(rect.centerx, rect.y + 385)))

        gap = 7
        button_y = rect.y + 398
        button_width = (rect.width - 48 - gap * 2) // 3
        inspected = egg is not None and egg.get("last_inspected_moon") == current_moon
        tended = egg is not None and egg.get("last_tended_moon") == current_moon
        healer_checked = egg is not None and egg.get("last_healer_check_moon") == current_moon
        action_buttons = [
            HatcheryButton(
                (rect.x + 17, button_y, button_width, 36),
                "INSPECTED" if inspected else "INSPECT",
                lambda: self.run_action("inspect"),
                enabled=egg is not None and not inspected,
            ),
            HatcheryButton(
                (rect.x + 17 + button_width + gap, button_y, button_width, 36),
                "TENDED" if tended else "TEND NEST",
                lambda: self.run_action("tend"),
                enabled=egg is not None and not tended and actions_remaining > 0,
                primary=True,
            ),
            HatcheryButton(
                (rect.x + 17 + (button_width + gap) * 2, button_y, button_width, 36),
                "CHECKED" if healer_checked else "HEALER",
                lambda: self.run_action("healer"),
                enabled=(
                    egg is not None
                    and bool(self.get_healers())
                    and not healer_checked
                    and actions_remaining > 0
                ),
            ),
        ]
        for action_button in action_buttons:
            self.buttons.append(action_button)
            action_button.draw(screen, self.fantasy_tiny, mouse_pos)

        log_rect = pygame.Rect(rect.x + 18, rect.y + 447, rect.width - 36, rect.height - 462)
        self.draw_hatchery_log(screen, log_rect)

    def hatchery_events(self):
        return [
            event
            for event in getattr(self.world, "event_log", [])
            if isinstance(event, dict) and event.get("type") == "hatchery"
        ]

    def draw_hatchery_log(self, screen, rect):
        label = self.fantasy_body_bold.render("HATCHERY CHRONICLE", True, GOLD)
        screen.blit(label, (rect.x, rect.y))
        line_y = rect.y + 21
        pygame.draw.line(screen, (86, 60, 42), (rect.x, line_y), (rect.right, line_y), 1)
        content_rect = pygame.Rect(rect.x, rect.y + 27, rect.width, rect.height - 27)
        events = list(reversed(self.hatchery_events()[-25:]))

        rendered = []
        for event in events:
            lines = self.wrap_lines(event.get("text", ""), self.fantasy_small, content_rect.width - 18)
            height = max(34, len(lines) * 15 + 12)
            rendered.append((lines, height))
        content_height = sum(item[1] for item in rendered)
        max_scroll = max(0, content_height - content_rect.height)
        self.log_scroll = max(-max_scroll, min(0, self.log_scroll))

        old_clip = screen.get_clip()
        screen.set_clip(content_rect)
        y = content_rect.y + self.log_scroll
        if not rendered:
            empty = self.fantasy_small.render("No hatchery entries yet.", True, MUTED)
            screen.blit(empty, (content_rect.x, content_rect.y + 8))
        for lines, height in rendered:
            pygame.draw.circle(screen, GOLD, (content_rect.x + 4, y + 8), 2)
            for index, line in enumerate(lines):
                image = self.fantasy_small.render(line, True, TEXT)
                screen.blit(image, (content_rect.x + 13, y + index * 15))
            y += height
        screen.set_clip(old_clip)
        self.draw_scroll_track(screen, content_rect, self.log_scroll, content_height, content_rect.height)
        self.log_rect = content_rect

    def draw_caretakers(self, screen, rect, mouse_pos):
        self.draw_beveled_panel(screen, rect, fill=(27, 23, 20, 220), edge=(111, 76, 50))
        title = self.fantasy_heading.render("CARETAKERS", True, CREAM)
        screen.blit(title, (rect.x + 18, rect.y + 17))
        subtitle = self.fantasy_small.render("Choose a guardian for this nest", True, MUTED)
        screen.blit(subtitle, (rect.x + 18, rect.y + 44))
        self.draw_divider(screen, rect.x + 17, rect.right - 17, rect.y + 68)

        egg = self.get_selected_egg()
        current_name = egg.get("caretaker") if egg else None
        current_box = pygame.Rect(rect.x + 13, rect.y + 79, rect.width - 26, 68)
        pygame.draw.rect(screen, (39, 33, 29), current_box, border_radius=8)
        pygame.draw.rect(screen, (80, 60, 43), current_box, 1, border_radius=8)
        self.draw_medallion(screen, (current_box.x + 31, current_box.centery), "C", (73, 111, 70), False, 18)
        label = self.fantasy_tiny.render("CURRENT CARETAKER", True, GOLD)
        screen.blit(label, (current_box.x + 59, current_box.y + 11))
        current_label = self.fit_text(current_name or "Unassigned", self.fantasy_body_bold, current_box.width - 69)
        current = self.fantasy_body_bold.render(current_label, True, TEXT if current_name else MUTED)
        screen.blit(current, (current_box.x + 59, current_box.y + 31))

        current_dragon = next(
            (dragon for dragon in self.get_dragons() if dragon.name == current_name),
            None,
        )
        if current_dragon and egg:
            current_score = self.caretaker_suitability(current_dragon, egg)
            current_rating, current_color = self.suitability_label(current_score)
            rating_image = self.fantasy_tiny.render(f"{current_rating} care", True, current_color)
            screen.blit(rating_image, (current_box.x + 59, current_box.y + 49))

        selected = self.get_selected_dragon()
        list_rect = pygame.Rect(rect.x + 10, rect.y + 160, rect.width - 20, rect.height - 230)
        dragons = self.get_dragons()
        row_height = 61
        content_height = len(dragons) * row_height
        visible_height = list_rect.height
        max_scroll = max(0, content_height - visible_height)
        self.list_scroll = max(-max_scroll, min(0, self.list_scroll))

        old_clip = screen.get_clip()
        screen.set_clip(list_rect)
        if not dragons:
            empty = self.fantasy_small.render("No living dragons available.", True, MUTED)
            screen.blit(empty, empty.get_rect(center=(list_rect.centerx, list_rect.y + 40)))

        for index, dragon in enumerate(dragons):
            row = pygame.Rect(list_rect.x + 4, list_rect.y + index * row_height + self.list_scroll, list_rect.width - 12, 52)
            if row.bottom < list_rect.top or row.top > list_rect.bottom:
                continue
            is_selected = dragon == selected
            is_current = getattr(dragon, "name", None) == current_name
            hovered = row.collidepoint(mouse_pos)
            fill = (70, 50, 32) if is_selected else ((53, 43, 35) if hovered else (39, 33, 29))
            edge = GOLD if is_selected else (GREEN if is_current else (72, 57, 45))
            pygame.draw.rect(screen, fill, row, border_radius=8)
            pygame.draw.rect(screen, edge, row, 2 if (is_selected or is_current) else 1, border_radius=8)

            initials = "".join(part[0] for part in str(getattr(dragon, "name", "?")).split()[:2]) or "?"
            self.draw_medallion(screen, (row.x + 27, row.centery), initials, (83, 67, 48), is_selected, 16)
            name_label = self.fit_text(
                getattr(dragon, "name", "Unknown"),
                self.fantasy_body_bold,
                row.width - 60,
            )
            name_image = self.fantasy_body_bold.render(name_label, True, CREAM)
            screen.blit(name_image, (row.x + 51, row.y + 8))
            role = str(getattr(dragon, "role", "Tribe member"))
            suitability = self.caretaker_suitability(dragon, egg) if egg else 0
            rating, rating_color = self.suitability_label(suitability)
            role_text = self.fit_text(
                f"{role} - {rating}",
                self.fantasy_tiny,
                row.width - 60,
            )
            role_image = self.fantasy_tiny.render(role_text, True, GREEN if is_current else rating_color)
            screen.blit(role_image, (row.x + 51, row.y + 29))
            self.buttons.append(ClickTarget(row, lambda chosen=dragon: self.select_dragon(chosen)))

        screen.set_clip(old_clip)
        self.draw_scroll_track(screen, list_rect, self.list_scroll, content_height, visible_height)
        self.caretaker_list_rect = list_rect

        can_assign = egg is not None and selected is not None and getattr(selected, "name", None) != current_name
        assign_button = HatcheryButton(
            (rect.x + 22, rect.bottom - 55, rect.width - 44, 40),
            "ASSIGN CARETAKER",
            lambda: self.run_action("caretaker"),
            enabled=can_assign,
            primary=True,
        )
        self.buttons.append(assign_button)
        assign_button.draw(screen, self.fantasy_body_bold, mouse_pos)

    def draw_hatching_reveal(self, screen, reveal, mouse_pos):
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((5, 3, 2, 205))
        screen.blit(shade, (0, 0))

        panel = pygame.Rect(230, 116, 540, 468)
        self.draw_beveled_panel(
            screen,
            panel,
            fill=(31, 24, 19, 250),
            edge=(184, 123, 55),
            cut=18,
        )

        pygame.draw.circle(screen, (94, 60, 29), (panel.centerx, panel.y + 108), 66)
        pygame.draw.circle(screen, GOLD, (panel.centerx, panel.y + 108), 66, 3)
        self.draw_egg_icon(screen, (panel.centerx, panel.y + 106), 1.85, True)

        heading = self.fantasy_small.render("A NEW DRAGONET HAS HATCHED", True, GOLD)
        screen.blit(heading, heading.get_rect(center=(panel.centerx, panel.y + 31)))
        name = self.fantasy_title.render(str(reveal.get("name", "Unknown")), True, CREAM)
        screen.blit(name, name.get_rect(center=(panel.centerx, panel.y + 207)))
        tribe = self.fantasy_body_bold.render(
            f"{reveal.get('tribe', 'Unknown')} dragonet",
            True,
            GOLD,
        )
        screen.blit(tribe, tribe.get_rect(center=(panel.centerx, panel.y + 240)))

        parents = reveal.get("parents", [])
        parent_text = " and ".join(parents) if parents else "Unknown"
        details = [
            ("Parents", parent_text),
            ("Caretaker", reveal.get("caretaker") or "None assigned"),
            ("Health", reveal.get("health", "Healthy")),
            ("Hatched", f"Moon {reveal.get('moon', getattr(self.world, 'moon', 0))}"),
        ]
        detail_box = pygame.Rect(panel.x + 66, panel.y + 270, panel.width - 132, 116)
        pygame.draw.rect(screen, (42, 33, 27), detail_box, border_radius=9)
        pygame.draw.rect(screen, (105, 72, 45), detail_box, 1, border_radius=9)
        for index, (label, value) in enumerate(details):
            y = detail_box.y + 14 + index * 25
            label_image = self.fantasy_small.render(f"{label}:", True, MUTED)
            screen.blit(label_image, (detail_box.x + 18, y))
            value_label = self.fit_text(value, self.fantasy_small, detail_box.width - 112)
            value_image = self.fantasy_small.render(value_label, True, TEXT)
            screen.blit(value_image, (detail_box.x + 104, y))

        welcome_button = HatcheryButton(
            (panel.centerx - 118, panel.bottom - 62, 236, 42),
            "WELCOME TO THE TRIBE",
            self.dismiss_hatching_reveal,
            primary=True,
        )
        self.buttons.append(welcome_button)
        welcome_button.draw(screen, self.fantasy_body_bold, mouse_pos)

    def draw(self, screen):
        self.buttons.clear()
        mouse_pos = pygame.mouse.get_pos()

        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill((31, 23, 18))

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((16, 9, 5, 103))
        screen.blit(overlay, (0, 0))

        frame = pygame.Rect(18, 12, WIDTH - 36, HEIGHT - 24)
        pygame.draw.rect(screen, (44, 29, 20), frame, width=5, border_radius=20)
        pygame.draw.rect(screen, (139, 92, 51), frame.inflate(-10, -10), width=2, border_radius=17)

        header = pygame.Rect(282, 18, 436, 73)
        self.draw_beveled_panel(screen, header, fill=(28, 22, 18, 238), edge=(151, 98, 51), cut=15)
        title = self.fantasy_title.render("THE HATCHERY", True, CREAM)
        screen.blit(title, title.get_rect(center=(header.centerx, header.y + 29)))
        subtitle = self.fantasy_small.render("Guard the tribe's next generation", True, MUTED)
        screen.blit(subtitle, subtitle.get_rect(center=(header.centerx, header.y + 54)))

        return_button = HatcheryButton(
            (823, 29, 135, 45),
            "RETURN",
            lambda: self.change_screen("locations"),
        )
        self.buttons.append(return_button)
        return_button.draw(screen, self.fantasy_body_bold, mouse_pos)

        egg_rect = pygame.Rect(31, 108, 246, 548)
        nest_rect = pygame.Rect(293, 108, 414, 548)
        caretaker_rect = pygame.Rect(723, 108, 246, 548)

        self.draw_egg_roster(screen, egg_rect, mouse_pos)
        self.draw_nest(screen, nest_rect, mouse_pos)
        self.draw_caretakers(screen, caretaker_rect, mouse_pos)

        reveal = self.get_hatching_reveal()
        if reveal:
            self.buttons.clear()
            self.draw_hatching_reveal(screen, reveal, mouse_pos)

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()
            if hasattr(self, "egg_list_rect") and self.egg_list_rect.collidepoint(mouse_pos):
                self.egg_scroll += event.y * 30
            elif hasattr(self, "caretaker_list_rect") and self.caretaker_list_rect.collidepoint(mouse_pos):
                self.list_scroll += event.y * 30
            elif hasattr(self, "log_rect") and self.log_rect.collidepoint(mouse_pos):
                self.log_scroll += event.y * 24

        for button in list(self.buttons):
            button.handle_event(event)
