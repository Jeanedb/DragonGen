import math
import pygame
from pathlib import Path

from ui_pygame.core.base_screen import BaseScreen
from ui_pygame.widgets.button import Button

WIDTH, HEIGHT = 1000, 700
TEXT = (230, 230, 230)
MUTED = (180, 180, 180)
GOLD = (242, 201, 76)


class DragonPortraitScreen(BaseScreen):
    def __init__(self, world, change_screen, dragon):
        super().__init__()
        self.world = world
        self.change_screen = change_screen
        self.dragon = dragon
        self.dragons = self.get_dragons()
        self.current_index = self.dragons.index(dragon) if dragon in self.dragons else 0
        self.time = 0
        self.recolor_cache = {}
        self.blink_timer = 0
        self.blink_state = "open"

        project_root = Path(__file__).resolve().parents[2]
        bg_path = project_root / "assets" / "menu" / "village_bg.png"

        try:
            self.bg_image = pygame.image.load(str(bg_path)).convert()
            self.bg_image = pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT))
        except Exception:
            self.bg_image = None

        self.sprite_parts = {}
        for name in [
            "tail",
            "wing_left",
            "body",
            "feet",
            "neck",
            "head_open",
            "head_half",
            "head_closed",
            "wing_right"
        ]:
            path = project_root / "assets" / f"{name}.png"
            try:
                img = pygame.image.load(str(path)).convert_alpha()
                img = pygame.transform.scale_by(img, 0.45)
                self.sprite_parts[name] = img
            except Exception as e:
                print(f"Could not load sprite part {name}: {e}")
                self.sprite_parts[name] = None

    def clamp_rgb(self, value):
        return max(0, min(255, int(value)))

    def get_dragons(self):
        if hasattr(self.world, "dragons"):
            return list(self.world.dragons)
        return list(self.world)

    def previous_dragon(self):
        if not self.dragons:
            return

        self.current_index = (self.current_index - 1) % len(self.dragons)
        self.dragon = self.dragons[self.current_index]
        self.recolor_cache.clear()


    def next_dragon(self):
        if not self.dragons:
            return

        self.current_index = (self.current_index + 1) % len(self.dragons)
        self.dragon = self.dragons[self.current_index]
        self.recolor_cache.clear()

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
        }
        return ramps.get(tribe, ((50, 50, 50), (130, 130, 130), (220, 220, 220)))

    def vary_color(self, rgb, shift_r=0, shift_g=0, shift_b=0, brightness=1.0):
        r, g, b = rgb
        return (
            self.clamp_rgb((r + shift_r) * brightness),
            self.clamp_rgb((g + shift_g) * brightness),
            self.clamp_rgb((b + shift_b) * brightness),
        )

    def get_individualized_ramp(self, dragon):
        dark, mid, light = self.get_tribe_color_ramp(getattr(dragon, "tribe", "Unknown"))
        dragon_id = getattr(dragon, "id", 0)

        hue_shift = (dragon_id % 5) - 2
        green_shift = ((dragon_id // 3) % 5) - 2
        bright_shift = ((dragon_id // 7) % 5) - 2

        shift_r = hue_shift * 6
        shift_g = green_shift * 6
        shift_b = -hue_shift * 4
        brightness = 1.0 + (bright_shift * 0.04)

        return (
            self.vary_color(dark, shift_r, shift_g, shift_b, brightness),
            self.vary_color(mid, shift_r, shift_g, shift_b, brightness),
            self.vary_color(light, shift_r, shift_g, shift_b, brightness),
        )

    def recolor_surface(self, surface, dragon):
        dark, mid, light = self.get_individualized_ramp(dragon)
        recolored = surface.copy()

        for x in range(recolored.get_width()):
            for y in range(recolored.get_height()):
                r, g, b, a = recolored.get_at((x, y))
                if a == 0:
                    continue

                brightness = (r + g + b) / 3 / 255

                if brightness < 0.5:
                    t = brightness / 0.5
                    nr = dark[0] * (1 - t) + mid[0] * t
                    ng = dark[1] * (1 - t) + mid[1] * t
                    nb = dark[2] * (1 - t) + mid[2] * t
                else:
                    t = (brightness - 0.5) / 0.5
                    nr = mid[0] * (1 - t) + light[0] * t
                    ng = mid[1] * (1 - t) + light[1] * t
                    nb = mid[2] * (1 - t) + light[2] * t

                recolored.set_at((x, y), (
                    self.clamp_rgb(nr),
                    self.clamp_rgb(ng),
                    self.clamp_rgb(nb),
                    a
                ))

        return recolored

    def get_part(self, part_name):
        img = self.sprite_parts.get(part_name)
        if not img:
            return None

        tribe = getattr(self.dragon, "tribe", "Unknown")
        cache_key = (part_name, getattr(self.dragon, "id", 0), tribe)

        if cache_key not in self.recolor_cache:
            self.recolor_cache[cache_key] = self.recolor_surface(img, self.dragon)

        return self.recolor_cache[cache_key]

    def blit_rotated_around_pivot(self, screen, img, pivot_world, pivot_local, angle, debug=False):
        w, h = img.get_size()
        px, py = pivot_local

        side = int(max(w, h) * 2.5)

        pivot_surface = pygame.Surface((side, side), pygame.SRCALPHA)
        center_x = side // 2
        center_y = side // 2

        paste_x = int(center_x - px)
        paste_y = int(center_y - py)

        pivot_surface.blit(img, (paste_x, paste_y))

        rotated = pygame.transform.rotate(pivot_surface, angle)
        rotated_rect = rotated.get_rect(center=pivot_world)

        screen.blit(rotated, rotated_rect.topleft)

        if debug:
            pygame.draw.circle(screen, (255, 170, 0), pivot_world, 6)
            pygame.draw.circle(screen, (255, 255, 255), pivot_world, 2)

    def draw_dragon(self, screen):
        cx = WIDTH // 2
        cy = 340

        head_part = "head_open"

        if self.blink_state == "half":
            head_part = "head_half"
        elif self.blink_state == "closed":
            head_part = "head_closed"

       # breath = math.sin(self.time * 2.2) * 5
        tail_sway = math.sin(self.time * 1.8) * 4
        wing_sway = math.sin(self.time * 1.6) * 3

        body_x = cx - 210
        body_y = cy - 40 #+ breath

        anchors = {
            "body": (body_x, body_y),
            "tail": (body_x + 230 + tail_sway, body_y - 25),
            "feet": (body_x + 30, body_y + 72),
            "neck": (body_x + 15, body_y - 100),# + breath),
            "head_open": (body_x + 0, body_y - 120),# + breath),
            "wing_left": (body_x + 55, body_y - 105 + wing_sway),
            "wing_right": (body_x + 65, body_y - 95 - wing_sway),
        }

        shadow = pygame.Surface((420, 40), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 250), shadow.get_rect())
        screen.blit(shadow, (cx - 200, cy + 130))

        angles = {
            "wing_left": wing_sway,
            "wing_right": -wing_sway,
            "tail": tail_sway,
            "neck": math.sin(self.time * 1.4) * 2,
            head_part: math.sin(self.time * 1.4) * 3,
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
            head_part: (body_x + 54, body_y - 66),
        }

        neck_angle = angles["neck"]

        neck_root = pivot_locals["neck"]
        neck_head_socket = (50, 30)  # tweak later if needed

        offset_x = neck_head_socket[0] - neck_root[0]
        offset_y = neck_head_socket[1] - neck_root[1]

        angle_rad = math.radians(neck_angle)

        # Pygame screen-space rotation: Y axis goes downward.
        # This matches how pygame.transform.rotate visually moves the neck.
        rotated_offset_x = offset_x * math.cos(angle_rad) + offset_y * math.sin(angle_rad)
        rotated_offset_y = -offset_x * math.sin(angle_rad) + offset_y * math.cos(angle_rad)

        pivot_worlds[head_part] = (
            pivot_worlds["neck"][0] + rotated_offset_x,
            pivot_worlds["neck"][1] + rotated_offset_y
        )
        pygame.draw.circle(screen, (0, 255, 255), pivot_worlds[head_part], 4)

        head_nod = math.sin(self.time * 1.8) * 1.5

        angles[head_part] = neck_angle + head_nod

        debug_pivots = True

        for part_name in ["wing_left", "tail", "body", "feet", "neck", head_part, "wing_right"]:
            img = self.get_part(part_name)
            if not img:
                continue

            if part_name in angles:
                
                self.blit_rotated_around_pivot(
                    screen,
                    img,
                    pivot_world=pivot_worlds[part_name],
                    pivot_local=pivot_locals[part_name],
                    angle=angles[part_name],
                    debug=debug_pivots
                )

            else:
                screen.blit(img, anchors[part_name])

    def update(self, dt):
        self.time += dt
        self.blink_timer += dt

        cycle = self.blink_timer % 4.0

        if cycle < 0.10:
            self.blink_state = "closed"
        elif cycle < 0.18:
            self.blink_state = "half"
        else:
            self.blink_state = "open"

    def draw(self, screen):
        self.buttons.clear()

        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill((18, 18, 18))

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        name = getattr(self.dragon, "name", "Unknown")
        tribe = getattr(self.dragon, "tribe", "Unknown")
        role = getattr(self.dragon, "role", "Unknown")

        title = self.title_font.render(name, True, TEXT)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 70)))

        subtitle = self.section_font.render(f"{tribe} • {role}", True, MUTED)
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 115)))

        self.draw_dragon(screen)

        prev_btn = Button(
            (280, 630, 120, 38),
            "Previous",
            self.previous_dragon
        )
        self.buttons.append(prev_btn)
        prev_btn.draw(screen, self.font)

        next_btn = Button(
            (600, 630, 120, 38),
            "Next",
            self.next_dragon
        )
        self.buttons.append(next_btn)
        next_btn.draw(screen, self.font)

        return_btn = Button(
            (430, 630, 140, 38),
            "Return",
            lambda: self.change_screen("scroll_library")
        )
        self.buttons.append(return_btn)
        return_btn.draw(screen, self.font)

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def blit_rotated(self, screen, img, pos, angle):
        rotated = pygame.transform.rotate(img, angle)
        rect = rotated.get_rect(center=img.get_rect(topleft=pos).center)
        screen.blit(rotated, rect.topleft)