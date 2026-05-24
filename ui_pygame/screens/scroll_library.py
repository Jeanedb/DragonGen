import pygame
from pathlib import Path

from ui_pygame.core.base_screen import BaseScreen
from ui_pygame.widgets.button import Button

try:
    from core.sim.flavor import ensure_dragon_flavor, generate_dragon_bio, generate_legacy_text
except Exception:
    ensure_dragon_flavor = None
    generate_dragon_bio = None
    generate_legacy_text = None

WIDTH, HEIGHT = 1000, 700

TEXT = (230, 230, 230)
MUTED = (180, 180, 180)
GOLD = (242, 201, 76)


class ScrollLibraryScreen(BaseScreen):
    def __init__(self, world, change_screen):
        super().__init__()
        self.world = world
        self.change_screen = change_screen
        self.selected_dragon = self.get_dragons()[0] if self.get_dragons() else None
        self.detail_scroll = 0
        self.roster_scroll = 0
        self.recolor_cache = {}

        project_root = Path(__file__).resolve().parents[2]
        bg_path = project_root / "assets" / "menu" / "village_bg.png"

        try:
            self.bg_image = pygame.image.load(str(bg_path)).convert()
            self.bg_image = pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT))
        except Exception:
            self.bg_image = None

        self.sprite_parts = {}
        sprite_names = [
            "tail",
            "wing_left",
            "body",
            "feet",
            "neck",
            "head_open",
            "wing_right",
        ]

        for name in sprite_names:
            path = project_root / "assets" / f"{name}.png"
            try:
                img = pygame.image.load(str(path)).convert_alpha()
                img = pygame.transform.scale_by(img, 0.22)
                self.sprite_parts[name] = img
            except Exception as e:
                print(f"Could not load sprite part {name}: {e}")
                self.sprite_parts[name] = None

    def get_dragons(self):
        if hasattr(self.world, "dragons"):
            return list(self.world.dragons)
        return list(self.world)

    def open_portrait(self):
        if self.selected_dragon:
            self.world.selected_portrait_dragon = self.selected_dragon
            self.change_screen("dragon_portrait")

    def draw_panel(self, screen, rect, alpha=185):
        surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        surf.fill((28, 28, 28, alpha))
        screen.blit(surf, rect.topleft)
        pygame.draw.rect(screen, (55, 55, 55), rect, width=1, border_radius=14)

    def get_dragon_by_id(self, dragon_id):
        return next((d for d in self.get_dragons() if d.id == dragon_id), None)

    def select_dragon(self, dragon):
        self.selected_dragon = dragon
        self.detail_scroll = 0

    def get_detail_text(self, d):
        if not d:
            return "No dragon selected."

        if ensure_dragon_flavor:
            ensure_dragon_flavor(d)

        bio = generate_dragon_bio(d, self.world) if generate_dragon_bio else "No biography available yet."
        legacy = generate_legacy_text(d, self.world) if generate_legacy_text and getattr(d, "status", "Alive") == "Dead" else ""

        friends = ", ".join(
            self.get_dragon_by_id(fid).name
            for fid in getattr(d, "friends", [])
            if self.get_dragon_by_id(fid)
        ) or "None"

        rivals = ", ".join(
            self.get_dragon_by_id(rid).name
            for rid in getattr(d, "rivals", [])
            if self.get_dragon_by_id(rid)
        ) or "None"

        titles = ", ".join(str(t) for t in getattr(d, "earned_titles", [])) or "None"
        hobbies = ", ".join(str(h) for h in getattr(d, "hobbies", [])) or "None"
        skills = ", ".join(str(s) for s in getattr(d, "skills", [])) or "None"
        scars = ", ".join(str(s) for s in getattr(d, "scars", [])) or "None"

        text = (
            "=== Archive Record ===\n"
            f"Name: {getattr(d, 'name', 'Unknown')}\n"
            f"Tribe: {getattr(d, 'tribe', 'Unknown')}\n"
            f"Age: {getattr(d, 'age_moons', getattr(d, 'age', 'Unknown'))}\n"
            f"Role: {getattr(d, 'role', 'Unknown')}\n"
            f"Rank: {getattr(d, 'rank', 'Unknown')}\n"
            f"Status: {getattr(d, 'status', 'Unknown')}\n"
            f"Health: {getattr(d, 'health', 'Unknown')}\n\n"

            "=== Visual Details ===\n"
            f"Height: {getattr(d, 'height', 'Unknown')}\n"
            f"Eye Color: {getattr(d, 'eye_color', 'Unknown')}\n"
            f"Horn Type: {getattr(d, 'horn_type', 'Unknown')}\n"
            f"Head Type: {getattr(d, 'head_type', 'Unknown')}\n"
            f"Snout Type: {getattr(d, 'snout_type', 'Unknown')}\n"
            f"Tail Type: {getattr(d, 'tail_type', 'Unknown')}\n"
            f"Wing Type: {getattr(d, 'wing_type', 'Unknown')}\n"
            f"Body Type: {getattr(d, 'body_type', 'Unknown')}\n"
            f"Markings: {getattr(d, 'marking_type', 'Unknown')}\n\n"

            "=== Life Details ===\n"
            f"Titles: {titles}\n"
            f"Skills: {skills}\n"
            f"Hobbies: {hobbies}\n"
            f"Scars: {scars}\n"
            f"Friends: {friends}\n"
            f"Rivals: {rivals}\n\n"

            "=== Biography ===\n"
            f"{bio}\n"
        )

        if legacy:
            text += f"\n=== Legacy ===\n{legacy}\n"

        return text

    def draw_library_text(self, screen, text, x, y):
        current_y = y

        for line in text.split("\n"):
            is_header = line.startswith("===")

            if is_header:
                line = line.replace("===", "").strip()
                font = self.section_font
                color = GOLD
                spacing = 34
            else:
                font = self.small
                color = TEXT
                spacing = 23

            self.draw_wrapped_text(screen, line, x, current_y, 520, font, color)
            current_y += spacing

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

    def draw_sprite_preview(self, screen, rect, dragon):
        self.draw_panel(screen, rect, alpha=130)

        self.draw_text(screen, "Sprite Preview", rect.x + 14, rect.y + 10, self.small, GOLD)

        if not dragon:
            self.draw_text(screen, "No dragon selected", rect.x + 14, rect.y + 50, self.small, MUTED)
            return

        cx = rect.centerx + 35
        cy = rect.centery + 10

        body_x = cx - 120
        body_y = cy - 20

        anchors = {
            "body": (body_x, body_y),
            "tail": (body_x + 115, body_y - 15),
            "feet": (body_x + 15, body_y + 36),
            "neck": (body_x + 8, body_y - 50),
            "head_open": (body_x + 1, body_y - 55),
            "wing_left": (body_x + 26, body_y - 51),
            "wing_right": (body_x + 30, body_y - 47),
        }

        draw_order = [
            "wing_left",
            "tail",
            "body",
            "feet",
            "neck",
            "head_open",
            "wing_right",
        ]

        tribe = getattr(dragon, "tribe", "Unknown")

        shadow_rect = pygame.Rect(cx - 150, cy + 63, 260, 22)
        shadow = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 100), shadow.get_rect())
        screen.blit(shadow, shadow_rect.topleft)

        for part_name in draw_order:
            x, y = anchors[part_name]
            img = self.sprite_parts.get(part_name)

            if not img:
                continue

            cache_key = (part_name, getattr(dragon, "id", 0), tribe)

            if cache_key not in self.recolor_cache:
                self.recolor_cache[cache_key] = self.recolor_surface(img, dragon)

            img = self.recolor_cache[cache_key]
            screen.blit(img, (x, y))

        self.draw_text(
            screen,
            f"{dragon.name} ({getattr(dragon, 'tribe', 'Unknown')})",
            rect.x + 14,
            rect.y + 36,
            self.small,
            TEXT
        )

    def draw(self, screen):
        self.buttons.clear()

        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill((18, 18, 18))

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 130))
        screen.blit(overlay, (0, 0))

        title = self.title_font.render("Scroll Library", True, TEXT)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 70)))

        library_dragons = [
            d for d in self.get_dragons()
            if getattr(d, "location", None) in [
                "scroll_library",
                "Scroll Library"
            ]
        ]

        self.draw_text(
            screen,
            "Present in Library:",
            55,
            40,
            self.small,
            GOLD
        )

        y = 60

        if not library_dragons:
            self.draw_text(
                screen,
                "No dragons here",
                55,
                y,
                self.small,
                MUTED
            )
        else:
            for d in library_dragons[:6]:
                self.draw_text(
                    screen,
                    f"{d.name} ({getattr(d, 'role', 'Unknown')})",
                    55,
                    y,
                    self.small,
                    MUTED
                )
                y += 18

            if len(library_dragons) > 6:
                self.draw_text(
                    screen,
                    f"+{len(library_dragons) - 6} more",
                    55,
                    y,
                    self.small,
                    MUTED
                )

        left = pygame.Rect(80, 130, 280, 500)
        right = pygame.Rect(390, 130, 530, 500)

        self.draw_panel(screen, left)
        self.draw_panel(screen, right)

        self.draw_text(screen, "Archives", left.x + 18, left.y + 16, self.section_font, GOLD)
        self.draw_text(screen, "Record", right.x + 18, right.y + 16, self.section_font, GOLD)

        sprite_rect = pygame.Rect(right.x + 18, right.y + 55, right.width - 36, 200)
        self.draw_sprite_preview(screen, sprite_rect, self.selected_dragon)

        portrait_btn = Button(
            (right.x + 350, right.y + 220, 130, 28),
            "View Portrait",
            self.open_portrait
        )
        self.buttons.append(portrait_btn)
        portrait_btn.draw(screen, self.small)

        roster_clip = pygame.Rect(left.x, left.y + 55, left.width, left.height - 65)

        old_clip = screen.get_clip()
        screen.set_clip(roster_clip)

        y = left.y + 60 + self.roster_scroll

        for d in self.get_dragons():
            btn = Button(
                (left.x + 18, y, 240, 34),
                f"{d.name} ({d.tribe})",
                lambda dragon=d: self.select_dragon(dragon)
            )
            self.buttons.append(btn)
            btn.draw(screen, self.small)

            if d == self.selected_dragon:
                pygame.draw.rect(
                    screen,
                    GOLD,
                    pygame.Rect(left.x + 14, y - 3, 248, 40),
                    width=2,
                    border_radius=8
                )

            y += 42

        screen.set_clip(old_clip)

        detail_rect = pygame.Rect(right.x + 18, right.y + 260, right.width - 36, right.height - 280)
        self.draw_panel(screen, detail_rect, alpha=150)

        old_clip = screen.get_clip()
        screen.set_clip(detail_rect)

        self.draw_library_text(
            screen,
            self.get_detail_text(self.selected_dragon),
            detail_rect.x + 12,
            detail_rect.y + 18 + self.detail_scroll
        )

        screen.set_clip(old_clip)

        return_btn = Button(
            (430, 645, 140, 38),
            "Return",
            lambda: self.change_screen("locations")
        )
        self.buttons.append(return_btn)
        return_btn.draw(screen, self.font)

    def update(self, dt):
        pass

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            mouse_x, mouse_y = pygame.mouse.get_pos()

            if mouse_x < 380:
                self.roster_scroll += event.y * 28
                self.roster_scroll = min(0, self.roster_scroll)

                max_scroll = max(0, len(self.get_dragons()) * 42 - 430)
                self.roster_scroll = max(-max_scroll, self.roster_scroll)

            else:
                self.detail_scroll += event.y * 25
                self.detail_scroll = min(0, self.detail_scroll)
                self.detail_scroll = max(-1600, self.detail_scroll)

        for button in self.buttons:
            button.handle_event(event)