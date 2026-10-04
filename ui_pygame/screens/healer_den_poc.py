import pygame
from dataclasses import dataclass
import sys
from pathlib import Path

from ui_pygame.core.base_screen import BaseScreen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

WIDTH, HEIGHT = 1000, 700
FPS = 60

TEXT = (236, 222, 196)
MUTED = (175, 158, 132)
GOLD = (227, 183, 84)
BRONZE = (133, 91, 53)
GREEN = (112, 178, 120)
RED = (205, 82, 66)
CREAM = (248, 230, 192)


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


class DenButton(ClickTarget):
    def __init__(self, rect, label, callback, emphasis=False, enabled=True):
        super().__init__(rect, callback)
        self.label = label
        self.emphasis = emphasis
        self.enabled = enabled

    def handle_event(self, event):
        if self.enabled:
            super().handle_event(event)

    def draw(self, screen, font, mouse_pos):
        hovered = self.enabled and self.rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (8, 5, 4), self.rect.move(0, 4), border_radius=8)
        if not self.enabled:
            edge, fill, text_color = (78, 70, 61), (43, 40, 36), (120, 113, 101)
        elif self.emphasis:
            edge = GOLD if hovered else (177, 121, 53)
            fill = (102, 61, 29) if hovered else (73, 47, 29)
            text_color = CREAM
        else:
            edge = GOLD if hovered else (111, 80, 55)
            fill = (64, 48, 36) if hovered else (43, 36, 32)
            text_color = TEXT

        pygame.draw.rect(screen, edge, self.rect, border_radius=8)
        inner = self.rect.inflate(-5, -5)
        pygame.draw.rect(screen, fill, inner, border_radius=6)
        pygame.draw.line(
            screen,
            (213, 167, 94) if self.enabled else (76, 70, 62),
            (inner.left + 8, inner.top + 3),
            (inner.right - 8, inner.top + 3),
            1,
        )
        image = font.render(self.label, True, text_color)
        screen.blit(image, image.get_rect(center=self.rect.center))


