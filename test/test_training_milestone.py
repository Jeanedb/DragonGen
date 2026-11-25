import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pygame

from core.generator import generate_starting_world
from core.save_manager import load_world, save_world
from core.sim.choice_generation.personal import create_injured_patrol_choice
from core.sim.choices import resolve_choice
from core.sim.patrol_experience import PATROL_MILESTONE
from ui_pygame.screens.border_routes import BorderRoutesScreen
from ui_pygame.screens.dragon_profile import DragonProfileScreen
from ui_pygame.screens.training_grounds import TrainingGroundsScreen


class TrainingMilestoneTest(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        pygame.display.set_mode((1000, 700))
        self.world = generate_starting_world("seawing")

    def reload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world.json"
            save_world(self.world, path)
            return load_world(path)

    def test_training_budget_and_injury_eligibility(self):
        screen = TrainingGroundsScreen(self.world, lambda _: None)
        first, second = screen.get_dragons()[:2]
        first.health = "Injured"
        screen.training_group_a, screen.training_group_b = [first], [second]
        self.assertNotIn(first, screen.get_dragons())
        screen.run_training("sparring")
        screen.run_training("team")
        self.assertEqual(screen.get_training_remaining(), 2)
        screen.run_training("mentor")
        self.assertEqual(screen.get_training_remaining(), 1)
        first.health = "Healthy"
        for _ in range(4):
            screen.run_training("sparring")
        self.assertEqual(screen.get_training_remaining(), 0)
        self.assertEqual(sum(event["type"] == "training" for event in self.world.event_log), 2)
        loaded = self.reload()
        reopened = TrainingGroundsScreen(loaded, lambda _: None)
        self.assertEqual(reopened.get_training_remaining(), 0)
        loaded.moon += 1
        self.assertEqual(reopened.get_training_remaining(), 2)

    def test_patrol_milestone_survives_chronicle_eviction_and_changes_rescue_risk(self):
        border = BorderRoutesScreen(self.world, lambda _: None)
        veteran = self.world.dragons[0]
        border.selected_party = [veteran]
        with patch("ui_pygame.screens.border_routes.random.randint", return_value=1), \
             patch.object(border, "create_border_encounter"):
            for moon in (0, 0, 1):
                self.world.moon = moon
                border.dispatch_mission("patrol")
            self.assertFalse(any(m.type == PATROL_MILESTONE for m in veteran.memories))
            self.world.moon = 2
            border.dispatch_mission("patrol")
            border.dispatch_mission("patrol")
        self.assertEqual(sum(m.type == PATROL_MILESTONE for m in veteran.memories), 1)
        self.world.event_log.clear()
        loaded = self.reload()
        veteran, patient, novice = loaded.dragons[:3]
        profile = DragonProfileScreen(loaded, lambda _: None)
        self.assertTrue(any(entry["type"] == PATROL_MILESTONE for entry in profile.get_dragon_events(veteran)))

        for helper, expected, risk in ((veteran, "Healthy", "20%"), (novice, "Injured", "35%")):
            patient.health = "Healthy"
            with (
                patch("core.sim.choice_generation.personal.get_most_hostile_relation", return_value=(None, 0)),
                patch("core.sim.choice_generation.personal.random.choices", return_value=[(patient, helper)]),
            ):
                self.assertTrue(create_injured_patrol_choice(loaded))
            self.assertIn(risk, loaded.pending_choice["options"][0]["text"])
            with patch("core.sim.choice_handlers.personal.random.random", return_value=0.25):
                resolve_choice(loaded, "stay_and_help")
            self.assertEqual(helper.health, expected)
