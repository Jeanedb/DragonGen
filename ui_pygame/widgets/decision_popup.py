import pygame
from ui_pygame.widgets.button import Button

WIDTH, HEIGHT = 1000, 700

TEXT = (230, 230, 230)
MUTED = (180, 180, 180)
GOLD = (242, 201, 76)


class DecisionPopup:
    def __init__(self, title, body, options, on_choose):
        self.title = title
        self.body = body
        self.options = options
        self.on_choose = on_choose
        self.buttons = []

        pygame.font.init()
        self.title_font = pygame.font.SysFont("arial", 24, bold=True)
        self.font = pygame.font.SysFont("arial", 16)
        self.small = pygame.font.SysFont("arial", 14)

    def draw_wrapped(self, screen, text, x, y, max_width, font, color):
        for paragraph in text.split("\n"):
            words = paragraph.split()
            line = ""

            for word in words:
                test = line + word + " "
                if font.size(test)[0] <= max_width:
                    line = test
                else:
                    img = font.render(line.strip(), True, color)
                    screen.blit(img, (x, y))
                    y += img.get_height() + 5
                    line = word + " "

            if line:
                img = font.render(line.strip(), True, color)
                screen.blit(img, (x, y))
                y += img.get_height() + 8

        return y

    def draw(self, screen):
        self.buttons.clear()

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))

        popup = pygame.Rect(250, 130, 500, 440)

        surface = pygame.Surface((popup.width, popup.height), pygame.SRCALPHA)
        surface.fill((28, 28, 28, 235))
        screen.blit(surface, popup.topleft)

        pygame.draw.rect(screen, (80, 80, 80), popup, width=2, border_radius=18)

        title_img = self.title_font.render(self.title, True, GOLD)
        screen.blit(title_img, (popup.x + 24, popup.y + 22))

        body_y = popup.y + 70
        body_y = self.draw_wrapped(
            screen,
            self.body,
            popup.x + 24,
            body_y,
            popup.width - 48,
            self.font,
            TEXT
        )

        y = max(body_y + 20, popup.y + 230)

        for option in self.options:
            btn = Button(
                (popup.x + 40, y, popup.width - 80, 42),
                option["text"],
                lambda oid=option["id"]: self.on_choose(oid)
            )
            self.buttons.append(btn)
            btn.draw(screen, self.small)

            hint = option.get("hint", "")
            if hint:
                hint_img = self.small.render(hint, True, (140, 140, 140))
                screen.blit(hint_img, (popup.x + 50, y + 45))
                y += 72
            else:
                y += 52

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)