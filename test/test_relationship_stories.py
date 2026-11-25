import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pygame

from core.generator import generate_starting_world
from core.save_manager import load_world, save_world
from core.sim.choices import resolve_choice
from core.sim.relationship_stories import try_expedition_credit, try_friendship_rations
from core.simulation import offer_moon_choice
from ui_pygame.app import PygameApp
from ui_pygame.screens.border_routes import BorderRoutesScreen
from ui_pygame.screens.dragon_profile import DragonProfileScreen
from ui_pygame.screens.training_grounds import TrainingGroundsScreen


class RelationshipStoryTest(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        pygame.display.set_mode((1000, 700))
        self.world = generate_starting_world("skywing")
        self.actor, self.other, self.witness = self.world.dragons[:3]

    def reload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slot.json"
            save_world(self.world, path)
            return load_world(path)

    def test_shared_meal_can_be_returned_and_survives_save_reload(self):
        self.actor.friends.append(self.other.id)
        self.other.health = "Injured"
        self.witness.resentment[self.actor.id] = 2
        self.world.food_stores = 8
        with patch("core.sim.relationship_stories.random.random", return_value=0):
            offer_moon_choice(self.world)
        self.assertEqual(self.world.pending_choice["location"], "village")
        resolve_choice(self.world, "share")
        self.assertEqual(self.world.food_stores, 6)
        self.assertEqual(self.other.trust[self.actor.id], 1)
        self.assertEqual(self.witness.resentment[self.actor.id], 2.5)

        self.world = self.reload()
        donor, friend = self.world.dragons[:2]
        donor.health = "Injured"
        friend.health = "Healthy"
        self.world.food_stores = 20
        self.world.moon = 2
        self.assertFalse(try_friendship_rations(self.world))
        self.world.moon = 3
        self.assertTrue(try_friendship_rations(self.world))
        self.assertTrue(self.world.pending_choice["returning"])
        self.assertEqual(self.world.pending_choice["actor_id"], friend.id)
        deferred = self.reload()
        resolve_choice(deferred, "reserve")
        self.assertEqual(deferred.food_stores, 20)
        self.assertFalse(try_friendship_rations(deferred))
        resolve_choice(self.world, "share")
        self.assertEqual(self.world.food_stores, 18)
        self.assertEqual(donor.trust[friend.id], 2)
        self.assertFalse(try_friendship_rations(self.world))
        self.world.event_log.clear()
        profile = DragonProfileScreen(self.world, lambda _: None)
        self.assertEqual(
            [entry["type"] for entry in profile.get_dragon_events(donor)],
            ["received_returned_ration", "shared_ration", "accused_of_favouritism"],
        )

    def test_successful_expedition_revisits_training_rivalry_and_routes_to_border(self):
        training = TrainingGroundsScreen(self.world, lambda _: None)
        training.apply_training_effect(self.other, self.actor, "embarrass")
        self.actor.resentment[self.other.id] = 2
        border = BorderRoutesScreen(self.world, lambda _: None)
        border.selected_party = [self.actor, self.other]
        with patch("ui_pygame.screens.border_routes.random.randint", side_effect=lambda low, high: low):
            border.dispatch_mission("expedition")
        self.assertEqual(self.world.pending_choice["type"], "expedition_credit")
        self.assertEqual(border.get_actions_remaining(), 1)
        claimed = self.reload()

        app = PygameApp(world=self.world)
        app.current_screen.open_pending_choice()
        self.assertEqual(app.current_screen_name, "border_routes")
        app.check_pending_choice()
        app.decision_popup.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1))
        self.assertEqual(self.actor.resentment[self.other.id], 1)
        self.assertEqual(self.other.reputation["reliable"], 0.5)
        self.assertFalse(try_expedition_credit(self.world, [self.actor, self.other]))
        self.world.event_log.clear()
        profile = DragonProfileScreen(self.world, lambda _: None)
        self.assertTrue(any(e["type"] == "received_expedition_credit"
                            for e in profile.get_dragon_events(self.other)))

        actor, other = claimed.dragons[:2]
        prior_resentment = other.resentment.get(actor.id, 0)
        resolve_choice(claimed, "claim_credit")
        self.assertEqual(actor.reputation["reliable"], 0.5)
        self.assertEqual(other.resentment[actor.id], prior_resentment + 2)
        self.assertIn(actor.id, other.rivals)
