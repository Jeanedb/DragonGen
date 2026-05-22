import pygame
from pathlib import Path

from ui_pygame.core.base_screen import BaseScreen
from ui_pygame.widgets.button import Button

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

BG = (18, 18, 18)
TEXT = (230, 230, 230)
MUTED = (180, 180, 180)
PANEL = (28, 28, 28)
CARD = (42, 42, 42)
GOLD = (242, 201, 76)
GREEN = (111, 207, 151)
RED = (235, 87, 87)


class QueenPalaceScreen(BaseScreen):
    def __init__(self, world, change_screen):
        super().__init__()
        self.world = world
        self.change_screen = change_screen
        self.selected_tribe = None
        self.hovered_tribe = None
        self.detail_scroll = 0

        PROJECT_ROOT = Path(__file__).resolve().parents[2]
        bg_path = PROJECT_ROOT / "assets" / "menu" / "queen_palace_bg.png"

        try:
            self.bg_image = pygame.image.load(str(bg_path)).convert()
            self.bg_image = pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT))
        except Exception as e:
            print(f"Could not load queen palace background: {e}")
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

    def get_selected_summary_text(self):
        tribe = self.selected_tribe

        if not tribe:
            return "No tribe selected."

        score = self.get_score(tribe)
        status = get_relation_status(score)
        queen = getattr(self.world, "tribal_leaders", {}).get(tribe, "Unknown")
        trait = getattr(self.world, "tribal_traits", {}).get(tribe, "neutral")

        return (
            f"Tribe: {tribe}\n"
            f"Status: {status}\n"
            f"Score: {score}\n"
            f"Queen: {queen}\n"
            f"Queen Traits: {trait}"
        )

    def apply_policy(self, action_id):
        if not self.selected_tribe:
            return

        if hasattr(self.world, "pending_choice"):
            self.world.pending_choice = {
                "type": "tribal_policy_choice",
                "tribe": self.selected_tribe
            }

        try:
            from core.sim.choices import resolve_choice
            resolve_choice(self.world, action_id)
        except Exception as e:
            print(f"Could not apply policy: {e}")

    def get_tribes(self):
        if hasattr(self.world, "tribal_relations"):
            return sorted(self.world.tribal_relations.keys())

        return ["SkyWing", "SeaWing", "RainWing", "SandWing", "IceWing", "NightWing"]

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

        if status == "War":
            return "Relations are effectively at war. Hostile incidents and violent encounters are highly likely."
        if status == "Hostile":
            return "Relations are openly hostile. Border incidents, suspicion, and conflict are more likely."
        if status == "Uneasy":
            return "Relations are strained and uncertain. Trust is limited, and tensions could worsen."
        if status == "Neutral":
            return "Relations are neutral. Neither openly friendly nor openly hostile."
        if status == "Friendly":
            return "Relations are positive. Cooperation and peaceful contact are more likely."
        if status == "Allied":
            return "Relations are very strong. Mutual trust and support would be expected."

        return "No description available."

    def get_selected_detail_text(self):
        tribe = self.selected_tribe

        if not tribe:
            return "No tribe selected."

        score = self.get_score(tribe)
        status = get_relation_status(score)
        queen = getattr(self.world, "tribal_leaders", {}).get(tribe, "Unknown")
        trait = getattr(self.world, "tribal_traits", {}).get(tribe, "neutral")

        profile = TRIBE_PROFILES.get(tribe, {})
        blurb = profile.get("blurb", "No historical data available.")

        incidents = getattr(self.world, "tribal_incidents", {}).get(tribe, [])
        incident_text = "\n".join(f"- {i}" for i in incidents) if incidents else "None yet."

        return (
            f"Description:\n{self.get_relation_description(score)}\n\n"
            f"Tribal Overview:\n{blurb}\n\n"
            f"Recent Incidents:\n{incident_text}"
        )

    def update(self, dt):
        pass

    def draw_transparent_rect(self, screen, rect, color, border=(65, 65, 65), radius=14):
        surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        surface.fill(color)
        screen.blit(surface, rect.topleft)
        pygame.draw.rect(screen, border, rect, width=1, border_radius=radius)

    def draw(self, screen):
        self.buttons.clear()

        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill(BG)

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 130))
        screen.blit(overlay, (0, 0))

        title = self.title_font.render("Queen's Palace", True, TEXT)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 75)))

        subtitle = self.small.render(
            "Review tribal relations, outside threats, and diplomatic posture.",
            True,
            MUTED
        )
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 115)))

        main_panel = pygame.Rect(90, 145, 820, 485)
        self.draw_transparent_rect(screen, main_panel, (28, 28, 28, 175), (45, 45, 45), 22)

        left_panel = pygame.Rect(120, 180, 300, 390)
        right_panel = pygame.Rect(445, 180, 435, 390)

        self.draw_transparent_rect(screen, left_panel, (32, 32, 32, 210))
        self.draw_transparent_rect(screen, right_panel, (32, 32, 32, 210))

        self.draw_text(screen, "Tribes", 145, 200, self.section_font, GOLD)
        self.draw_text(screen, "Relation Details", 470, 200, self.section_font, GOLD)

        mouse_pos = scale_mouse_pos(
            pygame.mouse.get_pos(),
            pygame.display.get_surface().get_size()
        )

        y = 240
        for tribe in self.get_tribes():
            score = self.get_score(tribe)
            status = get_relation_status(score)
            trend = self.get_trend(tribe)

            row = pygame.Rect(140, y, 255, 44)
            hovered = row.collidepoint(mouse_pos)
            selected = tribe == self.selected_tribe

            if selected:
                color = (70, 60, 35, 235)
                border = GOLD
            elif hovered:
                color = (55, 55, 55, 230)
                border = (120, 120, 120)
            else:
                color = (42, 42, 42, 205)
                border = (65, 65, 65)

            self.draw_transparent_rect(screen, row, color, border, 8)

            label = f"{tribe} — {status} ({score})"
            self.draw_text(screen, label, row.x + 10, row.y + 6, self.small, TEXT)
            symbol = "▲" if trend == "Improving" else "▼" if trend == "Worsening" else "■"
            trend_color = GREEN if trend == "Improving" else RED if trend == "Worsening" else MUTED

            self.draw_text(screen, f"{symbol} {trend}", row.x + 10, row.y + 24, self.small, trend_color)

            btn = Button(
                (row.x, row.y, row.width, row.height),
                "",
                lambda t=tribe: self.select_tribe(t)
            )
            self.buttons.append(btn)

            y += 52

        summary_rect = pygame.Rect(470, 240, 380, 100)
        self.draw_transparent_rect(screen, summary_rect, (42, 42, 42, 205), (65, 65, 65), 10)

        tribe = self.selected_tribe
        score = self.get_score(tribe)
        status = get_relation_status(score)
        queen = getattr(self.world, "tribal_leaders", {}).get(tribe, "Unknown")
        trait = getattr(self.world, "tribal_traits", {}).get(tribe, "neutral")

        left_x = summary_rect.x + 14
        right_x = summary_rect.x + 200
        top_y = summary_rect.y + 12

        self.draw_text(screen, f"Tribe: {tribe}", left_x, top_y, self.small, TEXT)
        self.draw_text(screen, f"Status: {status}", left_x, top_y + 28, self.small, self.get_status_color(status))
        self.draw_text(screen, f"Score: {score}", left_x, top_y + 56, self.small, TEXT)

        self.draw_text(screen, f"Queen: {queen}", right_x, top_y, self.small, TEXT)
        self.draw_text(screen, f"Traits: {trait}", right_x, top_y + 28, self.small, TEXT)

        detail_title_rect = pygame.Rect(470, 338, 380, 30)
        detail_rect = pygame.Rect(470, 365, 380, 180)

        self.draw_transparent_rect(screen, detail_rect, (42, 42, 42, 205), (65, 65, 65), 10)

        self.draw_text(
            screen,
            "Diplomatic Briefing",
            detail_title_rect.x + 5,
            detail_title_rect.y + 8,
            self.small,
            GOLD
        )

        screen.set_clip(detail_rect)

        self.draw_wrapped_text(
            screen,
            self.get_selected_detail_text(),
            detail_rect.x + 14,
            detail_rect.y + 8 + self.detail_scroll,
            detail_rect.width - 28,
            self.small,
            TEXT
        )

        screen.set_clip(None)

        return_btn = Button(
            (430, 625, 140, 38),
            "Return",
            lambda: self.change_screen("locations")
        )
        self.buttons.append(return_btn)

        actions = [
            ("Peace Gesture", "peace_gesture"),
            ("Border Patrol", "border_patrol"),
            ("Apply Pressure", "border_pressure"),
            ("Offer Aid", "offer_aid"),
        ]

        action_bar = pygame.Rect(470, 545, 380, 60)
        self.draw_transparent_rect(screen, action_bar, (32, 32, 32, 190), (65, 65, 65), 12)

        x = action_bar.x + 10
        y = action_bar.y + 11

        for label, action_id in actions:
            btn = Button(
                (x, y, 88, 38),
                label,
                lambda aid=action_id: self.apply_policy(aid)
            )
            self.buttons.append(btn)
            btn.draw(screen, self.small)
            x += 92

        return_btn.draw(screen, self.font)

    def select_tribe(self, tribe):
        self.selected_tribe = tribe
        self.detail_scroll = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            mouse_x, mouse_y = scale_mouse_pos(
                pygame.mouse.get_pos(),
                pygame.display.get_surface().get_size()
            )

            detail_title_rect = pygame.Rect(470, 365, 380, 30)
            detail_rect = pygame.Rect(470, 365, 380, 180)

            if detail_rect.collidepoint(mouse_x, mouse_y):
                self.detail_scroll += event.y * 30

                max_scroll = 0
                min_scroll = -300

                self.detail_scroll = max(min_scroll, min(max_scroll, self.detail_scroll))


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