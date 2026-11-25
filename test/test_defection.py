import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pygame

from core.generator import generate_starting_world
from core.save_manager import load_world, save_world
from core.sim.choices import resolve_choice
from core.sim.consequences import process_scheduled_events
from core.sim.world_state import get_living_dragons
from core.simulation import get_projected_population
from ui_pygame.app import PygameApp
from ui_pygame.screens.dragon_profile import DragonProfileScreen
from ui_pygame.screens.scroll_library import ScrollLibraryScreen


class DefectionTest(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        pygame.display.set_mode((1000, 700))
        self.world = generate_starting_world("mudwing")

    def reload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world.json"
            save_world(self.world, path)
            return load_world(path)

    def test_abandoned_patrol_defects_leaves_roster_and_returns_to_border_choice(self):
        abandoned, companion = [
            dragon for dragon in self.world.dragons if dragon.rank not in {"Leader", "Deputy"}
        ][:2]
        abandoned.health = "Injured"
        abandoned.mate_id = companion.id
        companion.mate_id = abandoned.id
        self.world.pending_choice = {
            "type": "injured_patrol_choice", "injured_id": abandoned.id, "helper_id": companion.id,
        }
        with patch("random.random", return_value=0):
            outcome = resolve_choice(self.world, "run_for_help")
            self.assertIn("felt abandoned", outcome.splitlines()[0])
            self.assertNotIn("defect", outcome.lower())
            self.world = self.reload()
            for moon in (4, 6):
                self.world.moon = moon
                process_scheduled_events(self.world)
        defector = next(dragon for dragon in self.world.dragons if dragon.id == abandoned.id)
        target = next(dragon for dragon in self.world.dragons if dragon.id == companion.id)
        self.assertEqual(defector.status, "Departed")
        self.assertEqual(defector.tribe, "MudWing")
        self.assertNotIn(defector.foreign_tribe, (None, "MudWing"))
        self.assertIsNone(target.mate_id)
        self.assertIn(("former_mate", defector.id), target.memory_flags)
        self.assertNotIn(defector, get_living_dragons(self.world))
        self.assertEqual(get_projected_population(self.world), 11)

        profile = DragonProfileScreen(self.world, lambda _: None)
        self.assertNotIn(defector, profile.get_filtered_dragons())
        profile.set_status_filter("Away")
        self.assertEqual(profile.get_filtered_dragons(), [defector])
        library = ScrollLibraryScreen(self.world, lambda _: None)
        library.set_filter("Away")
        self.assertEqual(library.get_filtered_dragons(), [defector])

        self.world.moon = 12
        self.world.pending_choice = {"type": "other_decision"}
        process_scheduled_events(self.world)
        self.assertEqual(self.world.pending_choice["type"], "other_decision")
        self.assertEqual(len(self.world.scheduled_events), 1)
        self.world.pending_choice = None
        process_scheduled_events(self.world)
        self.assertEqual(self.world.pending_choice["type"], "defector_return_choice")
        self.assertEqual(self.world.scheduled_events, [])
        refused = self.reload()
        self.world = self.reload()
        app = PygameApp(world=self.world)
        app.current_screen.open_pending_choice()
        if app.current_screen_name == "locations":
            app.current_screen.enter_notice_location()
        self.assertEqual(app.current_screen_name, "border_routes")
        app.check_pending_choice()
        app.decision_popup.draw(app.game_surface)
        app.decision_popup.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1))
        self.assertIsNone(self.world.pending_choice)
        self.assertIn("resentment", app.decision_popup.body.splitlines()[0])
        self.assertIn("Both will remember", app.decision_popup.body.splitlines()[0])
        listened = next(dragon for dragon in self.world.dragons if dragon.id == abandoned.id)
        self.assertEqual(listened.resentment[target.id], defector.resentment[target.id] - 2)
        self.assertEqual(listened.status, "Departed")
        self.world.event_log.clear()
        profile = DragonProfileScreen(self.world, lambda _: None)
        self.assertTrue(any(event["type"] == "heard_at_border" for event in profile.get_dragon_events(listened)))

        resolve_choice(refused, "turn_away")
        turned_away = next(dragon for dragon in refused.dragons if dragon.id == abandoned.id)
        self.assertEqual(turned_away.resentment[target.id], defector.resentment[target.id] + 2)

    def test_legacy_defector_is_migrated_out_of_active_roster(self):
        dragon = self.world.dragons[-1]
        dragon.role = "Defector"
        dragon.tribe = "LeafWing"
        loaded = self.reload().dragons[-1]
        self.assertEqual(loaded.status, "Departed")
        self.assertEqual(loaded.foreign_tribe, "LeafWing")
        self.assertEqual(loaded.location, "foreign_territory")
