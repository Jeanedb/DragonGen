import random
import pygame
from pathlib import Path
from tkinter import filedialog

from core.save_manager import load_world
from ui_pygame.widgets.button import Button
from ui_pygame.app import PygameApp

WIDTH, HEIGHT = 1000, 700
FPS = 60

TEXT = (230, 230, 230)
MUTED = (180, 180, 180)
GOLD = (242, 201, 76)
BRONZE = (151, 102, 52)
DEEP_BROWN = (28, 18, 14)
PANEL_DARK = (27, 24, 22)

TRIBE_THEMES = {
    "skywing": ((132, 43, 35), (222, 101, 55), "SK"),
    "seawing": ((20, 91, 112), (55, 190, 198), "SE"),
    "rainwing": ((96, 39, 104), (94, 202, 126), "RA"),
    "sandwing": ((146, 94, 32), (232, 183, 74), "SA"),
    "icewing": ((96, 145, 170), (203, 235, 240), "IC"),
    "nightwing": ((39, 31, 73), (112, 86, 164), "NI"),
    "mudwing": ((91, 54, 35), (156, 105, 65), "MU"),
    "hivewing": ((126, 69, 16), (239, 168, 34), "HI"),
    "silkwing": ((103, 63, 132), (217, 151, 230), "SI"),
    "leafwing": ((39, 92, 45), (105, 177, 76), "LE"),
    "mixed": ((66, 65, 75), (183, 137, 65), "MX"),
}

TRIBES = [
    ("skywing", "SkyWing", "Proud, fierce, and battle-ready."),
    ("seawing", "SeaWing", "Diplomatic, aquatic, and socially complex."),
    ("rainwing", "RainWing", "Colorful, emotional, and unpredictable."),
    ("sandwing", "SandWing", "Harsh, political, and survival-minded."),
    ("icewing", "IceWing", "Formal, hierarchical, and reputation-driven."),
    ("nightwing", "NightWing", "Secretive, clever, and prophecy-haunted."),
    ("mudwing", "MudWing", "Loyal, grounded, and family-focused."),
    ("hivewing", "HiveWing", "Structured, ambitious, and hierarchy-focused."),
    ("silkwing", "SilkWing", "Cooperative, expressive, and community-minded."),
    ("leafwing", "LeafWing", "Independent, protective, and deeply resilient."),
    ("mixed", "Mixed Tribe", "A varied tribe with unpredictable dynamics."),
]


class CircleButton:
    """Simple circular hit area used by the tribe medallions."""

    def __init__(self, center, radius, callback):
        self.center = center
        self.radius = radius
        self.callback = callback

    def contains(self, point):
        dx = point[0] - self.center[0]
        dy = point[1] - self.center[1]
        return dx * dx + dy * dy <= self.radius * self.radius

    def handle_event(self, event):
        if (
            event.type == pygame.MOUSEBUTTONUP
            and event.button == 1
            and self.contains(event.pos)
        ):
            self.callback()


