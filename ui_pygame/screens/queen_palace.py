import math
from pathlib import Path

import pygame

from ui_pygame.core.base_screen import BaseScreen


try:
    from core.sim.politics import get_relation_status
except Exception:
    def get_relation_status(score):
        if score <= -75:
            return "War"
        if score <= -40:
            return "Hostile"
        if score <= -10:
            return "Uneasy"
        if score < 30:
            return "Neutral"
        if score < 70:
            return "Friendly"
        return "Allied"


try:
    from data.tribe_profiles import TRIBE_PROFILES
except Exception:
    TRIBE_PROFILES = {}


WIDTH, HEIGHT = 1000, 700

TEXT = (235, 222, 197)
MUTED = (178, 160, 134)
GOLD = (242, 201, 76)
BRONZE = (139, 95, 52)
GREEN = (105, 200, 140)
RED = (220, 76, 62)


TRIBE_COLORS = {
    "SkyWing": (184, 63, 43),
    "SeaWing": (35, 137, 162),
    "RainWing": (109, 55, 137),
    "SandWing": (202, 137, 35),
    "IceWing": (139, 198, 220),
    "NightWing": (54, 44, 104),
    "MudWing": (123, 79, 50),
    "HiveWing": (186, 108, 20),
    "SilkWing": (167, 79, 170),
    "LeafWing": (60, 133, 62),
}


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


class PalaceButton(ClickTarget):
    def __init__(self, rect, label, callback, emphasis=False):
        super().__init__(rect, callback)
        self.label = label
        self.emphasis = emphasis

    def draw(self, screen, font, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos)

        shadow = self.rect.move(0, 4)
        pygame.draw.rect(screen, (8, 5, 4), shadow, border_radius=8)

        if self.emphasis:
            edge = GOLD if hovered else (185, 124, 53)
            fill = (112, 64, 27) if hovered else (75, 47, 27)
        else:
            edge = GOLD if hovered else (118, 83, 54)
            fill = (67, 47, 34) if hovered else (43, 35, 31)

        pygame.draw.rect(screen, edge, self.rect, border_radius=8)
        inner = self.rect.inflate(-5, -5)
        pygame.draw.rect(screen, fill, inner, border_radius=6)
        pygame.draw.line(
            screen,
            (221, 177, 105),
            (inner.left + 8, inner.top + 3),
            (inner.right - 8, inner.top + 3),
            1,
        )

        image = font.render(self.label, True, (247, 228, 190))
        screen.blit(image, image.get_rect(center=self.rect.center))


