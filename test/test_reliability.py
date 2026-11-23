import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pygame

from core.generator import generate_starting_world
from core.save_manager import load_world, save_world
from core.sim.consequences import process_scheduled_events, schedule_consequence
from core.simulation import advance_moon
from ui_pygame.app import PygameApp
from ui_pygame.main_menu import PygameMainMenu
from ui_pygame.widgets.save_slot_browser import SaveSlotBrowser


class SaveReliabilityTest(unittest.TestCase):
    def test_interrupted_overwrite_preserves_slot_and_cleans_up_temp_file(self):
        world = generate_starting_world("mudwing")

        def interrupt(_data, output, **_kwargs):
            output.write("{")
            raise OSError("Interrupted write")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slot_1.json"
            save_world(world, path)
            original = path.read_bytes()
            world.moon += 1
            with patch("core.save_manager.json.dump", side_effect=interrupt):
                with self.assertRaisesRegex(OSError, "Interrupted write"):
                    save_world(world, path)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_delayed_choice_consequence_and_caretaker_survive_reload(self):
        world = generate_starting_world("mudwing")
        child, caretaker = world.dragons[:2]
        child.caretaker_id = caretaker.id
        child.caretaker_role = caretaker.role
        schedule_consequence(world, 3, {
            "type": "abandoned_return", "abandoned": child.id, "abandoner": caretaker.id,
        })

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slot_1.json"
            save_world(world, path)
            loaded = load_world(path)
            self.assertEqual(loaded.dragons[0].caretaker_id, caretaker.id)
            self.assertEqual(loaded.dragons[0].caretaker_role, caretaker.role)
            loaded.moon = 2
            process_scheduled_events(loaded)
            self.assertEqual(len(loaded.scheduled_events), 1)
            loaded.moon = 3
            process_scheduled_events(loaded)
            self.assertEqual(loaded.scheduled_events, [])
            self.assertIn(caretaker.id, loaded.dragons[0].rivals)
            self.assertEqual(loaded.event_log[-1]["type"], "delayed_consequence")

            old_save = json.loads(path.read_text())
            old_save["save_version"] = 9
            old_save.pop("scheduled_events")
            for dragon in old_save["dragons"]:
                dragon.pop("caretaker_id")
                dragon.pop("caretaker_role")
            path.write_text(json.dumps(old_save), encoding="utf-8")
            legacy = load_world(path)
            self.assertEqual(legacy.scheduled_events, [])
            self.assertIsNone(legacy.dragons[0].caretaker_id)


class MoonReliabilityTest(unittest.TestCase):
    def test_choice_moon_completes_shared_phases_and_pending_choice_pauses_next_moon(self):
        for offer_choice in (False, True):
            with self.subTest(offer_choice=offer_choice):
                world = generate_starting_world("mudwing")
                phases = []

                def offer(current):
                    phases.append("choice")
                    if offer_choice:
                        current.pending_choice = {"type": "mudwing_marsh_fire", "location": "mud_wallow"}

                with (
                    patch("core.simulation.run_event_phase", side_effect=lambda _world: phases.append("events")),
                    patch("core.simulation.run_politics_phase", side_effect=lambda _world: phases.append("politics")),
                    patch("core.simulation.evaluate_world_titles", side_effect=lambda _world: phases.append("titles")),
                    patch("core.simulation.offer_moon_choice", side_effect=offer),
                    redirect_stdout(io.StringIO()),
                ):
                    self.assertTrue(advance_moon(world))
                    self.assertEqual(world.moon, 1)
                    self.assertEqual(phases, ["events", "politics", "titles", "choice"])
                    if offer_choice:
                        self.assertFalse(advance_moon(world))
                        self.assertEqual(world.moon, 1)
                        self.assertEqual(len(phases), 4)


class ResizedInputTest(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)

    def click(self, handler, position, scale, event_type=pygame.MOUSEBUTTONDOWN):
        window_pos = tuple(round(value * scale) for value in position)
        handler(pygame.event.Event(event_type, button=1, pos=window_pos))

    def test_menu_profile_wheel_decision_and_save_browser_at_three_sizes(self):
        with redirect_stdout(io.StringIO()), tempfile.TemporaryDirectory() as directory:
            menu = PygameMainMenu()
            app = PygameApp(starting_tribe="mudwing")
            for scale in (1, 1.25, 1.50):
                with self.subTest(scale=scale):
                    window = pygame.display.set_mode((int(1000 * scale), int(700 * scale)))
                    menu.screen = window
                    app.screen = window
                    menu.show_main()
                    menu.draw(0)
                    self.click(menu.handle_event, (241, 339), scale, pygame.MOUSEBUTTONUP)
                    self.assertEqual(menu.state, "tribes")

                    app.change_screen("dragon_profile")
                    app.current_screen.draw(app.game_surface)
                    with patch("pygame.mouse.get_pos", return_value=(int(180 * scale), int(320 * scale))):
                        app.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-1))
                    self.assertLess(app.current_screen.list_scroll, 0)
                    self.click(app.handle_event, (500, 660), scale)
                    self.assertEqual(app.current_screen_name, "locations")

                    app.world.pending_choice = {
                        "type": "mudwing_marsh_fire", "location": "mud_wallow",
                        "text": "The reeds are burning.",
                        "options": [{"id": "perimeter", "text": "Evacuate along the perimeter"}],
                    }
                    app.current_screen.draw(app.game_surface)
                    self.click(app.handle_event, (450, 385), scale)
                    self.assertEqual(app.current_screen_name, "mud_wallow")
                    app.check_pending_choice()
                    app.decision_popup.draw(app.game_surface)
                    self.click(app.handle_event, app.decision_popup.button_rects[0].center, scale)
                    self.assertIsNone(app.world.pending_choice)
                    app.close_decision_result()

                    saved = []
                    app.save_browser = SaveSlotBrowser(
                        directory, "save", lambda path, slot: saved.append((path, slot)), lambda: None
                    )
                    self.click(app.handle_event, (777, 164), scale, pygame.MOUSEBUTTONUP)
                    self.assertEqual(saved, [(Path(directory) / "saves" / "slot_1.json", 1)])
                    app.save_browser = None