class HealerDenScreen(BaseScreen):
    def __init__(self, world, change_screen=None):
        super().__init__()
        self.world = world
        self.change_screen = change_screen
        self.popup_dragon = None
        self.selected_patient_id = None
        self.scroll_left = 0
        self.scroll_right = 0
        self.popup_scroll = 0

        self.fantasy_title = pygame.font.SysFont("georgia", 30, bold=True)
        self.fantasy_heading = pygame.font.SysFont("georgia", 18, bold=True)
        self.fantasy_body = pygame.font.SysFont("georgia", 14)
        self.fantasy_body_bold = pygame.font.SysFont("georgia", 14, bold=True)
        self.fantasy_small = pygame.font.SysFont("georgia", 12)
        self.fantasy_tiny = pygame.font.SysFont("georgia", 11)
        self.medallion_font = pygame.font.SysFont("georgia", 18, bold=True)

        tribe_slug = (
            str(getattr(self.world, "tribe_name", ""))
            .lower()
            .replace(" tribe", "")
            .replace(" ", "")
        )
        tribe_bg = PROJECT_ROOT / "assets" / tribe_slug / "healer_den_bg.png"
        default_bg = PROJECT_ROOT / "assets" / "menu" / "healer_bg.png"
        bg_path = tribe_bg if tribe_bg.exists() else default_bg
        try:
            self.bg_image = pygame.image.load(str(bg_path)).convert()
            self.bg_image = pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT))
        except Exception as error:
            print(f"Could not load healer background: {error}")
            self.bg_image = None

    def update(self, dt):
        pass

    def get_dragons(self):
        return self.world.dragons if hasattr(self.world, "dragons") else self.world

    def get_injured_dragons(self):
        return [
            dragon for dragon in self.get_dragons()
            if getattr(dragon, "status", None) == "Alive"
            and getattr(dragon, "health", "Healthy") != "Healthy"
        ]

    def get_healers(self):
        return [
            dragon for dragon in self.get_dragons()
            if getattr(dragon, "status", None) == "Alive"
            and getattr(dragon, "role", None) == "Healer"
        ]

    def get_dragon_by_id(self, dragon_id):
        return next((dragon for dragon in self.get_dragons() if dragon.id == dragon_id), None)

    def get_patient_count(self, healer):
        return sum(
            1 for dragon in self.get_dragons()
            if getattr(dragon, "assigned_healer_id", None) == healer.id
        )

    def get_selected_patient(self):
        injured = self.get_injured_dragons()
        injured_ids = {dragon.id for dragon in injured}
        if self.selected_patient_id not in injured_ids:
            self.selected_patient_id = injured[0].id if injured else None
        return self.get_dragon_by_id(self.selected_patient_id)

    def get_present_dragons(self):
        return [
            dragon for dragon in self.get_dragons()
            if getattr(dragon, "location", None) in ("healer_den", "Healer's Den")
        ]

    def select_patient(self, dragon):
        self.selected_patient_id = dragon.id

    def assign_healer(self, injured_dragon, healer):
        injured_dragon.assigned_healer_id = healer.id
        self.popup_dragon = None
        self.popup_scroll = 0

    def open_popup(self, dragon):
        self.popup_dragon = dragon
        self.popup_scroll = 0

    def clamp_scrolls(self):
        left_content = len(self.get_injured_dragons()) * 84
        right_content = len(self.get_healers()) * 96
        popup_content = len(self.get_healers()) * 58
        self.scroll_left = max(min(0, 363 - left_content), min(0, self.scroll_left))
        self.scroll_right = max(min(0, 363 - right_content), min(0, self.scroll_right))
        self.popup_scroll = max(min(0, 260 - popup_content), min(0, self.popup_scroll))

    def draw_beveled_panel(self, screen, rect, fill=(28, 23, 20, 220), edge=BRONZE, cut=12):
        rect = pygame.Rect(rect)
        x, y, width, height = rect
        points = [
            (x + cut, y), (x + width - cut, y), (x + width, y + cut),
            (x + width, y + height - cut), (x + width - cut, y + height),
            (x + cut, y + height), (x, y + height - cut), (x, y + cut),
        ]
        pygame.draw.polygon(screen, (8, 5, 4), [(px, py + 5) for px, py in points])
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        local_points = [(px - x, py - y) for px, py in points]
        pygame.draw.polygon(panel, fill, local_points)
        screen.blit(panel, rect.topleft)
        pygame.draw.lines(screen, edge, True, points, 2)
        pygame.draw.line(
            screen, (208, 163, 94),
            (x + cut + 8, y + 5), (x + width - cut - 8, y + 5), 1,
        )

    def draw_medallion(self, screen, center, label, color, selected=False, radius=23):
        x, y = center
        pygame.draw.circle(screen, (8, 5, 4), (x, y + 3), radius + 5)
        pygame.draw.circle(screen, GOLD if selected else (112, 81, 55), center, radius + 4)
        pygame.draw.circle(screen, (32, 27, 24), center, radius)
        pygame.draw.circle(screen, color, center, radius - 5)
        pygame.draw.arc(
            screen, tuple(min(255, channel + 40) for channel in color),
            (x - radius + 8, y - radius + 8, (radius - 8) * 2, (radius - 8) * 2),
            0.55, 2.5, 2,
        )
        image = self.medallion_font.render(label, True, CREAM)
        screen.blit(image, image.get_rect(center=center))

    def draw_scroll_track(self, screen, rect, scroll, content_height, visible_height):
        if content_height <= visible_height:
            return
        pygame.draw.line(screen, (91, 66, 48), rect.midtop, rect.midbottom, 2)
        max_scroll = content_height - visible_height
        ratio = min(1.0, -scroll / max_scroll) if max_scroll else 0
        y = rect.top + int(ratio * rect.height)
        pygame.draw.circle(screen, GOLD, (rect.centerx, y), 4)

    def draw_patient_roster(self, screen, rect, mouse_pos):
        self.draw_beveled_panel(screen, rect, fill=(27, 23, 21, 226), edge=(111, 76, 50), cut=12)
        injured = self.get_injured_dragons()
        screen.blit(self.fantasy_heading.render("PATIENT WARD", True, GOLD), (rect.x + 16, rect.y + 15))
        screen.blit(self.fantasy_small.render(f"{len(injured)} requiring care", True, MUTED), (rect.x + 16, rect.y + 42))
        pygame.draw.line(screen, (112, 78, 51), (rect.x + 16, rect.y + 66), (rect.right - 16, rect.y + 66), 1)

        area = pygame.Rect(rect.x + 12, rect.y + 76, rect.width - 24, rect.height - 92)
        screen.set_clip(area)
        if not injured:
            screen.blit(self.fantasy_body.render("The ward is quiet.", True, TEXT), (area.x + 10, area.y + 18))
            screen.blit(self.fantasy_small.render("No dragons are injured.", True, GREEN), (area.x + 10, area.y + 44))
        else:
            y = area.y + self.scroll_left
            for dragon in injured:
                row = pygame.Rect(area.x, y, area.width - 5, 74)
                selected = dragon.id == self.selected_patient_id
                hovered = row.collidepoint(mouse_pos)
                fill = (77, 49, 34) if selected else (52, 41, 35) if hovered else (37, 32, 29)
                edge = GOLD if selected else (128, 82, 52) if hovered else (78, 60, 48)
                pygame.draw.rect(screen, fill, row, border_radius=8)
                pygame.draw.rect(screen, edge, row, width=2, border_radius=8)
                self.draw_medallion(screen, (row.x + 31, row.centery), "!", (139, 53, 43), selected, 18)
                assigned = self.get_dragon_by_id(getattr(dragon, "assigned_healer_id", None))
                care_text = f"Healer: {assigned.name}" if assigned else "Awaiting a healer"
                care_color = GREEN if assigned else GOLD
                screen.blit(self.fantasy_body_bold.render(str(dragon.name), True, CREAM), (row.x + 59, row.y + 10))
                screen.blit(self.fantasy_small.render(str(dragon.health), True, RED), (row.x + 59, row.y + 31))
                screen.blit(self.fantasy_tiny.render(care_text, True, care_color), (row.x + 59, row.y + 50))
                if row.colliderect(area):
                    self.buttons.append(ClickTarget(row, lambda patient=dragon: self.select_patient(patient)))
                y += 84
        screen.set_clip(None)
        self.draw_scroll_track(
            screen, pygame.Rect(rect.right - 10, area.y + 4, 2, area.height - 8),
            self.scroll_left, len(injured) * 84, area.height,
        )

    def draw_patient_chart(self, screen, rect, mouse_pos):
        self.draw_beveled_panel(screen, rect, fill=(29, 24, 21, 232), edge=(124, 85, 51), cut=13)
        patient = self.get_selected_patient()
        screen.blit(self.fantasy_small.render("TREATMENT CHART", True, GOLD), (rect.x + 20, rect.y + 17))
        pygame.draw.line(screen, (118, 81, 50), (rect.x + 20, rect.y + 42), (rect.right - 20, rect.y + 42), 1)
        if not patient:
            title = self.fantasy_heading.render("NO ACTIVE PATIENT", True, GREEN)
            screen.blit(title, title.get_rect(center=(rect.centerx, rect.y + 128)))
            body = self.fantasy_body.render("All injured dragons have recovered.", True, MUTED)
            screen.blit(body, body.get_rect(center=(rect.centerx, rect.y + 162)))
            return

        assigned = self.get_dragon_by_id(getattr(patient, "assigned_healer_id", None))
        self.draw_medallion(screen, (rect.x + 53, rect.y + 86), "!", (139, 53, 43), True, 25)
        screen.blit(self.fantasy_heading.render(str(patient.name).upper(), True, CREAM), (rect.x + 92, rect.y + 60))
        screen.blit(self.fantasy_body.render(str(patient.health), True, RED), (rect.x + 92, rect.y + 88))

        status_text = "UNDER TREATMENT" if assigned else "CARE NEEDED"
        status_color = GREEN if assigned else GOLD
        status_box = pygame.Rect(rect.right - 139, rect.y + 64, 118, 31)
        pygame.draw.rect(screen, (31, 29, 25), status_box, border_radius=15)
        pygame.draw.rect(screen, status_color, status_box, width=2, border_radius=15)
        status_image = self.fantasy_tiny.render(status_text, True, status_color)
        screen.blit(status_image, status_image.get_rect(center=status_box.center))

        fields = [
            ("TRIBE", str(patient.tribe)),
            ("ROLE", str(patient.role)),
            ("INJURED FOR", f"{patient.injury_duration} moons"),
            ("LOCATION", str(patient.location).replace("_", " ").title()),
        ]
        start_x, start_y, field_width = rect.x + 20, rect.y + 133, 174
        for index, (label, value) in enumerate(fields):
            column, row_number = index % 2, index // 2
            field = pygame.Rect(start_x + column * 184, start_y + row_number * 68, field_width, 57)
            pygame.draw.rect(screen, (37, 31, 28), field, border_radius=7)
            pygame.draw.rect(screen, (78, 59, 45), field, width=1, border_radius=7)
            screen.blit(self.fantasy_tiny.render(label, True, GOLD), (field.x + 10, field.y + 8))
            screen.blit(self.fantasy_body.render(value, True, TEXT), (field.x + 10, field.y + 28))

        care_box = pygame.Rect(rect.x + 20, rect.y + 281, rect.width - 40, 91)
        pygame.draw.rect(screen, (35, 30, 27), care_box, border_radius=8)
        pygame.draw.rect(screen, (95, 70, 49), care_box, width=1, border_radius=8)
        screen.blit(self.fantasy_tiny.render("ASSIGNED CARE", True, GOLD), (care_box.x + 12, care_box.y + 10))
        if assigned:
            self.draw_medallion(screen, (care_box.x + 38, care_box.y + 55), "H", (63, 112, 76), False, 17)
            screen.blit(self.fantasy_body_bold.render(str(assigned.name), True, CREAM), (care_box.x + 68, care_box.y + 38))
            skill = getattr(assigned, "healer_skill", 1.0)
            detail = self.fantasy_small.render(f"Healer skill {skill:.2f}  •  treatment underway", True, GREEN)
            screen.blit(detail, (care_box.x + 68, care_box.y + 60))
        else:
            screen.blit(self.fantasy_body_bold.render("No healer assigned", True, GOLD), (care_box.x + 13, care_box.y + 36))
            screen.blit(self.fantasy_small.render("Assign a healer to begin dedicated care.", True, MUTED), (care_box.x + 13, care_box.y + 59))

        assign_button = DenButton(
            (rect.x + 76, rect.bottom - 62, rect.width - 152, 42),
            "CARE ASSIGNED" if assigned else "ASSIGN A HEALER",
            lambda selected=patient: self.open_popup(selected),
            emphasis=not assigned,
            enabled=assigned is None,
        )
        self.buttons.append(assign_button)
        assign_button.draw(screen, self.fantasy_body_bold, mouse_pos)

    def draw_healer_roster(self, screen, rect, mouse_pos):
        self.draw_beveled_panel(screen, rect, fill=(27, 23, 21, 226), edge=(111, 76, 50), cut=12)
        healers = self.get_healers()
        screen.blit(self.fantasy_heading.render("DEN HEALERS", True, GREEN), (rect.x + 16, rect.y + 15))
        screen.blit(self.fantasy_small.render(f"{len(healers)} on the roster", True, MUTED), (rect.x + 16, rect.y + 42))
        pygame.draw.line(screen, (112, 78, 51), (rect.x + 16, rect.y + 66), (rect.right - 16, rect.y + 66), 1)

        area = pygame.Rect(rect.x + 12, rect.y + 76, rect.width - 24, rect.height - 92)
        screen.set_clip(area)
        if not healers:
            screen.blit(self.fantasy_body.render("No healers available.", True, MUTED), (area.x + 10, area.y + 18))
        else:
            y = area.y + self.scroll_right
            for healer in healers:
                row = pygame.Rect(area.x, y, area.width - 5, 86)
                patients = self.get_patient_count(healer)
                full = patients >= 2
                pygame.draw.rect(screen, (37, 32, 29), row, border_radius=8)
                pygame.draw.rect(screen, (78, 60, 48), row, width=1, border_radius=8)
                self.draw_medallion(screen, (row.x + 30, row.y + 31), "H", (58, 111, 74), False, 18)
                screen.blit(self.fantasy_body_bold.render(str(healer.name), True, CREAM), (row.x + 57, row.y + 10))
                meta = self.fantasy_tiny.render(
                    f"{healer.tribe}  •  Skill {getattr(healer, 'healer_skill', 1.0):.2f}", True, MUTED,
                )
                screen.blit(meta, (row.x + 57, row.y + 31))
                load_color = RED if full else GREEN
                screen.blit(self.fantasy_tiny.render(f"PATIENTS  {patients}/2", True, load_color), (row.x + 12, row.y + 59))
                bar = pygame.Rect(row.x + 102, row.y + 62, row.width - 116, 8)
                pygame.draw.rect(screen, (22, 19, 17), bar, border_radius=4)
                fill_width = int(bar.width * min(2, patients) / 2)
                if fill_width:
                    pygame.draw.rect(screen, load_color, (bar.x, bar.y, fill_width, bar.height), border_radius=4)
                y += 96
        screen.set_clip(None)
        self.draw_scroll_track(
            screen, pygame.Rect(rect.right - 10, area.y + 4, 2, area.height - 8),
            self.scroll_right, len(healers) * 96, area.height,
        )

    def draw_present_strip(self, screen, rect):
        self.draw_beveled_panel(screen, rect, fill=(27, 22, 19, 230), edge=(111, 76, 50), cut=10)
        present = self.get_present_dragons()
        screen.blit(self.fantasy_small.render("PRESENT IN THE DEN", True, GOLD), (rect.x + 18, rect.y + 13))
        if present:
            names = "  •  ".join(
                f"{dragon.name} ({getattr(dragon, 'role', 'Unknown')})" for dragon in present[:6]
            )
            if len(present) > 6:
                names += f"  •  +{len(present) - 6} more"
            image = self.fantasy_body.render(names, True, TEXT)
        else:
            image = self.fantasy_body.render("The den is presently empty.", True, MUTED)
        screen.blit(image, (rect.x + 18, rect.y + 36))

    def draw(self, screen):
        self.buttons.clear()
        self.get_selected_patient()
        self.clamp_scrolls()
        mouse_pos = scale_mouse_pos(pygame.mouse.get_pos(), pygame.display.get_surface().get_size())
        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill((18, 14, 12))

        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((10, 7, 5, 76))
        screen.blit(veil, (0, 0))
        pygame.draw.rect(screen, (111, 75, 45), (18, 16, 964, 668), width=3, border_radius=18)
        pygame.draw.rect(screen, (38, 28, 25), (25, 23, 950, 654), width=2, border_radius=15)

        self.draw_beveled_panel(screen, (250, 18, 500, 76), fill=(30, 24, 20, 240), edge=(145, 95, 52), cut=15)
        title = self.fantasy_title.render("HEALER'S DEN", True, CREAM)
        screen.blit(title, title.get_rect(center=(500, 45)))
        subtitle = self.fantasy_small.render("Triage, treatment, and the recovery of the tribe", True, MUTED)
        screen.blit(subtitle, subtitle.get_rect(center=(500, 72)))

        return_button = DenButton(
            (823, 32, 130, 42), "RETURN",
            lambda: self.change_screen("locations") if self.change_screen else pygame.event.post(pygame.event.Event(pygame.QUIT)),
        )
        self.buttons.append(return_button)
        return_button.draw(screen, self.fantasy_body, mouse_pos)
        self.draw_patient_roster(screen, pygame.Rect(35, 112, 250, 455), mouse_pos)
        self.draw_patient_chart(screen, pygame.Rect(300, 112, 400, 455), mouse_pos)
        self.draw_healer_roster(screen, pygame.Rect(715, 112, 250, 455), mouse_pos)
        self.draw_present_strip(screen, pygame.Rect(35, 580, 930, 72))
        if self.popup_dragon:
            self.draw_popup(screen, mouse_pos)

    def draw_popup(self, screen, mouse_pos):
        self.buttons.clear()
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((7, 4, 3, 190))
        screen.blit(overlay, (0, 0))
        popup = pygame.Rect(255, 103, 490, 494)
        self.draw_beveled_panel(screen, popup, fill=(30, 24, 21, 250), edge=(171, 113, 57), cut=16)

        title = self.fantasy_heading.render("ASSIGN A HEALER", True, CREAM)
        screen.blit(title, title.get_rect(center=(popup.centerx, popup.y + 35)))
        patient_line = self.fantasy_body.render(f"Choose dedicated care for {self.popup_dragon.name}", True, MUTED)
        screen.blit(patient_line, patient_line.get_rect(center=(popup.centerx, popup.y + 65)))
        pygame.draw.line(screen, (125, 84, 50), (popup.x + 28, popup.y + 87), (popup.right - 28, popup.y + 87), 1)

        healers = [healer for healer in self.get_healers() if healer.id != self.popup_dragon.id]
        area = pygame.Rect(popup.x + 28, popup.y + 101, popup.width - 56, 260)
        screen.set_clip(area)
        if not healers:
            screen.blit(self.fantasy_body.render("No healers are available.", True, MUTED), (area.x + 15, area.y + 20))
        else:
            y = area.y + self.popup_scroll
            for healer in healers:
                patients = self.get_patient_count(healer)
                full = patients >= 2
                row = pygame.Rect(area.x, y, area.width - 6, 50)
                pygame.draw.rect(screen, (39, 33, 29), row, border_radius=7)
                pygame.draw.rect(screen, (83, 62, 46), row, width=1, border_radius=7)
                screen.blit(self.fantasy_body_bold.render(str(healer.name), True, CREAM), (row.x + 12, row.y + 8))
                details = self.fantasy_tiny.render(
                    f"{healer.tribe}  •  Skill {getattr(healer, 'healer_skill', 1.0):.2f}  •  {patients}/2 patients",
                    True, RED if full else MUTED,
                )
                screen.blit(details, (row.x + 12, row.y + 29))
                choose = DenButton(
                    (row.right - 104, row.y + 8, 94, 34), "FULL" if full else "ASSIGN",
                    lambda selected_healer=healer: self.assign_healer(self.popup_dragon, selected_healer),
                    emphasis=not full, enabled=not full,
                )
                if row.colliderect(area):
                    self.buttons.append(choose)
                    choose.draw(screen, self.fantasy_tiny, mouse_pos)
                y += 58
        screen.set_clip(None)
        self.draw_scroll_track(
            screen, pygame.Rect(area.right - 1, area.y + 4, 2, area.height - 8),
            self.popup_scroll, len(healers) * 58, area.height,
        )
        note = self.fantasy_small.render("Each healer can care for up to two patients.", True, MUTED)
        screen.blit(note, note.get_rect(center=(popup.centerx, popup.y + 390)))
        cancel = DenButton(
            (popup.centerx - 75, popup.bottom - 63, 150, 40), "CANCEL",
            lambda: setattr(self, "popup_dragon", None),
        )
        self.buttons.append(cancel)
        cancel.draw(screen, self.fantasy_body, mouse_pos)

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            mouse_x, mouse_y = scale_mouse_pos(
                pygame.mouse.get_pos(), pygame.display.get_surface().get_size(),
            )
            if self.popup_dragon:
                if pygame.Rect(283, 204, 434, 260).collidepoint(mouse_x, mouse_y):
                    self.popup_scroll += event.y * 30
            elif pygame.Rect(35, 112, 250, 455).collidepoint(mouse_x, mouse_y):
                self.scroll_left += event.y * 30
            elif pygame.Rect(715, 112, 250, 455).collidepoint(mouse_x, mouse_y):
                self.scroll_right += event.y * 30
            self.clamp_scrolls()

        if event.type == pygame.MOUSEBUTTONDOWN:
            scaled_pos = scale_mouse_pos(event.pos, pygame.display.get_surface().get_size())
            scaled_event = pygame.event.Event(event.type, {"pos": scaled_pos, "button": event.button})
            for button in list(self.buttons):
                button.handle_event(scaled_event)
        else:
            for button in list(self.buttons):
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
    window_width, window_height = window_size
    return int(mouse_x * WIDTH / window_width), int(mouse_y * HEIGHT / window_height)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    game_surface = pygame.Surface((WIDTH, HEIGHT))
    pygame.display.set_caption("DragonGen - Healer's Den Pygame POC")
    clock = pygame.time.Clock()
    healer_screen = HealerDenScreen(create_test_world())
    running = True
    while running:
        dt = clock.tick(FPS) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            healer_screen.handle_event(event)
        healer_screen.update(dt)
        healer_screen.draw(game_surface)
        screen.blit(pygame.transform.smoothscale(game_surface, screen.get_size()), (0, 0))
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    main()
