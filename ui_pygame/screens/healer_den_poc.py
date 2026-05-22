import pygame
from dataclasses import dataclass
import sys
from pathlib import Path
from ui_pygame.core.base_screen import BaseScreen

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from ui_pygame.widgets.button import Button


WIDTH, HEIGHT = 1000, 700
FPS = 60

BG = (18, 18, 18)
PANEL = (28, 28, 28)
CARD = (42, 42, 42)
TEXT = (230, 230, 230)
MUTED = (180, 180, 180)
GREEN = (111, 207, 151)
RED = (235, 87, 87)
GOLD = (242, 201, 76)
BLUE = (70, 130, 200)


@dataclass
class Dragon:
    id: int
    name: str
    tribe: str
    role: str
    health: str = "Healthy"
    status: str = "Alive"
    injury_duration: int = 0
    location: str = "Healer's Den"
    healer_skill: float = 1.0
    assigned_healer_id: int | None = None
    resentment: dict = None
    perceived_reputation: dict = None
    trust: dict = None

    rivals: set = None
    friends: set = None
    mates: set = None

    personality: str = "neutral"
    mood: str = "neutral"

    age: int = 25
    memory_flags: set = None

    def __post_init__(self):

        if self.resentment is None:
            self.resentment = {}

        if self.perceived_reputation is None:
            self.perceived_reputation = {}

        if self.trust is None:
            self.trust = {}

        if self.rivals is None:
            self.rivals = set()

        if self.friends is None:
            self.friends = set()

        if self.mates is None:
            self.mates = set()
        
        if self.memory_flags is None:
            self.memory_flags = set()


