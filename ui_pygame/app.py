from pathlib import Path

import pygame

from ui_pygame.core.coordinates import CANVAS_SIZE, canvas_event, canvas_mouse_position

from core.save_manager import save_world
from ui_pygame.widgets.save_slot_browser import SaveSlotBrowser
from ui_pygame.screens.healer_den_poc import HealerDenScreen
from core.generator import generate_starting_world
from core.sim.locations import initialize_dragon_locations
from core.sim.flavor import ensure_dragon_flavor
from core.sim.leadership import maintain_hierarchy
from ui_pygame.screens.locations import LocationsScreen
from ui_pygame.screens.queen_palace import QueenPalaceScreen
from ui_pygame.screens.village_center_v2_3_dialogue_test import VillageCenterScreen
from ui_pygame.screens.dragon_profile import DragonProfileScreen
from ui_pygame.widgets.decision_popup import DecisionPopup
from core.sim.choices import resolve_choice
from core.sim.life_story import decision_follow_candidate, set_followed
from ui_pygame.screens.world_dashboard import WorldDashboardScreen
from ui_pygame.screens.scroll_library import ScrollLibraryScreen
from ui_pygame.screens.dragon_portrait import DragonPortraitScreen
from ui_pygame.screens.training_grounds import TrainingGroundsScreen
from ui_pygame.screens.hunting_grounds import HuntingGroundsScreen
from ui_pygame.screens.border_routes import BorderRoutesScreen
from ui_pygame.screens.hatchery import HatcheryScreen
from ui_pygame.screens.mud_wallow import MudWallowScreen


WIDTH, HEIGHT = CANVAS_SIZE
FPS = 60


