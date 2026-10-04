"""Native DragonGen save-slot browser used by saving and loading screens."""

import json
from datetime import datetime
from pathlib import Path

import pygame


WIDTH, HEIGHT = 1000, 700
SLOT_COUNT = 5

GOLD = (242, 201, 76)
PARCHMENT = (239, 220, 181)
MUTED = (173, 157, 132)
PANEL = (29, 23, 19)
ROW = (45, 36, 29)


class SaveSlotBrowser:
    """Five fixed save slots with native Pygame controls."""

    def __init__(self, project_root, mode, on_slot, on_cancel):
        if mode not in {"save", "load"}:
            raise ValueError("SaveSlotBrowser mode must be 'save' or 'load'.")

        self.mode = mode
        self.on_slot = on_slot
        self.on_cancel = on_cancel

        self.saves_dir = Path(project_root) / "saves"
        self.saves_dir.mkdir(parents=True, exist_ok=True)

        self.title_font = pygame.font.SysFont("georgia", 30, bold=True)
        self.heading_font = pygame.font.SysFont("georgia", 18, bold=True)
        self.body_font = pygame.font.SysFont("georgia", 15)
        self.small_font = pygame.font.SysFont("georgia", 13)
        self.button_font = pygame.font.SysFont("georgia", 13, bold=True)

        self.panel_rect = pygame.Rect(85, 35, 830, 630)
        self.row_rects = [
            pygame.Rect(125, 135 + index * 86, 750, 70)
            for index in range(SLOT_COUNT)
        ]
        self.action_rects = [
            pygame.Rect(715, row.y + 16, 125, 38)
            for row in self.row_rects
        ]
        self.delete_rects = [
            pygame.Rect(626, row.y + 16, 78, 38)
            for row in self.row_rects
        ]
        self.back_rect = pygame.Rect(410, 590, 180, 43)

        self.confirm_yes_rect = pygame.Rect(350, 407, 140, 42)
        self.confirm_no_rect = pygame.Rect(510, 407, 140, 42)

        self.pending_action = None
        self.status = ""
        self.slots = []
        self.refresh()

    def slot_path(self, slot_index):
        return self.saves_dir / f"slot_{slot_index + 1}.json"

    def refresh(self):
        self.slots = []

        for index in range(SLOT_COUNT):
            path = self.slot_path(index)
            entry = {
                "index": index,
                "path": path,
                "exists": path.exists(),
                "valid": False,
                "tribe": "EMPTY SLOT",
                "moon": 0,
                "dragons": 0,
                "modified": "",
            }

            if path.exists():
                try:
                    with path.open("r", encoding="utf-8") as save_file:
                        data = json.load(save_file)

                    entry["valid"] = True
                    entry["tribe"] = str(
                        data.get("tribe_name", "Unknown Tribe")
                    )
                    entry["moon"] = data.get("moon", 0)
                    entry["dragons"] = len(data.get("dragons", []))
                    entry["modified"] = datetime.fromtimestamp(
                        path.stat().st_mtime
                    ).strftime("%b %d, %Y  %I:%M %p")
                except Exception:
                    entry["tribe"] = "UNREADABLE SAVE"
                    entry["modified"] = "Delete this slot or overwrite it"

            self.slots.append(entry)

    def set_status(self, message):
        self.status = str(message)

    def perform_slot_action(self, slot_index):
        slot = self.slots[slot_index]

        if self.mode == "load" and not slot["valid"]:
            self.status = "That slot does not contain a valid saved game."
            return

        result = self.on_slot(slot["path"], slot_index + 1)
        if result is False and not self.status:
            self.status = "The operation could not be completed."

    def delete_slot(self, slot_index):
        path = self.slots[slot_index]["path"]
        try:
            path.unlink(missing_ok=True)
            self.status = f"Slot {slot_index + 1} was cleared."
        except Exception as error:
            print(f"Could not delete save slot: {error}")
            self.status = "That save slot could not be deleted."
        self.refresh()

    def handle_event(self, event, position_transform=None):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.pending_action:
                self.pending_action = None
            else:
                self.on_cancel()
            return True

        if event.type != pygame.MOUSEBUTTONUP or event.button != 1:
            return False

        mouse_pos = event.pos
        if position_transform:
            mouse_pos = position_transform(mouse_pos)

        if self.pending_action:
            if self.confirm_yes_rect.collidepoint(mouse_pos):
                action, slot_index = self.pending_action
                self.pending_action = None
                if action == "delete":
                    self.delete_slot(slot_index)
                else:
                    self.perform_slot_action(slot_index)
            elif self.confirm_no_rect.collidepoint(mouse_pos):
                self.pending_action = None
            return True

        if self.back_rect.collidepoint(mouse_pos):
            self.on_cancel()
            return True

        for index, slot in enumerate(self.slots):
            if self.delete_rects[index].collidepoint(mouse_pos) and slot["exists"]:
                self.pending_action = ("delete", index)
                self.status = ""
                return True

            if self.action_rects[index].collidepoint(mouse_pos):
                if self.mode == "save" and slot["exists"]:
                    self.pending_action = ("overwrite", index)
                    self.status = ""
                else:
                    self.perform_slot_action(index)
                return True

        return False

    def draw_button(self, surface, rect, label, mouse_pos, primary=False, enabled=True):
        hovered = enabled and rect.collidepoint(mouse_pos)
        shadow = rect.move(0, 4)
        pygame.draw.rect(surface, (9, 6, 4), shadow, border_radius=7)

        if not enabled:
            edge = (73, 66, 58)
            fill = (40, 37, 34)
            color = (104, 99, 91)
        elif primary:
            edge = GOLD if hovered else (184, 130, 62)
            fill = (116, 69, 28) if hovered else (83, 50, 24)
            color = (255, 232, 184)
        else:
            edge = (160, 113, 65) if hovered else (103, 77, 53)
            fill = (67, 51, 39) if hovered else (43, 35, 29)
            color = PARCHMENT

        pygame.draw.rect(surface, edge, rect, border_radius=7)
        pygame.draw.rect(surface, fill, rect.inflate(-5, -5), border_radius=5)
        label_image = self.button_font.render(label, True, color)
        surface.blit(label_image, label_image.get_rect(center=rect.center))

    def draw_confirmation(self, surface, mouse_pos):
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((4, 3, 2, 195))
        surface.blit(shade, (0, 0))

        action, slot_index = self.pending_action
        panel = pygame.Rect(260, 245, 480, 230)
        pygame.draw.rect(surface, (151, 103, 54), panel, border_radius=12)
        pygame.draw.rect(surface, PANEL, panel.inflate(-7, -7), border_radius=9)

        verb = "DELETE" if action == "delete" else "OVERWRITE"
        title = self.heading_font.render(
            f"{verb} SLOT {slot_index + 1}?",
            True,
            (246, 216, 158),
        )
        surface.blit(title, title.get_rect(center=(500, 300)))

        body_text = (
            "This saved game will be permanently removed."
            if action == "delete"
            else "The existing saved game in this slot will be replaced."
        )
        body = self.body_font.render(body_text, True, PARCHMENT)
        surface.blit(body, body.get_rect(center=(500, 350)))

        self.draw_button(
            surface,
            self.confirm_yes_rect,
            verb,
            mouse_pos,
            primary=True,
        )
        self.draw_button(
            surface,
            self.confirm_no_rect,
            "CANCEL",
            mouse_pos,
        )

    def draw(self, surface, mouse_pos=None):
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()

        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((6, 4, 3, 170))
        surface.blit(shade, (0, 0))

        shadow = self.panel_rect.move(0, 7)
        pygame.draw.rect(surface, (8, 5, 4), shadow, border_radius=16)
        pygame.draw.rect(surface, (128, 89, 50), self.panel_rect, border_radius=16)
        pygame.draw.rect(surface, PANEL, self.panel_rect.inflate(-7, -7), border_radius=12)

        title_text = "SAVE GAME" if self.mode == "save" else "LOAD GAME"
        subtitle_text = (
            "Choose a slot for the current tribe."
            if self.mode == "save"
            else "Choose a tribe to continue."
        )

        title = self.title_font.render(title_text, True, (246, 216, 158))
        surface.blit(title, title.get_rect(center=(500, 70)))
        subtitle = self.body_font.render(subtitle_text, True, MUTED)
        surface.blit(subtitle, subtitle.get_rect(center=(500, 103)))

        for index, slot in enumerate(self.slots):
            row = self.row_rects[index]
            hovered = row.collidepoint(mouse_pos)
            fill = (55, 43, 33) if hovered else ROW
            edge = (151, 106, 59) if hovered else (91, 70, 51)
            pygame.draw.rect(surface, edge, row, border_radius=9)
            pygame.draw.rect(surface, fill, row.inflate(-4, -4), border_radius=7)

            slot_label = self.heading_font.render(
                f"SLOT {index + 1}",
                True,
                (229, 193, 126),
            )
            surface.blit(slot_label, (row.x + 18, row.y + 13))

            if slot["exists"]:
                tribe = self.body_font.render(slot["tribe"].upper(), True, PARCHMENT)
                surface.blit(tribe, (row.x + 135, row.y + 10))

                if slot["valid"]:
                    details = (
                        f"Moon {slot['moon']}  •  {slot['dragons']} dragons  •  "
                        f"{slot['modified']}"
                    )
                else:
                    details = slot["modified"]
                detail_image = self.small_font.render(details, True, MUTED)
                surface.blit(detail_image, (row.x + 135, row.y + 39))
            else:
                empty = self.body_font.render("EMPTY", True, (130, 119, 102))
                surface.blit(empty, (row.x + 135, row.y + 25))

            self.draw_button(
                surface,
                self.delete_rects[index],
                "DELETE",
                mouse_pos,
                enabled=slot["exists"],
            )

            if self.mode == "save":
                action_label = "OVERWRITE" if slot["exists"] else "SAVE"
                enabled = True
            else:
                action_label = "LOAD"
                enabled = slot["valid"]

            self.draw_button(
                surface,
                self.action_rects[index],
                action_label,
                mouse_pos,
                primary=True,
                enabled=enabled,
            )

        if self.status:
            status = self.small_font.render(self.status, True, (222, 153, 111))
            surface.blit(status, status.get_rect(center=(500, 574)))

        self.draw_button(surface, self.back_rect, "BACK", mouse_pos)

        if self.pending_action:
            self.draw_confirmation(surface, mouse_pos)