class HealerDenScreen(BaseScreen):
    def __init__(self, world, change_screen=None):
        super().__init__()
        self.world = world
        self.change_screen = change_screen
        self.popup_dragon = None
        self.scroll_left = 0
        self.scroll_right = 0


        bg_path = PROJECT_ROOT / "assets" / "menu" / "healer_bg.png"

        try:
            self.bg_image = pygame.image.load(str(bg_path)).convert()
            self.bg_image = pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT))
        except Exception as e:
            print(f"Could not load healer background: {e}")
            self.bg_image = None

    def update(self, dt):
        pass


    def clamp_scrolls(self):
        injured_count = len(self.get_injured_dragons())
        healer_count = len(self.get_healers())

        visible_height = 280
        injured_content_height = 60 + injured_count * 230
        healer_content_height = 60 + healer_count * 165

        max_left_scroll = 0
        min_left_scroll = min(0, visible_height - injured_content_height)

        max_right_scroll = 0
        min_right_scroll = min(0, visible_height - healer_content_height)

        self.scroll_left = max(min_left_scroll, min(max_left_scroll, self.scroll_left))
        self.scroll_right = max(min_right_scroll, min(max_right_scroll, self.scroll_right))

    def get_injured_dragons(self):
        return [
            d for d in self.world
            if d.status == "Alive" and d.health != "Healthy"
        ]

    def get_healers(self):
        return [
            d for d in self.world
            if d.status == "Alive" and d.role == "Healer"
        ]

    def get_dragon_by_id(self, dragon_id):
        return next((d for d in self.world if d.id == dragon_id), None)

    def get_patient_count(self, healer):
        return sum(1 for d in self.world if d.assigned_healer_id == healer.id)

    def assign_healer(self, injured_dragon, healer):
        injured_dragon.assigned_healer_id = healer.id
        self.popup_dragon = None


    def draw_card(self, screen, rect, title, body, body_color=TEXT, button=None):
        pygame.draw.rect(screen, CARD, rect, border_radius=10)

        y = rect.y + 10
        self.draw_text(screen, title, rect.x + 12, y, self.font, TEXT)
        y += 32
        self.draw_text(screen, body, rect.x + 12, y, self.small, body_color)

        if button:
            button.draw(screen, self.small)

    def draw(self, screen):
        self.buttons.clear()
        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill(BG)

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))

        # Main content panel
        content = pygame.Rect(130, 70, 740, 560)
        content_surface = pygame.Surface((content.width, content.height), pygame.SRCALPHA)
        content_surface.fill((28, 28, 28, 180))
        screen.blit(content_surface, content.topleft)
        pygame.draw.rect(screen, (40, 40, 40), content, width=2, border_radius=24)

        title = self.title_font.render("Healer's Den", True, TEXT)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 90)))

        subtitle = self.small.render(
            "Review injured dragons and the healers available to care for them.",
            True,
            MUTED
        )
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 125)))

        left_panel = pygame.Rect(155, 220, 320, 330)
        right_panel = pygame.Rect(525, 220, 320, 330)

        pygame.draw.rect(screen, (32, 32, 32), left_panel, border_radius=14)
        pygame.draw.rect(screen, (32, 32, 32), right_panel, border_radius=14)

        self.draw_text(screen, "Injured Dragons", 175, 235, self.section_font, GOLD)
        self.draw_text(screen, "Available Healers", 545, 235, self.section_font, GREEN)

        # Injured dragon cards
        left_scroll_area = pygame.Rect(155, 270, 320, 280)
        screen.set_clip(left_scroll_area)
        y = 285 + self.scroll_left
        injured = self.get_injured_dragons()

        if not injured:
            self.draw_text(screen, "No dragons are currently injured.", 125, y, self.small, MUTED)
        else:
            for dragon in injured:
                assigned = self.get_dragon_by_id(dragon.assigned_healer_id)
                assigned_text = assigned.name if assigned else "None"

                body = (
                    f"Tribe: {dragon.tribe}\n"
                    f"Role: {dragon.role}\n"
                    f"Health: {dragon.health}\n"
                    f"Injured For: {dragon.injury_duration} moons\n"
                    f"Assigned Healer: {assigned_text}\n"
                    f"Location: {dragon.location}"
                )

                card_rect = pygame.Rect(175, y, 280, 215)

                has_healer = dragon.assigned_healer_id is not None
                btn_text = "Healer Assigned" if has_healer else "Assign Healer"
                btn = Button(
                    (190, y + 175, 250, 30),
                    btn_text,
                    lambda d=dragon: self.open_popup(d),
                    enabled=not has_healer
                )
                self.buttons.append(btn)

                self.draw_card(
                    screen,
                    card_rect,
                    dragon.name,
                    body,
                    GREEN if assigned else RED,
                    btn
                )
                y += 230        

        screen.set_clip(None)

        # Healer cards
        y = 285 + self.scroll_right
        right_scroll_area = pygame.Rect(525, 270, 320, 280)
        screen.set_clip(right_scroll_area)
        healers = self.get_healers()

        if not healers:
            self.draw_text(screen, "No healers are currently available.", 525, y, self.small, MUTED)
        else:
            for healer in healers:
                count = self.get_patient_count(healer)

                body = (
                    f"Tribe: {healer.tribe}\n"
                    f"Health: {healer.health}\n"
                    f"Healer Skill: {healer.healer_skill}\n"
                    f"Location: {healer.location}\n"
                    f"Patients: {count}/2"
                )

                card_rect = pygame.Rect(545, y, 280, 150)
                self.draw_card(screen, card_rect, healer.name, body, MUTED)
                y += 165

        screen.set_clip(None)

        return_btn = Button(
            (430, 580, 140, 38),
            "Return",
            lambda: self.change_screen("locations") if self.change_screen else pygame.event.post(pygame.event.Event(pygame.QUIT))
        )
        self.buttons.append(return_btn)
        return_btn.draw(screen, self.font)

        if self.popup_dragon:
            self.draw_popup(screen)

        

    def open_popup(self, dragon):
        self.popup_dragon = dragon

    def draw_popup(self, screen):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        popup = pygame.Rect(290, 160, 420, 380)
        pygame.draw.rect(screen, (25, 25, 25), popup, border_radius=16)

        self.draw_text(
            screen,
            f"Assign healer to {self.popup_dragon.name}",
            320,
            190,
            self.section_font,
            TEXT
        )

        y = 245
        healers = [
            h for h in self.get_healers()
            if h.id != self.popup_dragon.id
        ]

        if not healers:
            self.draw_text(screen, "No healers are available.", 320, y, self.font, MUTED)
            return

        for healer in healers:
            count = self.get_patient_count(healer)
            full = count >= 2

            text = f"{healer.name} ({healer.tribe})"
            if full:
                text += " - Full"

            btn = Button(
                (320, y, 360, 38),
                text,
                lambda h=healer: self.assign_healer(self.popup_dragon, h),
                enabled=not full
            )
            self.buttons.append(btn)
            btn.draw(screen, self.font)
            y += 48

        cancel = Button((430, 485, 140, 36), "Cancel", lambda: setattr(self, "popup_dragon", None))
        self.buttons.append(cancel)
        cancel.draw(screen, self.font)



    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            mouse_x, mouse_y = scale_mouse_pos(pygame.mouse.get_pos(), pygame.display.get_surface().get_size())

            if 105 <= mouse_x <= 495 and 210 <= mouse_y <= 575:
                self.scroll_left += event.y * 30

            elif 505 <= mouse_x <= 895 and 210 <= mouse_y <= 575:
                self.scroll_right += event.y * 30

            self.clamp_scrolls()

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


def create_test_world():
    return [
        Dragon(1, "Ashclaw", "SkyWing", "Warrior", health="Broken Wing", injury_duration=2),
        Dragon(2, "Mossglade", "LeafWing", "Hunter", health="Claw Wound", injury_duration=1),
        Dragon(3, "Shellseer", "SeaWing", "Healer", healer_skill=1.4),
        Dragon(4, "Frostmend", "IceWing", "Healer", healer_skill=1.2),
        Dragon(5, "Mudroot", "MudWing", "Healer", healer_skill=0.9),
        Dragon(6, "Nightfall", "NightWing", "Scout"),
    ]


def scale_mouse_pos(pos, window_size):
    mouse_x, mouse_y = pos
    window_w, window_h = window_size

    scale_x = WIDTH / window_w
    scale_y = HEIGHT / window_h

    return int(mouse_x * scale_x), int(mouse_y * scale_y)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    game_surface = pygame.Surface((WIDTH, HEIGHT))
    pygame.display.set_caption("DragonGen - Healer's Den Pygame POC")
    clock = pygame.time.Clock()

    world = create_test_world()
    healer_screen = HealerDenScreen(world)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            healer_screen.handle_event(event)

        healer_screen.update(dt)

        healer_screen.draw(game_surface)

        window_w, window_h = screen.get_size()
        scaled_surface = pygame.transform.smoothscale(game_surface, (window_w, window_h))
        screen.blit(scaled_surface, (0, 0))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()