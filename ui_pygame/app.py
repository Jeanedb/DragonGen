import pygame
from ui_pygame.screens.healer_den_poc import HealerDenScreen, create_test_world
from ui_pygame.screens.locations import LocationsScreen
from ui_pygame.screens.queen_palace import QueenPalaceScreen
from ui_pygame.screens.village_center import VillageCenterScreen
from ui_pygame.screens.dragon_profile import DragonProfileScreen
from ui_pygame.widgets.decision_popup import DecisionPopup
from core.sim.choices import resolve_choice

WIDTH, HEIGHT = 1000, 700
FPS = 60


class PygameApp:
    def __init__(self):
        pygame.init()

        self.decision_popup = None
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.game_surface = pygame.Surface((WIDTH, HEIGHT))
        pygame.display.set_caption("DragonGen - Pygame")

        self.clock = pygame.time.Clock()
        self.world = create_test_world()

        self.test_pending_choice = {
            "text": "Ashclaw is injured near the border. Mossglade hears rival dragons approaching. What should Mossglade do?",
            "options": [
                {
                    "id": "stay_help",
                    "text": "Stay and help Ashclaw",
                    "hint": "“No dragon deserves to be left behind.”"
                },
                {
                    "id": "run_for_help",
                    "text": "Run back to camp for help",
                    "hint": "“If both are lost, no one gets saved.”"
                },
                {
                    "id": "hide_wait",
                    "text": "Hide and wait for the rivals to pass",
                    "hint": "“Sometimes survival means silence.”"
                },
            ]
        }

        self.current_screen = LocationsScreen(self.world, self.change_screen)
        self.running = True

    def check_pending_choice(self):
        choice = getattr(self, "test_pending_choice", None)

        if choice and self.decision_popup is None:
            self.decision_popup = DecisionPopup(
                title="Decision",
                body=choice.get("text", "A choice must be made."),
                options=choice.get("options", []),
                on_choose=self.resolve_decision
            )

        elif not choice:
            self.decision_popup = None

    def resolve_decision(self, option_id):
        print(f"Chose option: {option_id}")
        self.test_pending_choice = None
        self.decision_popup = None

    def change_screen(self, screen_name):
        if screen_name == "locations":
            self.current_screen = LocationsScreen(self.world, self.change_screen)
        elif screen_name == "healer_den":
            self.current_screen = HealerDenScreen(self.world, self.change_screen)
        elif screen_name == "relations":
            self.current_screen = QueenPalaceScreen(self.world, self.change_screen)
        elif screen_name == "village":
            self.current_screen = VillageCenterScreen(self.world, self.change_screen)
        elif screen_name == "dragon_profile":
            self.current_screen = DragonProfileScreen(self.world, self.change_screen)

    def scale_surface_to_window(self):
        window_w, window_h = self.screen.get_size()
        scaled_surface = pygame.transform.smoothscale(
            self.game_surface,
            (window_w, window_h)
        )
        self.screen.blit(scaled_surface, (0, 0))

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if self.decision_popup:
                    self.decision_popup.handle_event(event)
                else:
                    self.current_screen.handle_event(event)

            self.current_screen.update(dt)
            self.check_pending_choice()
            self.current_screen.draw(self.game_surface)

            if self.decision_popup:
                self.decision_popup.draw(self.game_surface)

            self.scale_surface_to_window()
            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    app = PygameApp()
    app.run()