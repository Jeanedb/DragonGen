import pygame
from ui_pygame.widgets.button import Button
from ui_pygame.core.base_screen import BaseScreen
from pathlib import Path

WIDTH, HEIGHT = 1000, 700

BG = (18, 18, 18)
TEXT = (230, 230, 230)
MUTED = (180, 180, 180)
PANEL = (28, 28, 28)
CARD = (42, 42, 42)
GOLD = (242, 201, 76)


class LocationsScreen(BaseScreen):
    def __init__(self, world, change_screen):
        super().__init__()
        self.hovered_card = None
             
        PROJECT_ROOT = Path(__file__).resolve().parents[2]
        bg_path = PROJECT_ROOT / "assets" / "menu" / "main_locations_bg.png"

        try:
            self.bg_image = pygame.image.load(str(bg_path)).convert()
            self.bg_image = pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT))
        except Exception as e:
            print(f"Could not load locations background: {e}")
            self.bg_image = None
        
        self.world = world
        self.change_screen = change_screen


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

    def draw(self, screen):
        mouse_pos = scale_mouse_pos(
            pygame.mouse.get_pos(),
            pygame.display.get_surface().get_size()
        )
        self.hovered_card = None

        self.buttons.clear()
        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill(BG)

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))

        title = self.title_font.render("Tribe Locations", True, TEXT)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 80)))

        subtitle = self.small.render(
            "Choose where to focus your attention this week.",
            True,
            MUTED
        )
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 120)))

        dashboard_btn = Button(
            (755, 50, 150, 36),
            "Tribe Overview",
            lambda: self.open_location("dashboard")
        )
        self.buttons.append(dashboard_btn)
        dashboard_btn.draw(screen, self.small)

        profile_btn = Button(
            (755, 92, 150, 36),
            "Dragon Profile",
            lambda: self.open_location("dragon_profile")
        )
        self.buttons.append(profile_btn)
        profile_btn.draw(screen, self.small)

        panel = pygame.Rect(130, 135, 740, 550)
        panel_surface = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
        panel_surface.fill((28, 28, 28, 175))
        screen.blit(panel_surface, panel.topleft)
        pygame.draw.rect(screen, (45, 45, 45), panel, width=2, border_radius=22)

        locations = [
            ("Village Center", "Conversations and social interactions.", "village"),
            ("Queen's Palace", "Diplomacy and tribal relations.", "relations"),
            ("Healer's Den", "Healing, injuries, and recovery.", "healer_den"),
            ("Training Grounds", "Training, sparring, and warriors.", "training"),
            ("Hunting Grounds", "Food, hunting, and survival.", "hunting"),
            ("Border Routes", "Patrols, threats, and outside conflict.", "border"),
            ("Scroll Library", "History, knowledge, and records.", "library"),
            ("Hatchery", "Dragonets, family, and future generations.", "hatchery"),
        ]

        card_w = 320
        card_h = 105
        start_x = 170
        start_y = 170
        gap_x = 40
        gap_y = 20

        for idx, (name, desc, loc_id) in enumerate(locations):
            col = idx % 2
            row = idx // 2

            x = start_x + col * (card_w + gap_x)
            y = start_y + row * (card_h + gap_y)

            card = pygame.Rect(x, y, card_w, card_h)
            if card.collidepoint(mouse_pos):
                self.hovered_card = idx

            is_hovered = self.hovered_card == idx

            hover_offset = -4 if is_hovered else 0
            draw_rect = card.move(0, hover_offset)

            card_surface = pygame.Surface((draw_rect.width, draw_rect.height), pygame.SRCALPHA)
            

            if is_hovered:
                card_surface.fill((60, 60, 60, 235))
            else:
                card_surface.fill((42, 42, 42, 210))

            screen.blit(card_surface, draw_rect.topleft)

            border_color = (120, 120, 120) if is_hovered else (65, 65, 65)

            pygame.draw.rect(
                screen,
                border_color,
                draw_rect,
                width=2 if is_hovered else 1,
                border_radius=12
            )

            self.draw_text(
                screen,
                self.get_location_label(name, loc_id),
                draw_rect.x + 14,
                draw_rect.y + 10,
                self.section_font,
                GOLD
            )

            self.draw_text(screen, desc, draw_rect.x + 14, draw_rect.y + 42, self.small, MUTED)


            btn = Button(
                (draw_rect.x + 210, draw_rect.y + 62, 90, 28),
                "Enter",
                lambda lid=loc_id: self.open_location(lid)
            )
            self.buttons.append(btn)
            btn.draw(screen, self.small)

    def open_location(self, loc_id):
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