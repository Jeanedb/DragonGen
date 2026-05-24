import pygame
from pathlib import Path

from ui_pygame.widgets.button import Button
from ui_pygame.app import PygameApp

WIDTH, HEIGHT = 1000, 700
FPS = 60

TEXT = (230, 230, 230)
MUTED = (180, 180, 180)
GOLD = (242, 201, 76)

TRIBES = [
    ("skywing", "SkyWing", "Proud, fierce, and battle-ready."),
    ("seawing", "SeaWing", "Diplomatic, aquatic, and socially complex."),
    ("rainwing", "RainWing", "Colorful, emotional, and unpredictable."),
    ("sandwing", "SandWing", "Harsh, political, and survival-minded."),
    ("icewing", "IceWing", "Formal, hierarchical, and reputation-driven."),
    ("nightwing", "NightWing", "Secretive, clever, and prophecy-haunted."),
    ("mudwing", "MudWing", "Loyal, grounded, and family-focused."),
    ("mixed", "Mixed Tribe", "A varied tribe with unpredictable dynamics."),
]


class PygameMainMenu:
    def __init__(self):
        pygame.init()

        self.loading_timer = 0
        self.loading_duration = 2.0
        self.loading_tribe = None
        self.loading_step = 0

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.surface = pygame.Surface((WIDTH, HEIGHT))
        pygame.display.set_caption("DragonGen")

        self.clock = pygame.time.Clock()
        self.running = True
        self.state = "main"
        self.selected_tribe = None
        self.buttons = []

        self.title_font = pygame.font.SysFont("arial", 60, bold=True)
        self.section_font = pygame.font.SysFont("arial", 28, bold=True)
        self.font = pygame.font.SysFont("arial", 18)
        self.small = pygame.font.SysFont("arial", 15)

        project_root = Path(__file__).resolve().parents[1]
        bg_path = project_root / "assets" / "menu" / "main_menu_bg.png"

        try:
            self.bg_image = pygame.image.load(str(bg_path)).convert()
            self.bg_image = pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT))
        except Exception:
            self.bg_image = None

    def draw_background(self):
        if self.bg_image:
            self.surface.blit(self.bg_image, (0, 0))
        else:
            self.surface.fill((18, 18, 18))

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 105))
        self.surface.blit(overlay, (0, 0))

    def draw_text(self, text, x, y, font, color=TEXT):
        img = font.render(text, True, color)
        self.surface.blit(img, (x, y))

    def draw_panel(self, rect, alpha=180):
        surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        surf.fill((28, 28, 28, alpha))
        self.surface.blit(surf, rect.topleft)
        pygame.draw.rect(self.surface, (65, 65, 65), rect, width=1, border_radius=14)

    def draw_main(self):
        self.buttons.clear()
        self.draw_background()

        self.draw_text("DragonGen", 70, 105, self.title_font, GOLD)

        menu_items = [
            ("New Game", self.show_tribes),
            ("Load Game", self.start_mixed_game),
            ("Options", self.show_options),
            ("Exit", self.quit),
        ]

        y = 330
        for label, callback in menu_items:
            btn = Button((95, y, 260, 44), f"[{label.upper()}]", callback)
            self.buttons.append(btn)
            btn.draw(self.surface, self.section_font)
            y += 65

    def draw_tribe_select(self):
        self.buttons.clear()
        self.draw_background()

        title = self.section_font.render("Choose Your Tribe", True, TEXT)
        self.surface.blit(title, title.get_rect(center=(WIDTH // 2, 60)))

        subtitle = self.small.render(
            "Your choice will shape behavior, bonds, conflict, and survival.",
            True,
            MUTED
        )
        self.surface.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 95)))

        start_x = 125
        start_y = 130
        card_w = 360
        card_h = 105
        gap_x = 30
        gap_y = 18

        for idx, (tribe_id, name, desc) in enumerate(TRIBES):
            col = idx % 2
            row = idx // 2

            x = start_x + col * (card_w + gap_x)
            y = start_y + row * (card_h + gap_y)

            rect = pygame.Rect(x, y, card_w, card_h)
            selected = tribe_id == self.selected_tribe

            self.draw_panel(rect, alpha=220 if selected else 175)

            border = GOLD if selected else (65, 65, 65)
            pygame.draw.rect(self.surface, border, rect, width=2 if selected else 1, border_radius=14)

            self.draw_text(name, x + 16, y + 12, self.font, GOLD)
            self.draw_text(desc, x + 16, y + 42, self.small, MUTED)

            btn = Button(
                (x + 220, y + 66, 120, 28),
                "Selected" if selected else "Select",
                lambda tid=tribe_id: self.select_tribe(tid)
            )
            self.buttons.append(btn)
            btn.draw(self.surface, self.small)

        begin_enabled = self.selected_tribe is not None

        begin = Button(
            (360, 640, 140, 38),
            "Begin Tribe",
            self.begin_selected_game,
            enabled=begin_enabled
        )
        back = Button((520, 640, 110, 38), "Back", self.show_main)

        self.buttons.append(begin)
        self.buttons.append(back)
        begin.draw(self.surface, self.font)
        back.draw(self.surface, self.font)

    def draw_options(self):
        self.buttons.clear()
        self.draw_background()

        self.draw_text("Options", 420, 170, self.section_font, TEXT)
        self.draw_text("Options will go here later.", 385, 230, self.font, MUTED)

        back = Button((430, 310, 140, 38), "Back", self.show_main)
        self.buttons.append(back)
        back.draw(self.surface, self.font)

    def show_main(self):
        self.state = "main"

    def show_tribes(self):
        self.state = "tribes"

    def show_options(self):
        self.state = "options"

    def select_tribe(self, tribe_id):
        self.selected_tribe = tribe_id

    def begin_selected_game(self):
        if not self.selected_tribe:
            return
        self.launch_game(self.selected_tribe)

    def start_mixed_game(self):
        self.launch_game("mixed")

    def launch_game(self, tribe_id):
        self.loading_tribe = tribe_id
        self.loading_timer = 0
        self.loading_step = 0
        self.state = "loading"

    def draw_loading(self, dt):
        self.buttons.clear()
        self.draw_background()

        self.loading_timer += dt

        selected_name = next(
            (name for tid, name, _ in TRIBES if tid == self.loading_tribe),
            "Tribe"
        )

        steps = [
            "Gathering dragons...",
            "Assigning roles...",
            "Establishing hierarchy...",
            "Finalizing tribe..."
        ]

        progress = min(1.0, self.loading_timer / self.loading_duration)
        step_index = min(int(progress * len(steps)), len(steps) - 1)

        title = self.section_font.render(f"Preparing the {selected_name}...", True, TEXT)
        self.surface.blit(title, title.get_rect(center=(WIDTH // 2, 250)))

        subtitle = self.font.render(steps[step_index], True, MUTED)
        self.surface.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 300)))

        bar = pygame.Rect(320, 350, 360, 18)
        pygame.draw.rect(self.surface, (45, 45, 45), bar, border_radius=8)

        fill = pygame.Rect(bar.x, bar.y, int(bar.width * progress), bar.height)
        pygame.draw.rect(self.surface, GOLD, fill, border_radius=8)
        pygame.draw.rect(self.surface, (90, 90, 90), bar, width=1, border_radius=8)

        if progress >= 1.0:
            pygame.quit()
            app = PygameApp(starting_tribe=self.loading_tribe)
            app.run()
            self.running = False

    def quit(self):
        self.running = False

    def draw(self, dt):
        if self.state == "main":
            self.draw_main()
        elif self.state == "tribes":
            self.draw_tribe_select()
        elif self.state == "options":
            self.draw_options()
        elif self.state == "loading":
            self.draw_loading(dt)

    def scale_surface_to_window(self):
        window_w, window_h = self.screen.get_size()
        scaled = pygame.transform.smoothscale(self.surface, (window_w, window_h))
        self.screen.blit(scaled, (0, 0))

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                else:
                    for button in self.buttons:
                        button.handle_event(event)

            self.draw(dt)
            self.scale_surface_to_window()
            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    PygameMainMenu().run()