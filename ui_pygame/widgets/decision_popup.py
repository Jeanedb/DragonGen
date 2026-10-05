"""Fantasy-styled modal used for every pending DragonGen decision.

This is a drop-in replacement for ui_pygame/widgets/decision_popup.py.
It deliberately keeps the original public interface used by app.py:

    DecisionPopup(title, body, options, on_choose, context=None)
    popup.handle_event(event)
    popup.draw(surface)

No simulation or choice-resolution code belongs in this widget.
"""

from __future__ import annotations

import pygame


# DragonGen's virtual canvas is 1000 x 700.  The popup also derives its
# placement from the surface passed to draw(), so it remains centred if that
# canvas changes later.
GOLD = (211, 157, 65)
PALE_GOLD = (244, 220, 164)
BRONZE = (119, 78, 38)
DEEP_BRONZE = (65, 41, 22)
INK = (25, 19, 15)
PANEL = (31, 25, 20)
PANEL_LIGHT = (46, 36, 28)
TEXT = (232, 220, 197)
MUTED_TEXT = (174, 158, 135)
SHADOW = (7, 5, 4)


def _chamfered_rect(rect: pygame.Rect, cut: int = 14):
    """Return points for an eight-sided, clipped-corner panel."""
    cut = max(0, min(cut, rect.width // 4, rect.height // 4))
    return [
        (rect.left + cut, rect.top),
        (rect.right - cut, rect.top),
        (rect.right, rect.top + cut),
        (rect.right, rect.bottom - cut),
        (rect.right - cut, rect.bottom),
        (rect.left + cut, rect.bottom),
        (rect.left, rect.bottom - cut),
        (rect.left, rect.top + cut),
    ]


def _draw_panel(surface, rect, fill, border, width=2, cut=14):
    points = _chamfered_rect(rect, cut)
    pygame.draw.polygon(surface, fill, points)
    pygame.draw.polygon(surface, border, points, width)


def _wrap_text(text: str, font: pygame.font.Font, max_width: int):
    """Pixel-aware word wrapping, including explicit newlines."""
    lines = []
    for paragraph in str(text).splitlines() or [""]:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue

        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def _fit_text(text: str, preferred_size: int, minimum_size: int, max_width: int):
    """Return a Georgia font that fits a one-line button label."""
    for size in range(preferred_size, minimum_size - 1, -1):
        font = pygame.font.SysFont("georgia", size, bold=True)
        if font.size(text)[0] <= max_width:
            return font
    return pygame.font.SysFont("georgia", minimum_size, bold=True)


def _context_text(item):
    if isinstance(item, dict):
        label = str(item.get("label", "")).strip()
        value = str(item.get("value", "")).strip()
        if label and value:
            return f"{label}: {value}"
        return label or value
    return str(item).strip()


class DecisionPopup:
    """Modal presentation layer for a pending choice.

    ``options`` is the existing DragonGen format::

        [{"id": "call_healer", "text": "Call a healer"}, ...]
    """

    def __init__(self, title, body, options, on_choose, context=None):
        self.title = str(title or "Decision")
        self.body = str(body or "A choice must be made.")
        self.options = list(options or [])
        self.context = list(context or [])
        self.on_choose = on_choose
        self.on_continue = None
        self.mode = "choice"

        self.hovered_index = None
        self.button_rects = []
        self._mouse_pos = (-1, -1)

        self.title_font = pygame.font.SysFont("georgia", 31, bold=True)
        self.kicker_font = pygame.font.SysFont("georgia", 13, bold=True)
        self.body_font = pygame.font.SysFont("georgia", 19)
        self.context_font = pygame.font.SysFont("georgia", 15)
        self.hint_font = pygame.font.SysFont("georgia", 13)

    @property
    def is_showing_result(self):
        return self.mode == "result"

    def show_result(self, body, on_continue=None):
        """Reuse the same modal to show the consequence of the decision."""
        self.mode = "result"
        self.title = "Decision Resolved"
        self.body = str(body or "The decision was carried out.")
        self.context = []
        self.options = [{"id": "continue", "text": "Continue"}]
        self.on_continue = on_continue
        self.hovered_index = None
        self.button_rects = []

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self._mouse_pos = event.pos
            self._update_hover(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._mouse_pos = event.pos
            self._update_hover(event.pos)
            if self.hovered_index is not None:
                self._choose(self.hovered_index)

        elif event.type == pygame.KEYDOWN:
            # Number keys provide a quiet accessibility shortcut without
            # adding more visual clutter to the modal.
            if pygame.K_1 <= event.key <= pygame.K_9:
                index = event.key - pygame.K_1
                if index < len(self.options):
                    self._choose(index)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.mode == "result":
                    self._choose(0)
                elif self.hovered_index is not None:
                    self._choose(self.hovered_index)

    def _update_hover(self, mouse_pos):
        self.hovered_index = next(
            (i for i, rect in enumerate(self.button_rects) if rect.collidepoint(mouse_pos)),
            None,
        )

    def _choose(self, index):
        if not (0 <= index < len(self.options)):
            return
        option = self.options[index]
        option_id = option.get("id") if isinstance(option, dict) else option
        if self.mode == "result":
            if callable(self.on_continue):
                self.on_continue()
        elif option_id is not None:
            self.on_choose(option_id)

    def draw(self, surface):
        width, height = surface.get_size()

        # Darken the underlying location without completely hiding it.  The
        # player can still see *where* the decision is taking place.
        veil = pygame.Surface((width, height), pygame.SRCALPHA)
        veil.fill((5, 3, 2, 188))
        surface.blit(veil, (0, 0))

        option_count = max(1, len(self.options))
        panel_w = min(720, width - 70)

        body_width = panel_w - 116
        body_lines = _wrap_text(self.body, self.body_font, body_width)
        max_body_lines = 9 if self.mode == "result" else 5
        if len(body_lines) > max_body_lines:
            body_lines = body_lines[:max_body_lines]
            last = body_lines[-1]
            while last and self.body_font.size(last + "...")[0] > body_width:
                last = last[:-1]
            body_lines[-1] = last.rstrip() + "..."

        body_height = max(1, len(body_lines)) * 27

        context_lines = []
        if self.mode == "choice":
            for item in self.context:
                text = _context_text(item)
                if text:
                    context_lines.extend(
                        _wrap_text(text, self.context_font, body_width - 28)
                    )
        max_context_lines = 5
        if len(context_lines) > max_context_lines:
            context_lines = context_lines[:max_context_lines]
            last = context_lines[-1]
            while last and self.context_font.size(last + "...")[0] > body_width - 28:
                last = last[:-1]
            context_lines[-1] = last.rstrip() + "..."

        context_height = 0
        if context_lines:
            context_height = 52 + len(context_lines) * 21

        button_h = 48
        gap = 12
        total_buttons_h = option_count * button_h + (option_count - 1) * gap
        panel_h = min(
            height - 54,
            max(360, 210 + body_height + context_height + total_buttons_h),
        )
        panel = pygame.Rect(0, 0, panel_w, panel_h)
        panel.center = (width // 2, height // 2)

        # A substantial shadow gives the modal physical separation from the
        # map/screen below it.
        shadow_rect = panel.move(8, 10)
        _draw_panel(surface, shadow_rect, SHADOW, SHADOW, 1, 18)
        _draw_panel(surface, panel, PANEL, DEEP_BRONZE, 5, 18)

        inner = panel.inflate(-12, -12)
        pygame.draw.polygon(surface, BRONZE, _chamfered_rect(inner, 14), 2)

        # Header plaque.
        header = pygame.Rect(panel.left + 34, panel.top + 24, panel.width - 68, 82)
        _draw_panel(surface, header, INK, BRONZE, 2, 12)
        pygame.draw.line(
            surface,
            GOLD,
            (header.left + 68, header.top + 13),
            (header.right - 68, header.top + 13),
            1,
        )

        kicker_text = (
            "THE CONSEQUENCES ARE NOW KNOWN"
            if self.mode == "result"
            else "A MATTER REQUIRES YOUR JUDGMENT"
        )
        kicker = self.kicker_font.render(kicker_text, True, MUTED_TEXT)
        surface.blit(kicker, kicker.get_rect(center=(header.centerx, header.top + 27)))

        title = self.title_font.render(self.title.upper(), True, PALE_GOLD)
        title_shadow = self.title_font.render(self.title.upper(), True, SHADOW)
        title_rect = title.get_rect(center=(header.centerx, header.top + 56))
        surface.blit(title_shadow, title_rect.move(2, 2))
        surface.blit(title, title_rect)

        # Small centre ornament under the header.
        diamond_y = header.bottom + 17
        pygame.draw.line(
            surface,
            DEEP_BRONZE,
            (panel.left + 60, diamond_y),
            (panel.right - 60, diamond_y),
            1,
        )
        pygame.draw.polygon(
            surface,
            GOLD,
            [
                (panel.centerx, diamond_y - 5),
                (panel.centerx + 5, diamond_y),
                (panel.centerx, diamond_y + 5),
                (panel.centerx - 5, diamond_y),
            ],
        )

        body_left = panel.left + 58
        body_top = diamond_y + 24

        for line_number, line in enumerate(body_lines):
            rendered = self.body_font.render(line, True, TEXT)
            surface.blit(rendered, (body_left, body_top + line_number * 27))

        if context_lines:
            context_rect = pygame.Rect(
                panel.left + 50,
                body_top + body_height + 10,
                panel.width - 100,
                context_height - 10,
            )
            _draw_panel(surface, context_rect, INK, DEEP_BRONZE, 2, 8)

            heading = self.kicker_font.render("KNOWN SITUATION", True, GOLD)
            surface.blit(heading, (context_rect.left + 14, context_rect.top + 10))

            for line_number, line in enumerate(context_lines):
                rendered = self.context_font.render(line, True, MUTED_TEXT)
                surface.blit(
                    rendered,
                    (
                        context_rect.left + 14,
                        context_rect.top + 31 + line_number * 21,
                    ),
                )

        # Choices occupy the lower portion of the plaque.  Keeping all buttons
        # the same width makes them read as deliberate actions instead of OS
        # dialogue controls.
        buttons_bottom = panel.bottom - 38
        buttons_top = buttons_bottom - total_buttons_h

        divider_y = buttons_top - 19
        pygame.draw.line(
            surface,
            BRONZE,
            (panel.left + 50, divider_y),
            (panel.right - 50, divider_y),
            1,
        )

        self.button_rects = []
        for index, option in enumerate(self.options):
            button = pygame.Rect(
                panel.left + 50,
                buttons_top + index * (button_h + gap),
                panel.width - 100,
                button_h,
            )
            self.button_rects.append(button)

        # Refresh hover after layout so the first visible frame is responsive.
        self._update_hover(self._mouse_pos)

        for index, (option, button) in enumerate(zip(self.options, self.button_rects)):
            hovered = index == self.hovered_index
            fill = (91, 55, 25) if hovered else PANEL_LIGHT
            border = GOLD if hovered else BRONZE
            _draw_panel(surface, button, fill, border, 3 if hovered else 2, 9)

            # Choice number medallions are useful while deciding, but the
            # single Continue action on an outcome needs no numerical label.
            if self.mode == "choice":
                medallion_center = (button.left + 25, button.centery)
                pygame.draw.circle(surface, INK, medallion_center, 15)
                pygame.draw.circle(surface, border, medallion_center, 15, 2)
                number = self.kicker_font.render(str(index + 1), True, PALE_GOLD)
                surface.blit(number, number.get_rect(center=medallion_center))

            label = option.get("text", option.get("label", "Choose")) if isinstance(option, dict) else str(option)
            font = _fit_text(label, 17, 13, button.width - 92)
            color = PALE_GOLD if hovered else TEXT
            rendered = font.render(label, True, color)
            label_offset = 8 if self.mode == "choice" else 0
            surface.blit(rendered, rendered.get_rect(center=(button.centerx + label_offset, button.centery)))

            if hovered:
                arrow_x = button.right - 25
                pygame.draw.polygon(
                    surface,
                    GOLD,
                    [
                        (arrow_x - 4, button.centery - 6),
                        (arrow_x + 4, button.centery),
                        (arrow_x - 4, button.centery + 6),
                    ],
                )
