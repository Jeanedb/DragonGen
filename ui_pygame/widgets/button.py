import pygame

TEXT = (230, 230, 230)
BLUE = (70, 130, 200)


class Button:
    def __init__(self, rect, text, callback, enabled=True):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.enabled = enabled

    def draw(self, screen, font):
        mouse = pygame.mouse.get_pos()
        hovered = self.rect.collidepoint(mouse)

        color = BLUE if self.enabled else (80, 80, 80)
        if hovered and self.enabled:
            color = (90, 150, 220)

        pygame.draw.rect(screen, color, self.rect, border_radius=8)

        label = font.render(self.text, True, TEXT)
        screen.blit(label, label.get_rect(center=self.rect.center))

    def handle_event(self, event):
        if not self.enabled:
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()