class QueenPalaceScreen(BaseScreen):
    def __init__(self, world, change_screen):
        super().__init__()
        self.world = world
        self.change_screen = change_screen
        self.selected_tribe = None
        self.detail_scroll = 0

        self.fantasy_title = pygame.font.SysFont("georgia", 30, bold=True)
        self.fantasy_heading = pygame.font.SysFont("georgia", 18, bold=True)
        self.fantasy_body = pygame.font.SysFont("georgia", 14)
        self.fantasy_small = pygame.font.SysFont("georgia", 12)
        self.crest_font = pygame.font.SysFont("georgia", 17, bold=True)

        project_root = Path(__file__).resolve().parents[2]
        tribe_slug = (
            str(getattr(self.world, "tribe_name", ""))
            .lower()
            .replace(" tribe", "")
            .replace(" ", "")
        )

        tribe_bg = project_root / "assets" / tribe_slug / "queen_palace_bg.png"
        default_bg = project_root / "assets" / "menu" / "queen_palace_bg.png"
        bg_path = tribe_bg if tribe_bg.exists() else default_bg

        try:
            self.bg_image = pygame.image.load(str(bg_path)).convert()
            self.bg_image = pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT))
        except Exception as error:
            print(f"Could not load queen palace background: {error}")
            self.bg_image = None

        tribes = self.get_tribes()
        if tribes:
            self.selected_tribe = tribes[0]

    def get_status_color(self, status):
        if status in ("Friendly", "Allied"):
            return GREEN
        if status in ("Hostile", "War"):
            return RED
        if status == "Uneasy":
            return GOLD
        return TEXT

    def get_tribe_color(self, tribe):
        return TRIBE_COLORS.get(tribe, (105, 86, 70))

    def get_tribe_initials(self, tribe):
        capitals = "".join(character for character in tribe if character.isupper())
        if len(capitals) >= 2:
            return capitals[:2]
        return tribe[:2].upper()

    def apply_policy(self, action_id):
        if not self.selected_tribe:
            return

        if hasattr(self.world, "pending_choice"):
            self.world.pending_choice = {
                "type": "tribal_policy_choice",
                "tribe": self.selected_tribe,
                "location": "relations",
            }

        try:
            from core.sim.choices import resolve_choice
            resolve_choice(self.world, action_id)
        except Exception as error:
            print(f"Could not apply policy: {error}")

    def get_tribes(self):
        if hasattr(self.world, "tribal_relations"):
            return sorted(self.world.tribal_relations.keys())

        return [
            "SkyWing",
            "SeaWing",
            "RainWing",
            "SandWing",
            "IceWing",
            "NightWing",
        ]

    def get_score(self, tribe):
        return getattr(self.world, "tribal_relations", {}).get(tribe, 0)

    def get_trend(self, tribe):
        current = self.get_score(tribe)
        previous = getattr(self.world, "previous_tribal_relations", {}).get(tribe, current)

        if current > previous:
            return "Improving"
        if current < previous:
            return "Worsening"
        return "Stable"

    def get_relation_description(self, score):
        status = get_relation_status(score)

        descriptions = {
            "War": "Relations are effectively at war. Hostile incidents and violent encounters are highly likely.",
            "Hostile": "Relations are openly hostile. Border incidents, suspicion, and conflict are more likely.",
            "Uneasy": "Relations are strained and uncertain. Trust is limited, and tensions could worsen.",
            "Neutral": "Relations are neutral. Neither openly friendly nor openly hostile.",
            "Friendly": "Relations are positive. Cooperation and peaceful contact are more likely.",
            "Allied": "Relations are very strong. Mutual trust and support would be expected.",
        }
        return descriptions.get(status, "No description available.")

    def get_selected_detail_text(self):
        tribe = self.selected_tribe
        if not tribe:
            return "No tribe selected."

        score = self.get_score(tribe)
        profile = TRIBE_PROFILES.get(tribe, {})
        blurb = profile.get("blurb", "No historical data available.")

        incidents = getattr(self.world, "tribal_incidents", {}).get(tribe, [])
        incident_text = "\n".join(f"• {incident}" for incident in incidents) if incidents else "None recorded."

        return (
            f"CURRENT ASSESSMENT\n{self.get_relation_description(score)}\n\n"
            f"TRIBAL OVERVIEW\n{blurb}\n\n"
            f"RECENT INCIDENTS\n{incident_text}"
        )

    def update(self, dt):
        pass

    def draw_beveled_panel(self, screen, rect, fill=(28, 22, 20, 220), edge=BRONZE, cut=12):
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

        shadow_points = [(point_x, point_y + 5) for point_x, point_y in points]
        pygame.draw.polygon(screen, (8, 5, 4), shadow_points)

        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        local_points = [(point_x - x, point_y - y) for point_x, point_y in points]
        pygame.draw.polygon(panel, fill, local_points)
        screen.blit(panel, rect.topleft)

        pygame.draw.lines(screen, edge, True, points, 2)
        pygame.draw.line(
            screen,
            (213, 167, 94),
            (x + cut + 8, y + 5),
            (x + width - cut - 8, y + 5),
            1,
        )

    def draw_crest(self, screen, center, tribe, radius=28, selected=False):
        color = self.get_tribe_color(tribe)
        x, y = center

        pygame.draw.circle(screen, (8, 5, 4), (x, y + 4), radius + 5)
        pygame.draw.circle(screen, GOLD if selected else (116, 84, 55), center, radius + 4)
        pygame.draw.circle(screen, (34, 27, 24), center, radius)
        pygame.draw.circle(screen, color, center, radius - 5)

        highlight = tuple(min(255, channel + 45) for channel in color)
        pygame.draw.arc(
            screen,
            highlight,
            (x - radius + 8, y - radius + 8, (radius - 8) * 2, (radius - 8) * 2),
            math.radians(30),
            math.radians(150),
            3,
        )

        initials = self.crest_font.render(
            self.get_tribe_initials(tribe),
            True,
            (252, 232, 193),
        )
        screen.blit(initials, initials.get_rect(center=center))

    def draw_tribe_tile(self, screen, tribe, rect, mouse_pos):
        score = self.get_score(tribe)
        status = get_relation_status(score)
        selected = tribe == self.selected_tribe
        hovered = rect.collidepoint(mouse_pos)

        if selected:
            fill = (76, 54, 31, 235)
            edge = GOLD
        elif hovered:
            fill = (58, 45, 37, 230)
            edge = (176, 126, 70)
        else:
            fill = (31, 27, 25, 205)
            edge = (91, 68, 50)

        self.draw_beveled_panel(screen, rect, fill=fill, edge=edge, cut=8)
        self.draw_crest(screen, (rect.centerx, rect.y + 31), tribe, 23, selected)

        name_image = self.fantasy_small.render(tribe, True, TEXT)
        screen.blit(name_image, name_image.get_rect(center=(rect.centerx, rect.y + 61)))

        status_image = self.fantasy_small.render(
            f"{status}  {score:+d}",
            True,
            self.get_status_color(status),
        )
        screen.blit(status_image, status_image.get_rect(center=(rect.centerx, rect.y + 78)))

        self.buttons.append(ClickTarget(rect, lambda selected_tribe=tribe: self.select_tribe(selected_tribe)))

    def draw_relation_gauge(self, screen, rect, score, status):
        rect = pygame.Rect(rect)
        pygame.draw.rect(screen, (15, 12, 11), rect, border_radius=7)
        inner = rect.inflate(-4, -4)
        pygame.draw.rect(screen, (55, 46, 40), inner, border_radius=5)

        midpoint = inner.centerx
        clamped_score = max(-100, min(100, score))
        score_x = inner.left + int(((clamped_score + 100) / 200) * inner.width)
        gauge_color = self.get_status_color(status)

        if score_x >= midpoint:
            fill_rect = pygame.Rect(midpoint, inner.top, max(2, score_x - midpoint), inner.height)
        else:
            fill_rect = pygame.Rect(score_x, inner.top, max(2, midpoint - score_x), inner.height)

        pygame.draw.rect(screen, gauge_color, fill_rect, border_radius=4)
        pygame.draw.line(screen, (218, 194, 153), (midpoint, inner.top - 2), (midpoint, inner.bottom + 2), 1)
        pygame.draw.circle(screen, (248, 224, 176), (score_x, inner.centery), 5)
        pygame.draw.circle(screen, (42, 29, 22), (score_x, inner.centery), 5, 1)

        hostile = self.fantasy_small.render("HOSTILE", True, MUTED)
        allied = self.fantasy_small.render("ALLIED", True, MUTED)
        screen.blit(hostile, (rect.left, rect.bottom + 4))
        screen.blit(allied, (rect.right - allied.get_width(), rect.bottom + 4))

    def draw_court_roster(self, screen, rect):
        self.draw_beveled_panel(screen, rect, fill=(28, 23, 21, 215), edge=(104, 75, 50), cut=9)
        heading = self.fantasy_heading.render("COURT PRESENT", True, GOLD)
        screen.blit(heading, (rect.x + 15, rect.y + 12))

        palace_dragons = [
            dragon
            for dragon in getattr(self.world, "dragons", [])
            if getattr(dragon, "location", None) in ("queen_palace", "Queen's Palace")
        ]

        if not palace_dragons:
            empty = self.fantasy_small.render("The chamber is presently empty.", True, MUTED)
            screen.blit(empty, (rect.x + 15, rect.y + 43))
            return

        for index, dragon in enumerate(palace_dragons[:6]):
            column = index % 2
            row = index // 2
            text = f"• {dragon.name} ({getattr(dragon, 'role', 'Unknown')})"
            image = self.fantasy_small.render(text, True, TEXT)
            screen.blit(image, (rect.x + 15 + column * 153, rect.y + 43 + row * 19))

        if len(palace_dragons) > 6:
            more = self.fantasy_small.render(f"+{len(palace_dragons) - 6} more attending", True, MUTED)
            screen.blit(more, (rect.x + 15, rect.bottom - 23))

    def draw(self, screen):
        self.buttons.clear()
        mouse_pos = scale_mouse_pos(
            pygame.mouse.get_pos(),
            pygame.display.get_surface().get_size(),
        )

        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill((18, 14, 14))

        vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        vignette.fill((10, 6, 8, 82))
        screen.blit(vignette, (0, 0))

        pygame.draw.rect(screen, (111, 75, 45), (18, 16, 964, 668), width=3, border_radius=18)
        pygame.draw.rect(screen, (38, 28, 25), (25, 23, 950, 654), width=2, border_radius=15)

        self.draw_beveled_panel(
            screen,
            (250, 18, 500, 76),
            fill=(30, 22, 22, 238),
            edge=(145, 95, 52),
            cut=15,
        )
        title = self.fantasy_title.render("QUEEN'S PALACE", True, (248, 218, 163))
        screen.blit(title, title.get_rect(center=(500, 45)))
        subtitle = self.fantasy_small.render(
            "Diplomacy, foreign courts, and the posture of the tribe",
            True,
            MUTED,
        )
        screen.blit(subtitle, subtitle.get_rect(center=(500, 72)))

        return_button = PalaceButton(
            (823, 32, 130, 42),
            "RETURN",
            lambda: self.change_screen("locations"),
        )
        self.buttons.append(return_button)
        return_button.draw(screen, self.fantasy_body, mouse_pos)

        left_panel = pygame.Rect(35, 112, 345, 540)
        right_panel = pygame.Rect(400, 112, 565, 540)
        self.draw_beveled_panel(screen, left_panel, fill=(28, 23, 23, 218), edge=(112, 76, 50), cut=14)
        self.draw_beveled_panel(screen, right_panel, fill=(27, 22, 22, 224), edge=(112, 76, 50), cut=14)

        left_title = self.fantasy_heading.render("FOREIGN COURTS", True, GOLD)
        screen.blit(left_title, (55, 130))
        rule_y = 157
        pygame.draw.line(screen, (120, 82, 49), (55, rule_y), (360, rule_y), 1)

        tribes = self.get_tribes()
        tile_width = 94
        tile_height = 91
        tile_gap_x = 10
        tile_gap_y = 9
        grid_x = 55
        grid_y = 169

        for index, tribe in enumerate(tribes[:9]):
            column = index % 3
            row = index // 3
            tile = pygame.Rect(
                grid_x + column * (tile_width + tile_gap_x),
                grid_y + row * (tile_height + tile_gap_y),
                tile_width,
                tile_height,
            )
            self.draw_tribe_tile(screen, tribe, tile, mouse_pos)

        self.draw_court_roster(screen, pygame.Rect(50, 477, 315, 155))

        selected = self.selected_tribe
        if selected:
            score = self.get_score(selected)
            status = get_relation_status(score)
            trend = self.get_trend(selected)
            queen = getattr(self.world, "tribal_leaders", {}).get(selected, "Unknown")
            trait = getattr(self.world, "tribal_traits", {}).get(selected, "neutral")

            self.draw_crest(screen, (447, 165), selected, 31, True)

            selected_name = self.fantasy_title.render(selected.upper(), True, (248, 218, 163))
            screen.blit(selected_name, (491, 130))

            status_image = self.fantasy_heading.render(
                f"{status}  •  {score:+d}",
                True,
                self.get_status_color(status),
            )
            screen.blit(status_image, (492, 170))

            trend_color = GREEN if trend == "Improving" else RED if trend == "Worsening" else MUTED
            trend_image = self.fantasy_small.render(f"Trend: {trend}", True, trend_color)
            screen.blit(trend_image, (492, 198))

            queen_label = self.fantasy_small.render("RULER", True, GOLD)
            queen_value = self.fantasy_body.render(str(queen), True, TEXT)
            screen.blit(queen_label, (735, 137))
            screen.blit(queen_value, (735, 154))

            trait_label = self.fantasy_small.render("COURT TEMPERAMENT", True, GOLD)
            trait_value = self.fantasy_body.render(str(trait).title(), True, TEXT)
            screen.blit(trait_label, (735, 183))
            screen.blit(trait_value, (735, 200))

            self.draw_relation_gauge(screen, (430, 229, 505, 14), score, status)

        briefing_title = self.fantasy_heading.render("DIPLOMATIC BRIEFING", True, GOLD)
        screen.blit(briefing_title, (425, 270))
        pygame.draw.line(screen, (120, 82, 49), (425, 297), (940, 297), 1)

        detail_rect = pygame.Rect(425, 308, 515, 230)
        self.draw_beveled_panel(screen, detail_rect, fill=(35, 29, 27, 220), edge=(90, 67, 51), cut=9)

        screen.set_clip(detail_rect.inflate(-16, -14))
        self.draw_wrapped_text(
            screen,
            self.get_selected_detail_text(),
            detail_rect.x + 17,
            detail_rect.y + 14 + self.detail_scroll,
            detail_rect.width - 34,
            self.fantasy_body,
            TEXT,
        )
        screen.set_clip(None)

        pygame.draw.line(screen, (110, 78, 52), (930, 323), (930, 522), 2)
        scroll_position = int((-self.detail_scroll / 300) * 165)
        scroll_position = max(0, min(165, scroll_position))
        pygame.draw.circle(screen, GOLD, (930, 326 + scroll_position), 4)
        scroll_hint = self.fantasy_small.render("Scroll for full briefing", True, MUTED)
        screen.blit(scroll_hint, (detail_rect.right - scroll_hint.get_width(), detail_rect.bottom + 6))

        actions_title = self.fantasy_small.render("DIPLOMATIC ACTION", True, GOLD)
        screen.blit(actions_title, (425, 565))

        actions = [
            ("PEACE GESTURE", "peace_gesture"),
            ("BORDER PATROL", "border_patrol"),
            ("APPLY PRESSURE", "border_pressure"),
            ("OFFER AID", "offer_aid"),
        ]

        button_x = 425
        for label, action_id in actions:
            button = PalaceButton(
                (button_x, 590, 122, 42),
                label,
                lambda policy_id=action_id: self.apply_policy(policy_id),
                emphasis=action_id == "peace_gesture",
            )
            self.buttons.append(button)
            button.draw(screen, self.fantasy_small, mouse_pos)
            button_x += 130

    def select_tribe(self, tribe):
        self.selected_tribe = tribe
        self.detail_scroll = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            mouse_x, mouse_y = scale_mouse_pos(
                pygame.mouse.get_pos(),
                pygame.display.get_surface().get_size(),
            )

            detail_rect = pygame.Rect(425, 308, 515, 230)
            if detail_rect.collidepoint(mouse_x, mouse_y):
                self.detail_scroll += event.y * 30
                self.detail_scroll = max(-300, min(0, self.detail_scroll))

        if event.type == pygame.MOUSEBUTTONDOWN:
            scaled_pos = scale_mouse_pos(
                event.pos,
                pygame.display.get_surface().get_size(),
            )
            scaled_event = pygame.event.Event(
                event.type,
                {"pos": scaled_pos, "button": event.button},
            )

            for button in self.buttons:
                button.handle_event(scaled_event)
        else:
            for button in self.buttons:
                button.handle_event(event)


def scale_mouse_pos(pos, window_size):
    mouse_x, mouse_y = pos
    window_width, window_height = window_size

    scale_x = WIDTH / window_width
    scale_y = HEIGHT / window_height

    return int(mouse_x * scale_x), int(mouse_y * scale_y)
