import pygame
from ui_pygame.screens.healer_den_poc import HealerDenScreen
from core.generator import generate_starting_world
from core.sim.locations import initialize_dragon_locations
from core.sim.flavor import ensure_dragon_flavor
from core.sim.leadership import maintain_hierarchy
from ui_pygame.screens.locations import LocationsScreen
from ui_pygame.screens.queen_palace import QueenPalaceScreen
from ui_pygame.screens.village_center import VillageCenterScreen
from ui_pygame.screens.dragon_profile import DragonProfileScreen
from ui_pygame.widgets.decision_popup import DecisionPopup
from core.sim.choices import resolve_choice
from ui_pygame.screens.world_dashboard import WorldDashboardScreen
from ui_pygame.screens.scroll_library import ScrollLibraryScreen
from ui_pygame.screens.dragon_portrait import DragonPortraitScreen


WIDTH, HEIGHT = 1000, 700
FPS = 60


class PygameApp:
    def __init__(self, starting_tribe="mixed"):
        pygame.init()

        self.selected_portrait_dragon = None

        self.decision_popup = None
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.game_surface = pygame.Surface((WIDTH, HEIGHT))
        pygame.display.set_caption("DragonGen - Pygame")

        self.clock = pygame.time.Clock()
        self.world = generate_starting_world(starting_tribe)
        initialize_dragon_locations(self.world)
        maintain_hierarchy(self.world)

        for dragon in self.world.dragons:
            ensure_dragon_flavor(dragon)


        self.current_screen = LocationsScreen(self.world, self.change_screen)
        self.running = True

    def check_pending_choice(self):
        choice = getattr(self.world, "pending_choice", None)

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
        resolve_choice(self.world, option_id)
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
        elif screen_name == "dashboard":
            self.current_screen = WorldDashboardScreen(self.world, self.change_screen)
        elif screen_name == "scroll_library":
            self.current_screen = ScrollLibraryScreen(self.world, self.change_screen)
        elif screen_name == "dragon_portrait":
            self.current_screen = DragonPortraitScreen(
                self.world,
                self.change_screen,
                getattr(self.world, "selected_portrait_dragon", None)
            )

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