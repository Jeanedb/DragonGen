import math
import pygame
from ui_pygame.core.base_screen import BaseScreen
from pathlib import Path

try:
    from core.simulation import advance_moon
except Exception:
    advance_moon = None

WIDTH, HEIGHT = 1000, 700

BG = (18, 18, 18)
TEXT = (230, 230, 230)
MUTED = (180, 180, 180)
PANEL = (28, 28, 28)
CARD = (42, 42, 42)
GOLD = (242, 201, 76)
BRONZE = (145, 101, 55)
PARCHMENT = (229, 209, 168)
PANEL_DARK = (30, 24, 20)


class ClickTarget:
    """A lightweight clickable region compatible with BaseScreen.buttons."""

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
    """Compact fantasy navigation button used by the top HUD."""

    def __init__(self, rect, label, callback):
        super().__init__(rect, callback)
        self.label = label



    def draw(self, screen, font, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos)
        shadow = self.rect.move(0, 4)
        pygame.draw.rect(screen, (10, 7, 5), shadow, border_radius=8)

        edge = GOLD if hovered else (125, 91, 57)
        fill = (83, 54, 29) if hovered else (43, 35, 29)
        pygame.draw.rect(screen, edge, self.rect, border_radius=8)
        inner = self.rect.inflate(-5, -5)
        pygame.draw.rect(screen, fill, inner, border_radius=6)
        pygame.draw.line(
            screen,
            (219, 174, 100),
            (inner.left + 7, inner.top + 3),
            (inner.right - 7, inner.top + 3),
            1,
        )

        image = font.render(self.label, True, (244, 224, 184))
        screen.blit(image, image.get_rect(center=self.rect.center))