class FantasyButton:
    """A beveled menu button that avoids the default blue UI look."""

    def __init__(self, rect, label, callback, enabled=True, primary=False):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.callback = callback
        self.enabled = enabled
        self.primary = primary

    def handle_event(self, event):
        if (
            self.enabled
            and event.type == pygame.MOUSEBUTTONUP
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        ):
            self.callback()

    def draw(self, surface, font):
        hovered = self.enabled and self.rect.collidepoint(pygame.mouse.get_pos())

        shadow = self.rect.move(0, 5)
        pygame.draw.rect(surface, (12, 8, 6), shadow, border_radius=8)

        if not self.enabled:
            fill = (45, 42, 39)
            edge = (80, 74, 66)
            text_color = (112, 106, 98)
        elif self.primary:
            fill = (91, 55, 26) if not hovered else (124, 75, 32)
            edge = GOLD if hovered else (190, 134, 65)
            text_color = (255, 234, 185)
        else:
            fill = (48, 42, 37) if not hovered else (67, 57, 48)
            edge = (151, 111, 67) if hovered else (100, 79, 57)
            text_color = (231, 214, 182)

        pygame.draw.rect(surface, edge, self.rect, border_radius=8)
        inner = self.rect.inflate(-6, -6)
        pygame.draw.rect(surface, fill, inner, border_radius=6)
        pygame.draw.line(
            surface,
            (211, 167, 91) if self.enabled else (76, 72, 67),
            (inner.left + 8, inner.top + 3),
            (inner.right - 8, inner.top + 3),
            1,
        )

        image = font.render(self.label, True, text_color)
        surface.blit(image, image.get_rect(center=self.rect.center))


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

        # Serif faces give the menus a carved-bookplate look while keeping
        # everything code-driven and portable.
        self.fantasy_title = pygame.font.SysFont("georgia", 44, bold=True)
        self.fantasy_heading = pygame.font.SysFont("georgia", 25, bold=True)
        self.fantasy_label = pygame.font.SysFont("georgia", 17, bold=True)
        self.fantasy_body = pygame.font.SysFont("georgia", 16)
        self.crest_font = pygame.font.SysFont("georgia", 24, bold=True)

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

    def draw_beveled_panel(self, rect, fill=PANEL_DARK, edge=BRONZE, cut=12):
        """Draw a clipped-corner fantasy plaque."""
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

        shadow = [(px, py + 5) for px, py in points]
        pygame.draw.polygon(self.surface, (10, 7, 6), shadow)
        pygame.draw.polygon(self.surface, edge, points)

        inner_rect = pygame.Rect(rect).inflate(-6, -6)
        ix, iy, iw, ih = inner_rect
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
        pygame.draw.polygon(self.surface, fill, inner_points)
        pygame.draw.lines(self.surface, (213, 164, 88), False, inner_points[:3], 1)

    def draw_tribe_medallion(self, tribe_id, name, center, radius, selected):
        dark, bright, monogram = TRIBE_THEMES[tribe_id]
        mouse = pygame.mouse.get_pos()
        dx = mouse[0] - center[0]
        dy = mouse[1] - center[1]
        hovered = dx * dx + dy * dy <= radius * radius

        if selected or hovered:
            glow = pygame.Surface((radius * 3, radius * 3), pygame.SRCALPHA)
            glow_center = (glow.get_width() // 2, glow.get_height() // 2)
            glow_color = GOLD if selected else bright
            for size, alpha in ((radius + 14, 18), (radius + 9, 32), (radius + 4, 50)):
                pygame.draw.circle(glow, (*glow_color, alpha), glow_center, size)
            self.surface.blit(glow, glow.get_rect(center=center))

        # Shadow, metal rim, coloured enamel, and a soft upper highlight.
        pygame.draw.circle(self.surface, (8, 6, 5), (center[0], center[1] + 5), radius + 8)
        pygame.draw.circle(self.surface, GOLD if selected else (111, 85, 58), center, radius + 8)
        pygame.draw.circle(self.surface, (35, 28, 23), center, radius + 4)
        pygame.draw.circle(self.surface, dark, center, radius)
        pygame.draw.circle(self.surface, bright, (center[0], center[1] - 5), radius - 9)
        pygame.draw.circle(self.surface, dark, (center[0], center[1] + 8), radius - 14)
        pygame.draw.arc(
            self.surface,
            (255, 239, 196),
            pygame.Rect(center[0] - radius + 9, center[1] - radius + 9, (radius - 9) * 2, (radius - 9) * 2),
            0.55,
            2.55,
            2,
        )

        # Temporary crest. These monograms can later be replaced one-for-one
        # by finished tribe portrait assets without changing the layout.
        crest = self.crest_font.render(monogram, True, (255, 239, 198))
        self.surface.blit(crest, crest.get_rect(center=(center[0], center[1] - 1)))

        label_color = (255, 225, 158) if selected else (225, 210, 184)
        label = self.fantasy_label.render(name, True, label_color)
        self.surface.blit(label, label.get_rect(center=(center[0], center[1] + radius + 22)))

        if selected:
            marker = self.small.render("SELECTED", True, GOLD)
            self.surface.blit(marker, marker.get_rect(center=(center[0], center[1] + radius + 42)))

    def draw_main(self):
        self.buttons.clear()
        self.draw_background()

        self.draw_text("DragonGen", 70, 105, self.title_font, GOLD)

        menu_items = [
            ("New Game", self.show_tribes),
            ("Load Game", self.load_game),
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

        # A contained game-board frame keeps the background as atmosphere
        # instead of making it compete with the controls.
        frame = pygame.Surface((950, 670), pygame.SRCALPHA)
        frame.fill((12, 9, 8, 196))
        self.surface.blit(frame, (25, 15))
        pygame.draw.rect(self.surface, (97, 72, 48), (25, 15, 950, 670), width=3, border_radius=18)
        pygame.draw.rect(self.surface, (35, 27, 22), (32, 22, 936, 656), width=2, border_radius=15)

        self.draw_beveled_panel((250, 24, 500, 64), fill=(31, 24, 20), edge=(127, 89, 51))
        title = self.fantasy_title.render("DRAGONGEN", True, (244, 210, 148))
        self.surface.blit(title, title.get_rect(center=(WIDTH // 2, 56)))

        self.draw_beveled_panel((330, 98, 340, 42), fill=(39, 34, 31), edge=(104, 85, 67), cut=10)
        heading = self.fantasy_heading.render("TRIBE SELECTION", True, (242, 224, 188))
        self.surface.blit(heading, heading.get_rect(center=(WIDTH // 2, 119)))

        # Six crests on the first row, five centred beneath them.
        radius = 45
        first_row_x = [95, 257, 419, 581, 743, 905]
        second_row_x = [176, 338, 500, 662, 824]

        for idx, (tribe_id, name, _desc) in enumerate(TRIBES):
            if idx < 6:
                center = (first_row_x[idx], 205)
            else:
                center = (second_row_x[idx - 6], 350)

            selected = tribe_id == self.selected_tribe
            self.draw_tribe_medallion(tribe_id, name, center, radius, selected)

            hitbox = CircleButton(
                center,
                radius + 9,
                lambda tid=tribe_id: self.select_tribe(tid),
            )
            self.buttons.append(hitbox)

        self.draw_beveled_panel((85, 455, 830, 118), fill=(31, 27, 24), edge=(116, 86, 55))

        if self.selected_tribe:
            _tid, selected_name, selected_desc = next(
                tribe for tribe in TRIBES if tribe[0] == self.selected_tribe
            )
            accent = TRIBE_THEMES[self.selected_tribe][1]
            pygame.draw.rect(self.surface, accent, (103, 473, 5, 80), border_radius=2)

            name_image = self.fantasy_heading.render(selected_name.upper(), True, (247, 215, 153))
            self.surface.blit(name_image, (126, 472))

            desc_image = self.fantasy_body.render(selected_desc, True, (218, 207, 188))
            self.surface.blit(desc_image, (126, 510))

            hint = self.small.render(
                "This choice shapes culture, relationships, conflict, and survival.",
                True,
                (154, 146, 134),
            )
            self.surface.blit(hint, (126, 540))
        else:
            prompt = self.fantasy_heading.render("Choose a founding tribe", True, (231, 211, 176))
            self.surface.blit(prompt, prompt.get_rect(center=(WIDTH // 2, 495)))
            hint = self.fantasy_body.render(
                "Select a crest above to review its culture before beginning.",
                True,
                (166, 156, 142),
            )
            self.surface.blit(hint, hint.get_rect(center=(WIDTH // 2, 535)))

        begin_enabled = self.selected_tribe is not None
        back = FantasyButton((70, 615, 155, 44), "BACK", self.show_main)
        random_button = FantasyButton((405, 615, 190, 44), "RANDOM TRIBE", self.select_random_tribe)
        begin = FantasyButton(
            (690, 615, 240, 44),
            "CONFIRM SELECTION",
            self.begin_selected_game,
            enabled=begin_enabled,
            primary=True,
        )

        for button in (back, random_button, begin):
            self.buttons.append(button)
            button.draw(self.surface, self.fantasy_label)

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

    def select_random_tribe(self):
        self.selected_tribe = random.choice(TRIBES)[0]

    def begin_selected_game(self):
        if not self.selected_tribe:
            return
        self.launch_game(self.selected_tribe)

    def start_mixed_game(self):
        self.launch_game("mixed")
    
    def load_game(self):
        project_root = Path(__file__).resolve().parents[1]
        saves_dir = project_root / "saves"
        saves_dir.mkdir(exist_ok=True)

        filename = filedialog.askopenfilename(
            title="Load DragonGen Save",
            initialdir=str(saves_dir),
            filetypes=[("DragonGen Saves", "*.json")]
        )

        if not filename:
            return

        try:
            world = load_world(filename)
        except Exception as error:
            print(f"Could not load save: {error}")
            return

        pygame.quit()
        app = PygameApp(world=world)
        app.run()
        self.running = False

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

            if not self.running:
                break

            self.draw(dt)

            if not self.running:
                break

            self.scale_surface_to_window()
            pygame.display.flip()

        pygame.quit()

if __name__ == "__main__":
    PygameMainMenu().run()
