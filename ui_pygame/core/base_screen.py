import pygame

TEXT = (230, 230, 230)


class BaseScreen:
    def __init__(self):
        self.buttons = []

        pygame.font.init()
        self.font = pygame.font.SysFont("arial", 18)
        self.small = pygame.font.SysFont("arial", 15)
        self.title_font = pygame.font.SysFont("arial", 34, bold=True)
        self.section_font = pygame.font.SysFont("arial", 22, bold=True)

    def update(self, dt):
        pass

    def draw_text(self, screen, text, x, y, font=None, color=TEXT):
        font = font or self.small

        for line in text.split("\n"):
            img = font.render(line, True, color)
            screen.blit(img, (x, y))
            y += img.get_height() + 4

        return y

    def handle_button_events(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def draw_wrapped_text(self, screen, text, x, y, max_width, font=None, color=TEXT, line_gap=4):
        font = font or self.small

        for paragraph in text.split("\n"):
            words = paragraph.split(" ")
            line = ""

            for word in words:
                test_line = line + word + " "
                if font.size(test_line)[0] <= max_width:
                    line = test_line
                else:
                    img = font.render(line.strip(), True, color)
                    screen.blit(img, (x, y))
                    y += img.get_height() + line_gap
                    line = word + " "

            if line:
                img = font.render(line.strip(), True, color)
                screen.blit(img, (x, y))
                y += img.get_height() + line_gap

            y += line_gap

        return y