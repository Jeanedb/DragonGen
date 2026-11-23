import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pygame

from core.generator import generate_starting_world
from core.save_manager import load_world, save_world
from ui_pygame.screens.border_routes import BorderRoutesScreen


class SibPatrolTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        cls.addClassCleanup(pygame.display.quit)
        pygame.display.set_mode((1, 1))
        pygame.font.init()
        cls.addClassCleanup(pygame.font.quit)

    def setUp(self):
        self.world = generate_starting_world("mudwing")
        self.injured, self.sib, self.third = self.world.dragons[:3]
        for dragon in self.world.dragons:
            dragon.role = "Warrior"
        self.injured.is_bigwings = False
        self.sib.is_bigwings = False
        self.third.is_bigwings = True
        self.screen = BorderRoutesScreen(self.world, lambda _: None)

    def dispatch_failed_patrol(self, party):
        self.screen.selected_party = party
        # Force a failed mission, an injury, and an encounter if anyone remains.
        with (
            patch("random.randint", return_value=100),
            patch("random.random", return_value=0),
            patch("random.choice", side_effect=lambda candidates: candidates[0]),
        ):
            self.screen.dispatch_mission("patrol")

    def test_bigwings_escorts_sib_and_remaining_sib_handles_encounter(self):
        trust_before = self.injured.trust.get(self.third.id, 0)
        self.dispatch_failed_patrol([self.injured, self.sib, self.third])

        self.assertEqual(self.injured.health, "Injured")
        self.assertEqual(self.injured.location, "healer_den")
        self.assertEqual(self.third.location, "healer_den")
        self.assertEqual(self.world.pending_choice["party_ids"], [self.sib.id])
        self.assertEqual(self.screen.get_actions_remaining(), 1)
        self.assertTrue(any(
            f"{self.third.name} left the patrol" in event["text"]
            for event in self.world.event_log
        ))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world.json"
            save_world(self.world, path)
            loaded = load_world(path)

        by_id = {dragon.id: dragon for dragon in loaded.dragons}
        injured = by_id[self.injured.id]
        escort = by_id[self.third.id]
        self.assertEqual(escort.location, "healer_den")
        self.assertEqual(injured.trust[escort.id], trust_before + 1)
        self.assertTrue(any(
            memory.type == "escorted_by_sib" and memory.other_id == escort.id
            for memory in injured.memories
        ))
        self.assertTrue(any(
            memory.type == "escorted_injured_sib" and memory.other_id == injured.id
            for memory in escort.memories
        ))

    def test_encounter_is_skipped_when_no_patrolmates_remain(self):
        self.dispatch_failed_patrol([self.injured, self.sib])

        self.assertEqual(self.sib.location, "healer_den")
        self.assertIsNone(self.world.pending_choice)

    def test_unrelated_patrolmate_keeps_existing_patrol_behavior(self):
        self.sib.sib_group_id = "another-sib-group"
        original_location = self.sib.location
        self.dispatch_failed_patrol([self.injured, self.sib])

        self.assertEqual(self.injured.health, "Injured")
        self.assertEqual(self.sib.location, original_location)
        self.assertEqual(
            self.world.pending_choice["party_ids"], [self.injured.id, self.sib.id]
        )
        self.assertFalse(any(
            memory.type == "escorted_by_sib" for memory in self.injured.memories
        ))


if __name__ == "__main__":
    unittest.main()