class PygameApp:
    def __init__(self, starting_tribe="mixed", world=None):
        pygame.init()

        self.selected_portrait_dragon = None

        self.decision_popup = None
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.game_surface = pygame.Surface((WIDTH, HEIGHT))
        pygame.display.set_caption("DragonGen - Pygame")

        self.clock = pygame.time.Clock()
        self.world = (
            world
            if world is not None
            else generate_starting_world(starting_tribe)
        )
        initialize_dragon_locations(self.world)
        maintain_hierarchy(self.world)

        for dragon in self.world.dragons:
            ensure_dragon_flavor(dragon)


        self.current_screen_name = "locations"
        self.current_screen = LocationsScreen(self.world, self.change_screen)
        self.running = True

        # Returning to the menu is owned by the app rather than by an
        # individual screen.  That keeps saving and navigation consistent
        # everywhere in the game.
        self.exit_action = "quit"
        self.show_exit_prompt = False
        self.save_browser = None
        self.save_returns_to_menu = False
        self.exit_status = ""
        self.menu_button_rect = pygame.Rect(211, 28, 82, 39)
        self.exit_save_rect = pygame.Rect(285, 364, 205, 48)
        self.exit_without_save_rect = pygame.Rect(510, 364, 205, 48)
        self.exit_cancel_rect = pygame.Rect(410, 425, 180, 42)

        self.menu_font = pygame.font.SysFont("georgia", 14, bold=True)
        self.exit_title_font = pygame.font.SysFont("georgia", 26, bold=True)
        self.exit_body_font = pygame.font.SysFont("georgia", 16)
        self.exit_button_font = pygame.font.SysFont("georgia", 14, bold=True)

    def check_pending_choice(self):
        # A resolved choice deliberately remains visible until the player
        # acknowledges its consequences.
        if self.decision_popup and self.decision_popup.is_showing_result:
            return

        choice = getattr(self.world, "pending_choice", None)

        if not choice:
            self.decision_popup = None
            return

        # Location IDs stored on choices are intentionally the same IDs used
        # by the map. Screen class names are translated here where necessary.
        screen_locations = {
            "relations": "relations",
            "village": "village",
            "healer_den": "healer_den",
            "training_grounds": "training",
            "hunting_grounds": "hunting",
            "border_routes": "border",
            "scroll_library": "library",
            "hatchery": "hatchery",
            "mud_wallow": "mud_wallow",
        }
        open_location = screen_locations.get(self.current_screen_name)
        choice_location = choice.get("location", "relations")

        # Keep the choice pending, but do not interrupt the player on the map
        # or while visiting an unrelated location.
        if open_location != choice_location:
            self.decision_popup = None
            return

        if self.decision_popup is None:
            self.decision_popup = DecisionPopup(
                title="Decision",
                body=choice.get("text", "A choice must be made."),
                options=choice.get("options", []),
                on_choose=self.resolve_decision,
                context=choice.get("context", []),
            )

    def resolve_decision(self, option_id):
        event_start = len(self.world.event_log)
        outcome = resolve_choice(self.world, option_id)
        if self.decision_popup is not None:
            candidate = decision_follow_candidate(self.world, self.world.event_log[event_start:], option_id)
            follow = None
            if candidate:
                follow = lambda: set_followed(self.world, candidate.id, True)
            self.decision_popup.show_result(
                outcome,
                on_continue=self.close_decision_result,
                follow_name=candidate.name if candidate else None,
                on_follow=follow,
            )
        else:
            self.decision_popup = None

    def close_decision_result(self):
        self.decision_popup = None

    def change_screen(self, screen_name, *, dragon_id=None):
        if screen_name == "save_game":
            self.open_save_slots(return_to_menu=False)
            return

        self.current_screen_name = screen_name

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
            if dragon_id is not None:
                dragon = next((member for member in self.world.dragons if member.id == dragon_id), None)
                if dragon is not None:
                    self.current_screen.set_status_filter("All")
                    self.current_screen.select_dragon(dragon)
                    self.current_screen.set_profile_tab("History")
                    self.current_screen.set_history_mode("Full Chronicle")
        elif screen_name == "dashboard":
            self.current_screen = WorldDashboardScreen(self.world, self.change_screen)
        elif screen_name == "scroll_library":
            self.current_screen = ScrollLibraryScreen(self.world, self.change_screen)
        elif screen_name == "training_grounds":
            self.current_screen = TrainingGroundsScreen(self.world, self.change_screen)
        elif screen_name == "hunting_grounds":
            self.current_screen = HuntingGroundsScreen(self.world, self.change_screen)
        elif screen_name == "border_routes":
            self.current_screen = BorderRoutesScreen(self.world, self.change_screen)
        elif screen_name == "hatchery":
            self.current_screen = HatcheryScreen(self.world, self.change_screen)    
        elif screen_name == "mud_wallow":
            self.current_screen = MudWallowScreen(self.world, self.change_screen)
        elif screen_name == "dragon_portrait":
            self.current_screen = DragonPortraitScreen(
                self.world,
                self.change_screen,
                getattr(self.world, "selected_portrait_dragon", None)
            )

    def request_main_menu(self):
        self.exit_status = ""
        self.show_exit_prompt = True

    def cancel_main_menu(self):
        self.exit_status = ""
        self.show_exit_prompt = False

    def return_to_main_menu(self):
        self.exit_action = "main_menu"
        self.running = False

    def open_save_slots(self, return_to_menu=True):
        project_root = Path(__file__).resolve().parents[1]
        self.save_returns_to_menu = return_to_menu
        self.show_exit_prompt = False
        self.save_browser = SaveSlotBrowser(
            project_root=project_root,
            mode="save",
            on_slot=self.save_to_slot,
            on_cancel=self.cancel_save_slots,
        )

    def cancel_save_slots(self):
        self.save_browser = None
        if self.save_returns_to_menu:
            self.show_exit_prompt = True

    def save_to_slot(self, filename, slot_number):
        try:
            save_world(self.world, str(filename))
            print(f"Game saved to: {filename}")
        except Exception as error:
            print(f"Could not save game: {error}")
            if self.save_browser:
                self.save_browser.set_status(
                    "The game could not be saved. Please try again."
                )
            return False

        if self.save_returns_to_menu:
            self.return_to_main_menu()
        elif self.save_browser:
            self.save_browser.refresh()
            self.save_browser.set_status(
                f"Game saved successfully in Slot {slot_number}."
            )
        return True

    def handle_exit_prompt_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.cancel_main_menu()
            return

        if event.type != pygame.MOUSEBUTTONUP or event.button != 1:
            return

        mouse_pos = event.pos
        if self.exit_save_rect.collidepoint(mouse_pos):
            self.open_save_slots()
        elif self.exit_without_save_rect.collidepoint(mouse_pos):
            self.return_to_main_menu()
        elif self.exit_cancel_rect.collidepoint(mouse_pos):
            self.cancel_main_menu()

    def draw_fantasy_button(self, surface, rect, label, font, primary=False):
        mouse_pos = canvas_mouse_position()
        hovered = rect.collidepoint(mouse_pos)

        shadow = rect.move(0, 4)
        pygame.draw.rect(surface, (10, 7, 5), shadow, border_radius=8)

        if primary:
            edge = (242, 201, 76) if hovered else (181, 128, 62)
            fill = (112, 67, 28) if hovered else (82, 49, 24)
        else:
            edge = (166, 118, 68) if hovered else (112, 83, 56)
            fill = (67, 52, 40) if hovered else (43, 35, 29)

        pygame.draw.rect(surface, edge, rect, border_radius=8)
        inner = rect.inflate(-6, -6)
        pygame.draw.rect(surface, fill, inner, border_radius=6)
        pygame.draw.line(
            surface,
            (219, 174, 100),
            (inner.left + 7, inner.top + 3),
            (inner.right - 7, inner.top + 3),
            1,
        )

        text = font.render(label, True, (244, 224, 184))
        surface.blit(text, text.get_rect(center=rect.center))

    def draw_menu_button(self, surface):
        # The map has a purpose-built gap between Advance Moon and its title.
        # Other screens can open the same menu with Escape without disturbing
        # their carefully arranged layouts.
        if self.current_screen_name != "locations":
            return
        if getattr(self.current_screen, "show_advance_confirmation", False):
            return
        if self.decision_popup or self.show_exit_prompt or self.save_browser:
            return

        self.draw_fantasy_button(
            surface,
            self.menu_button_rect,
            "MENU",
            self.menu_font,
        )

    def draw_exit_prompt(self, surface):
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((5, 3, 2, 195))
        surface.blit(shade, (0, 0))

        panel = pygame.Rect(235, 175, 530, 320)
        shadow = panel.move(0, 8)
        pygame.draw.rect(surface, (8, 5, 4), shadow, border_radius=12)
        pygame.draw.rect(surface, (151, 103, 54), panel, border_radius=12)
        inner = panel.inflate(-7, -7)
        pygame.draw.rect(surface, (29, 23, 19), inner, border_radius=9)
        pygame.draw.rect(surface, (75, 55, 38), inner, width=2, border_radius=9)

        title = self.exit_title_font.render(
            "RETURN TO MAIN MENU?",
            True,
            (246, 216, 158),
        )
        surface.blit(title, title.get_rect(center=(WIDTH // 2, 225)))

        line_one = self.exit_body_font.render(
            "Would you like to save your tribe before leaving?",
            True,
            (226, 211, 184),
        )
        surface.blit(line_one, line_one.get_rect(center=(WIDTH // 2, 276)))

        line_two = self.exit_body_font.render(
            "Pending decisions and current progress are included in the save.",
            True,
            (167, 151, 130),
        )
        surface.blit(line_two, line_two.get_rect(center=(WIDTH // 2, 307)))

        if self.exit_status:
            status = self.exit_body_font.render(
                self.exit_status,
                True,
                (220, 137, 104),
            )
            surface.blit(status, status.get_rect(center=(WIDTH // 2, 338)))

        self.draw_fantasy_button(
            surface,
            self.exit_save_rect,
            "SAVE & RETURN",
            self.exit_button_font,
            primary=True,
        )
        self.draw_fantasy_button(
            surface,
            self.exit_without_save_rect,
            "LEAVE WITHOUT SAVING",
            self.exit_button_font,
        )
        self.draw_fantasy_button(
            surface,
            self.exit_cancel_rect,
            "CANCEL",
            self.exit_button_font,
        )

    def scale_surface_to_window(self):
        window_w, window_h = self.screen.get_size()
        scaled_surface = pygame.transform.smoothscale(
            self.game_surface,
            (window_w, window_h)
        )
        self.screen.blit(scaled_surface, (0, 0))

    def handle_event(self, event):
        event = canvas_event(event)
        if event.type == pygame.QUIT:
            self.exit_action = "quit"
            self.running = False
            return

        if self.save_browser:
            self.save_browser.handle_event(event)
            return

        if self.show_exit_prompt:
            self.handle_exit_prompt_event(event)
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.request_main_menu()
            return

        if (
            self.current_screen_name == "locations"
            and not self.decision_popup
            and not getattr(
                self.current_screen,
                "show_advance_confirmation",
                False,
            )
            and event.type == pygame.MOUSEBUTTONUP
            and event.button == 1
            and self.menu_button_rect.collidepoint(event.pos)
        ):
            self.request_main_menu()
            return

        if self.decision_popup:
            self.decision_popup.handle_event(event)
        else:
            self.current_screen.handle_event(event)

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000

            for event in pygame.event.get():
                self.handle_event(event)

            if not self.running:
                break

            self.current_screen.update(dt)
            self.check_pending_choice()
            self.current_screen.draw(self.game_surface)

            self.draw_menu_button(self.game_surface)

            if self.decision_popup:
                self.decision_popup.draw(self.game_surface)

            if self.show_exit_prompt:
                self.draw_exit_prompt(self.game_surface)

            if self.save_browser:
                self.save_browser.draw(
                    self.game_surface,
                    mouse_pos=canvas_mouse_position(),
                )

            self.scale_surface_to_window()
            pygame.display.flip()

        pygame.quit()
        return self.exit_action


if __name__ == "__main__":
    app = PygameApp()
    app.run()