class LocationsScreen(BaseScreen):
    def __init__(self, world, change_screen):
        super().__init__()

        self.world = world
        self.change_screen = change_screen

        self.show_advance_confirmation = False
        self.notice_popup_location = None

        self.hovered_card = None

        self.fantasy_title = pygame.font.SysFont("georgia", 30, bold=True)
        self.fantasy_heading = pygame.font.SysFont("georgia", 18, bold=True)
        self.fantasy_body = pygame.font.SysFont("georgia", 15)
        self.marker_font = pygame.font.SysFont("georgia", 14, bold=True)
        self.marker_icon_font = pygame.font.SysFont("georgia", 12, bold=True)
        self.notice_font = pygame.font.SysFont("georgia", 12, bold=True)
        self._fitted_font_cache = {}

        self.locations = [
            {
                "name": "Village Center",
                "desc": "Conversations and social interactions.",
                "id": "village",
                "icon": "VC",
                "anchor": (450, 250),
                "side": "right",
            },
            {
                "name": "Queen's Palace",
                "desc": "Diplomacy and tribal relations.",
                "id": "relations",
                "icon": "QP",
                "anchor": (108, 112),
                "side": "right",
            },
            {
                "name": "Healer's Den",
                "desc": "Healing, injuries, and recovery.",
                "id": "healer_den",
                "icon": "HD",
                "anchor": (112, 305),
                "side": "right",
            },
            {
                "name": "Training Grounds",
                "desc": "Training, sparring, and warriors.",
                "id": "training",
                "icon": "TG",
                "anchor": (865, 205),
                "side": "left",
            },
            {
                "name": "Hunting Grounds",
                "desc": "Food, hunting, and survival.",
                "id": "hunting",
                "icon": "HG",
                "anchor": (870, 350),
                "side": "left",
            },
            {
                "name": "Border Routes",
                "desc": "Patrols, threats, and outside conflict.",
                "id": "border",
                "icon": "BR",
                "anchor": (455, 520),
                "side": "right",
            },
            {
                "name": "Scroll Library",
                "desc": "History, knowledge, and records.",
                "id": "library",
                "icon": "SL",
                "anchor": (105, 500),
                "side": "right",
            },
            {
                "name": "Hatchery",
                "desc": "Dragonets, family, and future generations.",
                "id": "hatchery",
                "icon": "HA",
                "anchor": (870, 510),
                "side": "left",
            },
        ]
             
        PROJECT_ROOT = Path(__file__).resolve().parents[2]

        # Get the tribe being played.
        tribe = getattr(self.world, "tribe_name", "MudWing Tribe")

        tribe = (
            str(tribe)
            .lower()
            .replace(" tribe", "")
            .replace(" ", "")
        )

        print("LOCATION MAP TRIBE:", tribe)
        print("WORLD ATTRIBUTES:", vars(self.world))

        # Try the tribe-specific location map first.
        bg_path = PROJECT_ROOT / "assets" / tribe / "location_map.png"

        # If that tribe doesn't have a map yet, use the old generic map.
        if not bg_path.exists():
            print(f"No location map found for {tribe}. Using default.")
            bg_path = PROJECT_ROOT / "assets" / "menu" / "main_locations_bg.png"

        try:
            self.bg_image = pygame.image.load(str(bg_path)).convert()
            self.bg_image = pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT))
        except Exception as e:
            print(f"Could not load locations background: {e}")
            self.bg_image = None
        
    def advance_week(self):
        if advance_moon:
            try:
                advance_moon(self.world)
            except Exception as error:
                print(f"Could not advance moon/week: {error}")
        else:
            # Emergency fallback if the simulation import fails.
            if hasattr(self.world, "moon"):
                self.world.moon += 1

    def request_advance_week(self):
        self.show_advance_confirmation = True


    def cancel_advance_week(self):
        self.show_advance_confirmation = False


    def confirm_advance_week(self):
        self.show_advance_confirmation = False
        self.advance_week()

    def get_pending_choice_location(self):
        choice = getattr(self.world, "pending_choice", None)
        if not isinstance(choice, dict):
            return None

        # Older saves may contain choices created before locations were added.
        return choice.get("location", "relations")

    def get_location_notices(self, loc_id):
        notices = getattr(self.world, "location_notices", {})
        if not isinstance(notices, dict):
            return []

        location_notices = notices.get(loc_id, [])
        return location_notices if isinstance(location_notices, list) else []

    def get_location_notice_count(self, loc_id):
        return len(self.get_location_notices(loc_id))

    def clear_location_notices(self, loc_id):
        notices = getattr(self.world, "location_notices", None)
        if isinstance(notices, dict):
            notices.pop(loc_id, None)

    def get_location_name(self, loc_id):
        for location in self.locations:
            if location["id"] == loc_id:
                return location["name"]
        return "Location"

    def wrap_notice_text(self, text, font, max_width):
        words = str(text).split()
        if not words:
            return [""]

        lines = []
        current = words[0]

        for word in words[1:]:
            candidate = f"{current} {word}"
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word

        lines.append(current)
        return lines

    def dismiss_notice_popup(self):
        # Closing the report leaves the updates unread and the gold badge intact.
        self.notice_popup_location = None

    def enter_notice_location(self):
        loc_id = self.notice_popup_location
        if not loc_id:
            return

        self.clear_location_notices(loc_id)
        self.notice_popup_location = None
        self.change_to_location(loc_id)

    def draw_notice_popup(self, screen, mouse_pos):
        loc_id = self.notice_popup_location
        notices = self.get_location_notices(loc_id)

        # If another system cleared the notices while the popup was open,
        # continue into the destination rather than showing an empty report.
        if not notices:
            self.notice_popup_location = None
            self.change_to_location(loc_id)
            return

        darkness = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        darkness.fill((5, 3, 2, 195))
        screen.blit(darkness, (0, 0))

        panel_rect = pygame.Rect(170, 105, 660, 490)
        self.draw_beveled_panel(
            screen,
            panel_rect,
            fill=(31, 24, 20),
            edge=(176, 124, 55),
        )

        location_name = self.get_location_name(loc_id).upper()
        title = self.fantasy_title.render(
            f"NEW AT {location_name}",
            True,
            (246, 216, 158),
        )
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 148)))

        count = len(notices)
        noun = "update" if count == 1 else "updates"
        subtitle = self.fantasy_body.render(
            f"{count} unread {noun} from the tribe chronicle",
            True,
            (190, 170, 139),
        )
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 181)))

        pygame.draw.line(screen, (137, 96, 52), (215, 205), (785, 205), 1)

        # The newest five entries fit comfortably without creating another
        # scrolling screen.  Older unread entries remain available in Overview.
        visible_notices = notices[-5:]
        hidden_count = max(0, count - len(visible_notices))
        y = 224

        if hidden_count:
            hidden = self.small.render(
                f"+ {hidden_count} earlier unread updates remain in Overview",
                True,
                (181, 147, 91),
            )
            screen.blit(hidden, (225, y))
            y += 29

        for notice in visible_notices:
            if isinstance(notice, dict):
                moon = notice.get("moon", getattr(self.world, "moon", 0))
                text = notice.get("text", "New activity was recorded.")
            else:
                moon = getattr(self.world, "moon", 0)
                text = str(notice)

            lines = self.wrap_notice_text(text, self.fantasy_body, 445)

            pygame.draw.circle(screen, GOLD, (228, y + 8), 4)
            moon_image = self.small.render(
                f"MOON {moon}",
                True,
                (207, 158, 79),
            )
            screen.blit(moon_image, (244, y))

            text_y = y
            for line in lines[:2]:
                line_image = self.fantasy_body.render(
                    line,
                    True,
                    (228, 215, 191),
                )
                screen.blit(line_image, (330, text_y))
                text_y += 21

            y += max(31, 21 * min(2, len(lines)) + 8)
            if y > 455:
                break

        pygame.draw.line(screen, (137, 96, 52), (215, 495), (785, 495), 1)

        enter_btn = FantasyButton(
            (500, 520, 260, 48),
            "ENTER LOCATION",
            self.enter_notice_location,
        )
        later_btn = FantasyButton(
            (240, 520, 230, 48),
            "KEEP UNREAD",
            self.dismiss_notice_popup,
        )

        self.buttons.clear()
        for button in (later_btn, enter_btn):
            self.buttons.append(button)
            button.draw(screen, self.fantasy_body, mouse_pos)

    def open_pending_choice(self):
        location = self.get_pending_choice_location()
        if location:
            self.open_location(location)

    def draw_advance_confirmation(self, screen, mouse_pos):
        # Darken and temporarily disable everything behind the prompt.
        darkness = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        darkness.fill((5, 3, 2, 185))
        screen.blit(darkness, (0, 0))

        panel_rect = pygame.Rect(250, 210, 500, 250)

        self.draw_beveled_panel(
            screen,
            panel_rect,
            fill=(31, 24, 20),
            edge=(154, 105, 52),
        )

        title = self.fantasy_heading.render(
            "ADVANCE TO THE NEXT WEEK?",
            True,
            (246, 216, 158),
        )
        screen.blit(title, title.get_rect(center=(500, 260)))

        current_moon = getattr(self.world, "moon", 0)

        message = self.fantasy_body.render(
            f"Moon {current_moon} will end and the tribe simulation will advance.",
            True,
            (220, 207, 183),
        )
        screen.blit(message, message.get_rect(center=(500, 310)))

        warning = self.fantasy_body.render(
            "Events, food consumption, relationships, and injuries may change.",
            True,
            (174, 158, 135),
        )
        screen.blit(warning, warning.get_rect(center=(500, 340)))

        confirm_btn = FantasyButton(
            (315, 385, 175, 46),
            "ADVANCE",
            self.confirm_advance_week,
        )

        cancel_btn = FantasyButton(
            (510, 385, 175, 46),
            "CANCEL",
            self.cancel_advance_week,
        )

        # Remove every map button while the confirmation is open.
        self.buttons.clear()

        for button in (confirm_btn, cancel_btn):
            self.buttons.append(button)
            button.draw(screen, self.fantasy_body, mouse_pos)

    def update(self, dt):
        pass

    def get_dragons_at_location(self, loc_id):
        dragons = getattr(self.world, "dragons", self.world)

        aliases = {
            "village": ["village", "village_center", "Village Center"],
            "relations": ["relations", "queen_palace", "Queen's Palace"],
            "healer_den": ["healer_den", "Healer's Den"],
            "training": ["training", "training_grounds", "Training Grounds"],
            "hunting": ["hunting", "hunting_grounds", "Hunting Grounds"],
            "border": ["border", "border_routes", "Border Routes"],
            "library": ["library", "scroll_library", "Scroll Library"],
            "hatchery": ["hatchery", "Hatchery"],
        }

        valid_names = aliases.get(loc_id, [loc_id])

        return [
            d for d in dragons
            if getattr(d, "location", None) in valid_names
        ]


    def get_location_label(self, name, loc_id):
        count = len(self.get_dragons_at_location(loc_id))
        return f"{name} ({count})"


    def get_location_dragons_text(self, loc_id):
        dragons = self.get_dragons_at_location(loc_id)

        if not dragons:
            return "No dragons here."

        shown = dragons[:3]
        names = [f"{d.name} ({d.role})" for d in shown]

        if len(dragons) > 3:
            names.append(f"+{len(dragons) - 3} more")

        return " • ".join(names)

    def get_fitted_font(self, text, max_width, start_size, minimum_size=10, bold=False):
        text = str(text)
        for size in range(start_size, minimum_size - 1, -1):
            key = (size, bold)
            font = self._fitted_font_cache.get(key)
            if font is None:
                font = pygame.font.SysFont("georgia", size, bold=bold)
                self._fitted_font_cache[key] = font
            if font.size(text)[0] <= max_width:
                return font
        return self._fitted_font_cache[(minimum_size, bold)]

    def truncate_to_width(self, text, font, max_width):
        """Shorten a single-line label without allowing it past its panel."""
        text = str(text)
        if font.size(text)[0] <= max_width:
            return text

        suffix = "…"
        shortened = text
        while shortened and font.size(shortened.rstrip() + suffix)[0] > max_width:
            shortened = shortened[:-1]
        return shortened.rstrip() + suffix

    def draw_beveled_panel(self, screen, rect, fill=PANEL_DARK, edge=BRONZE, cut=12):
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

        pygame.draw.polygon(screen, (10, 7, 5), [(px, py + 5) for px, py in points])
        pygame.draw.polygon(screen, edge, points)

        inner = pygame.Rect(rect).inflate(-6, -6)
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
        pygame.draw.lines(screen, (211, 165, 92), False, inner_points[:3], 1)

    def draw_location_marker(self, screen, location, mouse_pos):
        name = location["name"]
        loc_id = location["id"]
        icon = location["icon"]
        anchor_x, anchor_y = location["anchor"]
        side = location["side"]

        count = len(self.get_dragons_at_location(loc_id))
        label_text = f"{name.upper()}  •  {count}"
        label_image = self.marker_font.render(label_text, True, (238, 220, 184))
        plaque_w = max(150, label_image.get_width() + 30)
        plaque_h = 34

        if side == "right":
            plaque = pygame.Rect(anchor_x + 15, anchor_y - plaque_h // 2, plaque_w, plaque_h)
        else:
            plaque = pygame.Rect(anchor_x - plaque_w - 15, anchor_y - plaque_h // 2, plaque_w, plaque_h)

        icon_rect = pygame.Rect(anchor_x - 23, anchor_y - 23, 46, 46)
        hit_rect = plaque.union(icon_rect)
        hovered = hit_rect.collidepoint(mouse_pos)
        needs_attention = self.get_pending_choice_location() == loc_id
        notice_count = self.get_location_notice_count(loc_id)

        if hovered:
            glow = pygame.Surface((hit_rect.width + 28, hit_rect.height + 28), pygame.SRCALPHA)
            pygame.draw.rect(glow, (242, 201, 76, 42), glow.get_rect(), border_radius=18)
            screen.blit(glow, glow.get_rect(center=hit_rect.center))

        shadow = plaque.move(0, 4)
        pygame.draw.rect(screen, (9, 6, 5), shadow, border_radius=7)
        plaque_edge = (225, 91, 48) if needs_attention else (121, 86, 52)
        pygame.draw.rect(screen, GOLD if hovered else plaque_edge, plaque, border_radius=7)
        inner = plaque.inflate(-5, -5)
        pygame.draw.rect(
            screen,
            (79, 50, 27) if hovered else (41, 32, 27),
            inner,
            border_radius=5,
        )

        screen.blit(label_image, label_image.get_rect(center=plaque.center))

        pygame.draw.circle(screen, (9, 6, 5), (anchor_x, anchor_y + 4), 25)
        pygame.draw.circle(screen, GOLD if hovered else (132, 92, 51), (anchor_x, anchor_y), 24)
        pygame.draw.circle(screen, (44, 33, 27), (anchor_x, anchor_y), 19)
        pygame.draw.circle(screen, (111, 64, 28) if hovered else (76, 48, 31), (anchor_x, anchor_y), 15)

        icon_image = self.marker_icon_font.render(icon, True, (250, 226, 177))
        screen.blit(icon_image, icon_image.get_rect(center=(anchor_x, anchor_y)))

        if needs_attention:
            # A gentle pulse keeps the indicator visible without obscuring the map.
            pulse = (math.sin(pygame.time.get_ticks() / 220.0) + 1.0) / 2.0
            badge_x = anchor_x - 14 if notice_count else anchor_x
            badge_y = anchor_y - 38
            glow_radius = 15 + int(pulse * 4)

            glow = pygame.Surface((50, 50), pygame.SRCALPHA)
            pygame.draw.circle(glow, (242, 201, 76, 45), (25, 25), glow_radius)
            screen.blit(glow, glow.get_rect(center=(badge_x, badge_y)))

            pygame.draw.circle(screen, (48, 25, 15), (badge_x, badge_y), 13)
            pygame.draw.circle(screen, GOLD, (badge_x, badge_y), 13, 3)
            pygame.draw.circle(screen, (177, 48, 34), (badge_x, badge_y), 9)

            alert_image = self.fantasy_heading.render("!", True, (255, 235, 184))
            screen.blit(alert_image, alert_image.get_rect(center=(badge_x, badge_y - 1)))

        if notice_count:
            # Gold numbers are informational.  They remain until the player
            # enters this location, while red decisions remain until resolved.
            badge_x = anchor_x + 14 if needs_attention else anchor_x
            badge_y = anchor_y - 38
            count_text = "99+" if notice_count > 99 else str(notice_count)
            radius = 14 if notice_count > 9 else 13

            glow = pygame.Surface((44, 44), pygame.SRCALPHA)
            pygame.draw.circle(glow, (242, 201, 76, 42), (22, 22), radius + 5)
            screen.blit(glow, glow.get_rect(center=(badge_x, badge_y)))

            pygame.draw.circle(screen, (50, 34, 18), (badge_x, badge_y), radius)
            pygame.draw.circle(screen, GOLD, (badge_x, badge_y), radius, 3)
            pygame.draw.circle(screen, (150, 101, 32), (badge_x, badge_y), radius - 5)

            count_image = self.notice_font.render(count_text, True, (255, 239, 197))
            screen.blit(count_image, count_image.get_rect(center=(badge_x, badge_y)))

        target = ClickTarget(hit_rect, lambda lid=loc_id: self.open_location(lid))
        self.buttons.append(target)

        return hovered

    def draw_location_tooltip(self, screen, location, mouse_pos):
        """Draw location details beside the hovered marker."""

        card_w = 350
        needs_attention = self.get_pending_choice_location() == location["id"]
        notice_count = self.get_location_notice_count(location["id"])
        card_h = 96
        if needs_attention:
            card_h += 24
        if notice_count:
            card_h += 24
        gap = 18

        # Initially place the tooltip below and right of the cursor.
        x = mouse_pos[0] + gap
        y = mouse_pos[1] + gap

        # Move it left if it would leave the right side of the screen.
        if x + card_w > WIDTH - 20:
            x = mouse_pos[0] - card_w - gap

        # Move it above if it would leave the bottom of the screen.
        if y + card_h > HEIGHT - 20:
            y = mouse_pos[1] - card_h - gap

        # Keep it inside the screen and beneath the header.
        x = max(20, min(x, WIDTH - card_w - 20))
        y = max(95, min(y, HEIGHT - card_h - 20))

        self.draw_beveled_panel(
            screen,
            (x, y, card_w, card_h),
            fill=(31, 27, 23),
            edge=(127, 91, 55),
        )

        count = len(self.get_dragons_at_location(location["id"]))

        dragon_word = "DRAGON" if count == 1 else "DRAGONS"
        heading_text = f"{location['name'].upper()}  •  {count} {dragon_word}"
        heading_font = self.get_fitted_font(
            heading_text,
            card_w - 36,
            start_size=18,
            minimum_size=13,
            bold=True,
        )
        heading = heading_font.render(
            heading_text,
            True,
            (246, 216, 158),
        )
        screen.blit(heading, (x + 18, y + 14))

        description = self.fantasy_body.render(
            location["desc"],
            True,
            (220, 207, 183),
        )
        screen.blit(description, (x + 18, y + 43))

        residents_text = self.truncate_to_width(
            self.get_location_dragons_text(location["id"]),
            self.small,
            card_w - 36,
        )
        residents = self.small.render(
            residents_text,
            True,
            (168, 155, 134),
        )
        screen.blit(residents, (x + 18, y + 68))

        message_y = y + 91

        if needs_attention:
            attention = self.small.render(
                "! A decision requires your attention.",
                True,
                (242, 201, 76),
            )
            screen.blit(attention, (x + 18, message_y))
            message_y += 24

        if notice_count:
            noun = "update" if notice_count == 1 else "updates"
            update = self.small.render(
                f"{notice_count} new {noun} recorded here.",
                True,
                (230, 185, 91),
            )
            screen.blit(update, (x + 18, message_y))

    def draw(self, screen):
        mouse_pos = scale_mouse_pos(
            pygame.mouse.get_pos(),
            pygame.display.get_surface().get_size()
        )
        self.buttons.clear()

        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill(BG)

        # Keep the illustrated settlement visible. A light vignette improves
        # text contrast without turning the scene back into a dark menu.
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 9, 6, 52))
        screen.blit(overlay, (0, 0))

        pygame.draw.rect(
            screen,
            (108, 76, 47),
            (18, 16, 964, 668),
            width=3,
            border_radius=18,
        )
        pygame.draw.rect(
            screen,
            (35, 27, 22),
            (25, 23, 950, 654),
            width=2,
            border_radius=15,
        )

        self.draw_beveled_panel(
            screen,
            (300, 18, 400, 67),
            fill=(31, 24, 20),
            edge=(136, 95, 52),
        )
        title = self.fantasy_title.render("TRIBE LOCATIONS", True, (246, 216, 158))
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 43)))

        living = [
            dragon
            for dragon in getattr(self.world, "dragons", [])
            if getattr(dragon, "status", "Alive") == "Alive"
        ]

        moon = getattr(self.world, "moon", 0)
        food = getattr(self.world, "food_stores", 0)
        tension = getattr(self.world, "tension", 0.0)

        status_text = (
            f"MOON {moon}  •  "
            f"{len(living)} LIVING  •  "
            f"FOOD {food}  •  "
            f"TENSION {tension:.1f}"
        )

        subtitle = self.small.render(
            status_text,
            True,
            (184, 166, 135),
        )
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 68)))

        if self.get_pending_choice_location():
            advance_btn = FantasyButton(
                (28, 28, 175, 39),
                "DECISION PENDING",
                self.open_pending_choice,
            )
        else:
            advance_btn = FantasyButton(
                (28, 28, 175, 39),
                "ADVANCE WEEK",
                self.request_advance_week,
            )

        dashboard_btn = FantasyButton(
            (744, 28, 112, 39),
            "OVERVIEW",
            lambda: self.open_location("dashboard")
        )
        profile_btn = FantasyButton(
            (864, 28, 112, 39),
            "DRAGONS",
            lambda: self.open_location("dragon_profile")
        )

        for button in (advance_btn, dashboard_btn, profile_btn):
            self.buttons.append(button)
            button.draw(screen, self.small, mouse_pos)

        hovered_location = None
        for location in self.locations:
            if self.draw_location_marker(screen, location, mouse_pos):
                hovered_location = location

        # Show details only while hovering over a location.
        if hovered_location:
            self.draw_location_tooltip(
                screen,
                hovered_location,
                mouse_pos,
            )

        if self.show_advance_confirmation:
            self.draw_advance_confirmation(screen, mouse_pos)
        elif self.notice_popup_location:
            self.draw_notice_popup(screen, mouse_pos)

    def open_location(self, loc_id):
        if self.get_location_notice_count(loc_id):
            self.notice_popup_location = loc_id
            return

        self.change_to_location(loc_id)

    def change_to_location(self, loc_id):

        if loc_id == "healer_den":
            self.change_screen("healer_den")
        elif loc_id == "relations":
            self.change_screen("relations")
        elif loc_id == "village":
            self.change_screen("village")
        elif loc_id == "library":
            self.change_screen("scroll_library")
        elif loc_id == "dashboard":
            self.change_screen("dashboard")
        elif loc_id == "dragon_profile":
            self.change_screen("dragon_profile")
        elif loc_id == "training":
            self.change_screen("training_grounds")
        elif loc_id == "hunting":
            self.change_screen("hunting_grounds")
        elif loc_id == "border":
            self.change_screen("border_routes")
        elif loc_id == "hatchery":
            self.change_screen("hatchery")
        else:
            print(f"{loc_id} not built yet.")

    def handle_event(self, event):

        if self.notice_popup_location and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.dismiss_notice_popup()
                return

            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.enter_notice_location()
                return

        if self.show_advance_confirmation and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.cancel_advance_week()
                return

            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.confirm_advance_week()
                return

        if event.type == pygame.MOUSEBUTTONDOWN:
            scaled_pos = scale_mouse_pos(
                event.pos,
                pygame.display.get_surface().get_size()
            )

            scaled_event = pygame.event.Event(
                event.type,
                {
                    "pos": scaled_pos,
                    "button": event.button
                }
            )

            for button in self.buttons:
                button.handle_event(scaled_event)
        else:
            for button in self.buttons:
                button.handle_event(event)

def scale_mouse_pos(pos, window_size):
    mouse_x, mouse_y = pos
    window_w, window_h = window_size

    scale_x = WIDTH / window_w
    scale_y = HEIGHT / window_h

    return int(mouse_x * scale_x), int(mouse_y * scale_y)
