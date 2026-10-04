import math
import random
from pathlib import Path

import pygame

from ui_pygame.core.base_screen import BaseScreen


WIDTH, HEIGHT = 1000, 700
TEXT = (236, 222, 196)
MUTED = (176, 158, 132)
GOLD = (227, 183, 84)
BRONZE = (133, 91, 53)
CREAM = (248, 230, 192)
PANEL = (31, 25, 20)
RED = (196, 83, 68)
GREEN = (111, 178, 120)


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


class PortraitButton:
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

    def draw(self, screen, font, mouse_pos):
        hovered = self.enabled and self.rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (7, 5, 4), self.rect.move(0, 4), border_radius=7)
        if not self.enabled:
            edge, fill, color = (72, 65, 58), (40, 37, 34), (112, 104, 94)
        elif self.primary:
            edge = GOLD if hovered else (177, 121, 53)
            fill = (111, 66, 31) if hovered else (79, 48, 27)
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
                (inner.x + 8, inner.y + 3),
                (inner.right - 8, inner.y + 3),
                1,
            )
        image = font.render(self.label, True, color)
        screen.blit(image, image.get_rect(center=self.rect.center))


class DragonPortraitScreen(BaseScreen):
    """Full-screen visual inspection room for one dragon.

    The Scroll Library owns biographies, lineage, and legacy. This screen keeps
    its purpose deliberately narrower: see the dragon clearly, inspect a small
    identity record, and move through the archive.
    """

    def __init__(self, world, change_screen, dragon):
        super().__init__()
        self.world = world
        self.change_screen = change_screen
        self.dragons = self.get_dragons()
        self.dragon = dragon if dragon in self.dragons else (self.dragons[0] if self.dragons else None)
        self.current_index = self.dragons.index(self.dragon) if self.dragon in self.dragons else 0

        self.time = 0.0
        self.blink_timer = random.uniform(2.0, 4.5)
        self.blink_state = "open"
        self.blink_elapsed = 0.0
        self.animation_paused = False
        self.ui_hidden = False
        self.recolor_cache = {}
        self.background_cache = {}
        self.buttons = []

        self.title_fantasy = pygame.font.SysFont("georgia", 31, bold=True)
        self.heading = pygame.font.SysFont("georgia", 17, bold=True)
        self.body = pygame.font.SysFont("georgia", 13)
        self.body_bold = pygame.font.SysFont("georgia", 13, bold=True)
        self.small = pygame.font.SysFont("georgia", 11)
        self.tiny = pygame.font.SysFont("georgia", 10)

        self.project_root = find_project_root()
        self.sprite_parts = {}
        for name in (
            "tail",
            "wing_left",
            "body",
            "feet",
            "neck",
            "head_open",
            "head_half",
            "head_closed",
            "wing_right",
        ):
            path = self.project_root / "assets" / f"{name}.png"
            try:
                image = pygame.image.load(str(path)).convert_alpha()
                self.sprite_parts[name] = pygame.transform.scale_by(image, 0.45)
            except Exception as error:
                print(f"Could not load sprite part {name}: {error}")
                self.sprite_parts[name] = None

    # Data -----------------------------------------------------------

    def get_dragons(self):
        return list(getattr(self.world, "dragons", self.world if self.world is not None else []))

    def is_dead(self, dragon=None):
        dragon = dragon or self.dragon
        return str(getattr(dragon, "status", "Alive")).lower() in {"dead", "deceased"}

    def safe_value(self, *names, default="Unknown"):
        if not self.dragon:
            return default
        for name in names:
            value = getattr(self.dragon, name, None)
            if value not in (None, "", []):
                if isinstance(value, (list, tuple, set)):
                    return ", ".join(str(item) for item in value) or default
                return str(value)
        return default

    def age_text(self):
        value = self.safe_value("age_moons", "age")
        return value if value == "Unknown" or "moon" in value.lower() else f"{value} moons"

    def location_text(self):
        value = self.safe_value("location", "current_location", "assigned_location")
        return value.replace("_", " ").title() if value != "Unknown" else value

    def record_position(self):
        if not self.dragons:
            return "0 OF 0"
        return f"{self.current_index + 1} OF {len(self.dragons)}"

    def set_dragon(self, index):
        if not self.dragons:
            return
        self.current_index = index % len(self.dragons)
        self.dragon = self.dragons[self.current_index]
        self.world.selected_portrait_dragon = self.dragon
        self.recolor_cache.clear()
        self.blink_timer = random.uniform(2.0, 4.5)
        self.blink_state = "open"
        self.blink_elapsed = 0.0

    def previous_dragon(self):
        self.set_dragon(self.current_index - 1)

    def next_dragon(self):
        self.set_dragon(self.current_index + 1)

    def return_to_library(self):
        if self.dragon:
            self.world.selected_portrait_dragon = self.dragon
        self.change_screen("scroll_library")

    def toggle_animation(self):
        self.animation_paused = not self.animation_paused

    def toggle_ui(self):
        self.ui_hidden = not self.ui_hidden

    # Background -----------------------------------------------------

    def tribe_slug(self):
        tribe = self.safe_value("tribe", default=getattr(self.world, "tribe_name", ""))
        return tribe.lower().replace(" tribe", "").replace(" ", "")

    def get_background(self):
        slug = self.tribe_slug()
        if slug in self.background_cache:
            return self.background_cache[slug]

        candidates = [
            self.project_root / "assets" / slug / "dragon_portrait_bg.png",
            self.project_root / "assets" / slug / "portrait_bg.png",
            self.project_root / "assets" / slug / "location_map.png",
            self.project_root / "assets" / "menu" / "village_bg.png",
            self.project_root / "assets" / "menu" / "main_locations_bg.png",
        ]
        background = None
        for path in candidates:
            if not path.exists():
                continue
            try:
                background = pygame.image.load(str(path)).convert()
                background = pygame.transform.scale(background, (WIDTH, HEIGHT))
                break
            except Exception as error:
                print(f"Could not load portrait background {path}: {error}")
        self.background_cache[slug] = background
        return background

    # Sprite recolouring --------------------------------------------

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

    def dragon_seed(self):
        raw_id = getattr(self.dragon, "id", 0)
        try:
            return int(raw_id)
        except (TypeError, ValueError):
            return sum(ord(character) for character in str(raw_id))

    def vary_color(self, rgb, shift_r=0, shift_g=0, shift_b=0, brightness=1.0):
        red, green, blue = rgb
        return (
            self.clamp_rgb((red + shift_r) * brightness),
            self.clamp_rgb((green + shift_g) * brightness),
            self.clamp_rgb((blue + shift_b) * brightness),
        )

    def get_individualized_ramp(self, dragon):
        dark, middle, light = self.get_tribe_color_ramp(getattr(dragon, "tribe", "Unknown"))
        dragon_id = self.dragon_seed()
        hue_shift = (dragon_id % 5) - 2
        green_shift = ((dragon_id // 3) % 5) - 2
        brightness_shift = ((dragon_id // 7) % 5) - 2
        shift_r = hue_shift * 6
        shift_g = green_shift * 6
        shift_b = -hue_shift * 4
        brightness = 1.0 + (brightness_shift * 0.04)
        return (
            self.vary_color(dark, shift_r, shift_g, shift_b, brightness),
            self.vary_color(middle, shift_r, shift_g, shift_b, brightness),
            self.vary_color(light, shift_r, shift_g, shift_b, brightness),
        )

    def recolor_surface(self, surface, dragon):
        dark, middle, light = self.get_individualized_ramp(dragon)
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
                    tuple(
                        self.clamp_rgb(low[index] * (1 - blend) + high[index] * blend)
                        for index in range(3)
                    )
                    + (alpha,),
                )
        return recolored

    def get_part(self, part_name):
        image = self.sprite_parts.get(part_name)
        if not image or not self.dragon:
            return None
        key = (
            part_name,
            str(getattr(self.dragon, "id", 0)),
            str(getattr(self.dragon, "tribe", "Unknown")),
        )
        if key not in self.recolor_cache:
            self.recolor_cache[key] = self.recolor_surface(image, self.dragon)
        return self.recolor_cache[key]

    # Sprite animation ----------------------------------------------

    def blit_rotated_around_pivot(self, screen, image, pivot_world, pivot_local, angle):
        width, height = image.get_size()
        pivot_x, pivot_y = pivot_local
        side = int(max(width, height) * 2.5)
        pivot_surface = pygame.Surface((side, side), pygame.SRCALPHA)
        center_x = side // 2
        center_y = side // 2
        pivot_surface.blit(image, (int(center_x - pivot_x), int(center_y - pivot_y)))
        rotated = pygame.transform.rotate(pivot_surface, angle)
        rotated_rect = rotated.get_rect(center=pivot_world)
        screen.blit(rotated, rotated_rect.topleft)

    def draw_dragon(self, screen):
        if not self.dragon:
            return
        center_x = 610
        center_y = 358
        head_part = {
            "half": "head_half",
            "half_opening": "head_half",
            "closed": "head_closed",
        }.get(self.blink_state, "head_open")

        tail_sway = math.sin(self.time * 1.8) * 4
        wing_sway = math.sin(self.time * 1.6) * 3
        body_x = center_x - 210
        body_y = center_y - 40

        anchors = {
            "body": (body_x, body_y),
            "feet": (body_x + 30, body_y + 72),
        }
        angles = {
            "wing_left": wing_sway,
            "wing_right": -wing_sway,
            "tail": tail_sway,
            "neck": math.sin(self.time * 1.4) * 2,
        }
        pivot_locals = {
            "tail": (12, 140),
            "wing_left": (12, 152),
            "wing_right": (12, 152),
            "neck": (24, 118),
            head_part: (52, 48),
        }
        pivot_worlds = {
            "tail": (body_x + 240, body_y + 105),
            "wing_left": (body_x + 69, body_y + 50),
            "wing_right": (body_x + 74, body_y + 55),
            "neck": (body_x + 37, body_y + 27),
        }

        neck_angle = angles["neck"]
        neck_root = pivot_locals["neck"]
        neck_head_socket = (50, 30)
        offset_x = neck_head_socket[0] - neck_root[0]
        offset_y = neck_head_socket[1] - neck_root[1]
        angle_radians = math.radians(neck_angle)
        rotated_offset_x = offset_x * math.cos(angle_radians) + offset_y * math.sin(angle_radians)
        rotated_offset_y = -offset_x * math.sin(angle_radians) + offset_y * math.cos(angle_radians)
        pivot_worlds[head_part] = (
            pivot_worlds["neck"][0] + rotated_offset_x,
            pivot_worlds["neck"][1] + rotated_offset_y,
        )
        angles[head_part] = neck_angle + math.sin(self.time * 1.8) * 1.5

        shadow = pygame.Surface((470, 48), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 185), shadow.get_rect())
        screen.blit(shadow, (center_x - 225, center_y + 126))

        for part_name in ("wing_left", "tail", "body", "feet", "neck", head_part, "wing_right"):
            image = self.get_part(part_name)
            if not image:
                continue
            if part_name in angles:
                self.blit_rotated_around_pivot(
                    screen,
                    image,
                    pivot_worlds[part_name],
                    pivot_locals[part_name],
                    angles[part_name],
                )
            else:
                screen.blit(image, anchors[part_name])

    def update(self, dt):
        if self.animation_paused or not self.dragon:
            return
        self.time += dt
        if self.blink_state == "open":
            self.blink_timer -= dt
            if self.blink_timer <= 0:
                self.blink_state = "half"
                self.blink_elapsed = 0.0
        else:
            self.blink_elapsed += dt
            if self.blink_state == "half" and self.blink_elapsed >= 0.07:
                self.blink_state = "closed"
                self.blink_elapsed = 0.0
            elif self.blink_state == "closed" and self.blink_elapsed >= 0.08:
                self.blink_state = "half_opening"
                self.blink_elapsed = 0.0
            elif self.blink_state == "half_opening" and self.blink_elapsed >= 0.07:
                self.blink_state = "open"
                self.blink_timer = random.uniform(2.0, 4.5)
                self.blink_elapsed = 0.0

    # Drawing helpers ------------------------------------------------

    def draw_text(self, screen, text, x, y, font, color=TEXT, center=False):
        image = font.render(str(text), True, color)
        rect = image.get_rect()
        if center:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        screen.blit(image, rect)
        return rect

    def fit_text(self, text, font, max_width):
        text = str(text)
        if font.size(text)[0] <= max_width:
            return text
        while text and font.size(text + "…")[0] > max_width:
            text = text[:-1]
        return text + "…"

    def draw_panel(self, screen, rect, alpha=225):
        shadow = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow, (5, 3, 2, 190), shadow.get_rect(), border_radius=12)
        screen.blit(shadow, (rect.x + 5, rect.y + 6))
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (*PANEL, alpha), panel.get_rect(), border_radius=12)
        screen.blit(panel, rect.topleft)
        pygame.draw.rect(screen, BRONZE, rect, 2, border_radius=12)
        pygame.draw.rect(screen, (61, 42, 31), rect.inflate(-8, -8), 1, border_radius=9)

    def draw_outer_frame(self, screen):
        outer = pygame.Rect(24, 20, WIDTH - 48, HEIGHT - 40)
        pygame.draw.rect(screen, (20, 13, 9), outer, 8, border_radius=22)
        pygame.draw.rect(screen, BRONZE, outer, 3, border_radius=22)
        pygame.draw.rect(screen, (79, 52, 35), outer.inflate(-12, -12), 2, border_radius=17)
        for x, y in (
            (outer.left + 16, outer.top + 16),
            (outer.right - 16, outer.top + 16),
            (outer.left + 16, outer.bottom - 16),
            (outer.right - 16, outer.bottom - 16),
        ):
            pygame.draw.circle(screen, GOLD, (x, y), 4)
            pygame.draw.circle(screen, (69, 42, 27), (x, y), 2)

    def draw_title_plaque(self, screen):
        rect = pygame.Rect(300, 31, 400, 92)
        pygame.draw.polygon(
            screen,
            BRONZE,
            [
                (rect.x + 15, rect.y),
                (rect.right - 15, rect.y),
                (rect.right, rect.y + 15),
                (rect.right, rect.bottom - 15),
                (rect.right - 15, rect.bottom),
                (rect.x + 15, rect.bottom),
                (rect.x, rect.bottom - 15),
                (rect.x, rect.y + 15),
            ],
        )
        inner = rect.inflate(-5, -5)
        pygame.draw.polygon(
            screen,
            (30, 23, 18),
            [
                (inner.x + 12, inner.y),
                (inner.right - 12, inner.y),
                (inner.right, inner.y + 12),
                (inner.right, inner.bottom - 12),
                (inner.right - 12, inner.bottom),
                (inner.x + 12, inner.bottom),
                (inner.x, inner.bottom - 12),
                (inner.x, inner.y + 12),
            ],
        )
        name = self.safe_value("name")
        prefix = "† " if self.is_dead() else ""
        self.draw_text(screen, prefix + name.upper(), rect.centerx, rect.y + 32, self.title_fantasy, CREAM, center=True)
        descriptor = f"{self.safe_value('tribe')}  •  {self.safe_value('role')}"
        self.draw_text(screen, descriptor.upper(), rect.centerx, rect.y + 67, self.small, GOLD, center=True)

    def draw_identity_panel(self, screen):
        rect = pygame.Rect(44, 145, 225, 398)
        self.draw_panel(screen, rect, alpha=232)
        self.draw_text(screen, "ARCHIVE PORTRAIT", rect.x + 17, rect.y + 17, self.heading, GOLD)
        pygame.draw.line(screen, (106, 73, 48), (rect.x + 17, rect.y + 48), (rect.right - 17, rect.y + 48), 1)

        status = self.safe_value("status", default="Alive")
        status_color = RED if self.is_dead() else GREEN
        pygame.draw.circle(screen, status_color, (rect.x + 23, rect.y + 71), 5)
        self.draw_text(screen, status.upper(), rect.x + 36, rect.y + 63, self.body_bold, status_color)

        fields = (
            ("AGE", self.age_text()),
            ("RANK", self.safe_value("rank", default="None")),
            ("HEALTH", self.safe_value("health")),
            ("PERSONALITY", self.safe_value("personality")),
            ("LOCATION", self.location_text()),
            ("HEIGHT", self.safe_value("height")),
            ("EYES", self.safe_value("eye_color")),
        )
        y = rect.y + 96
        for label, value in fields:
            self.draw_text(screen, label, rect.x + 17, y, self.tiny, GOLD)
            self.draw_text(
                screen,
                self.fit_text(value, self.body, rect.width - 34),
                rect.x + 17,
                y + 15,
                self.body,
                TEXT,
            )
            y += 37

        pygame.draw.line(screen, (106, 73, 48), (rect.x + 17, rect.bottom - 49), (rect.right - 17, rect.bottom - 49), 1)
        self.draw_text(screen, "PERMANENT RECORD", rect.centerx, rect.bottom - 29, self.tiny, MUTED, center=True)

    def draw_stage(self, screen):
        rect = pygame.Rect(287, 142, 669, 405)
        stage = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(stage, (20, 15, 12, 120), stage.get_rect(), border_radius=16)
        pygame.draw.ellipse(stage, (189, 145, 69, 18), (80, 12, rect.width - 160, rect.height - 45))
        pygame.draw.rect(stage, (131, 90, 52, 135), stage.get_rect(), 2, border_radius=16)
        pygame.draw.rect(stage, (52, 36, 26, 170), stage.get_rect().inflate(-10, -10), 1, border_radius=12)
        screen.blit(stage, rect.topleft)
        self.draw_text(screen, "LIVING LIKENESS", rect.x + 18, rect.y + 15, self.tiny, GOLD)
        label = self.tiny.render(
            "ANIMATION PAUSED" if self.animation_paused else "ARCHIVE ANIMATION",
            True,
            MUTED,
        )
        screen.blit(label, label.get_rect(topright=(rect.right - 18, rect.y + 15)))

    def draw_footer(self, screen, mouse_pos):
        record_badge = pygame.Rect(58, 593, 138, 32)
        pygame.draw.rect(screen, (31, 25, 20), record_badge, border_radius=7)
        pygame.draw.rect(screen, BRONZE, record_badge, 1, border_radius=7)
        self.draw_text(
            screen,
            f"RECORD {self.record_position()}",
            record_badge.centerx,
            record_badge.centery,
            self.tiny,
            GOLD,
            center=True,
        )

        previous = PortraitButton((220, 602, 150, 44), "PREVIOUS DRAGON", self.previous_dragon, enabled=len(self.dragons) > 1)
        back = PortraitButton((390, 596, 220, 52), "RETURN TO LIBRARY", self.return_to_library, primary=True)
        following = PortraitButton((630, 602, 150, 44), "NEXT DRAGON", self.next_dragon, enabled=len(self.dragons) > 1)
        pause_label = "RESUME" if self.animation_paused else "PAUSE"
        pause = PortraitButton((800, 602, 78, 36), pause_label, self.toggle_animation)
        hide = PortraitButton((884, 602, 72, 36), "HIDE UI", self.toggle_ui)
        self.buttons.extend((previous, back, following, pause, hide))
        for button in self.buttons:
            button.draw(screen, self.small if button is back else self.tiny, mouse_pos)

        self.draw_text(
            screen,
            "←/→ Browse   •   Space Pause   •   H Hide Interface   •   Esc Return",
            WIDTH // 2,
            667,
            self.tiny,
            MUTED,
            center=True,
        )

    def draw(self, screen):
        self.buttons.clear()
        background = self.get_background()
        if background:
            screen.blit(background, (0, 0))
        else:
            screen.fill((27, 20, 16))

        dimmer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dimmer.fill((7, 4, 2, 105 if self.ui_hidden else 130))
        screen.blit(dimmer, (0, 0))

        if self.ui_hidden:
            self.draw_dragon(screen)
            self.draw_text(
                screen,
                "Click or press H to restore the archive interface",
                WIDTH // 2,
                672,
                self.tiny,
                MUTED,
                center=True,
            )
            return

        self.draw_outer_frame(screen)
        self.draw_stage(screen)
        self.draw_dragon(screen)
        self.draw_identity_panel(screen)
        self.draw_title_plaque(screen)
        self.draw_footer(screen, pygame.mouse.get_pos())

    def handle_event(self, event):
        if self.ui_hidden:
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.ui_hidden = False
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_h, pygame.K_ESCAPE):
                self.ui_hidden = False
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                self.previous_dragon()
                return
            if event.key == pygame.K_RIGHT:
                self.next_dragon()
                return
            if event.key == pygame.K_SPACE:
                self.toggle_animation()
                return
            if event.key == pygame.K_h:
                self.toggle_ui()
                return
            if event.key == pygame.K_ESCAPE:
                self.return_to_library()
                return

        for button in self.buttons:
            button.handle_event(event)
