import io
import random
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pygame

from core.generator import generate_starting_world
from core.save_manager import load_world, save_world
from core.sim.choices import resolve_choice
from core.sim.seawing import try_reef_storm
from core.simulation import advance_moon
from ui_pygame.app import PygameApp


class SeaWingFeatureTest(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        random_state = random.getstate()
        self.addCleanup(random.setstate, random_state)
        random.seed(11)
        with redirect_stdout(io.StringIO()):
            self.app = PygameApp(starting_tribe="seawing")
        self.world = self.app.world
        self.diver, self.shore_helper = self.world.dragons[:2]
        for dragon in (self.diver, self.shore_helper):
            dragon.role = "Hunter"
            dragon.health = "Healthy"
        self.shore_helper.tribe = "SkyWing"

    def expedition_buttons(self):
        screen = self.app.current_screen
        screen.draw(self.app.game_surface)
        return [button for button in screen.buttons if getattr(button, "label", "") == "BEGIN"]

    def test_reef_route_buttons_split_mixed_party_and_share_hunt_budget(self):
        self.app.current_screen.open_location("hunting")
        hunt = self.app.current_screen
        hunt.hunt_party_mode = "party"
        hunt.selected_party = [self.shore_helper]
        small, large, dangerous, shallow, deep = self.expedition_buttons()
        self.assertTrue(all(button.enabled for button in (small, large, dangerous, shallow)))
        self.assertFalse(deep.enabled)
        hunt.run_hunt("deep_reef")
        self.assertEqual(hunt.get_hunts_remaining(), 2)

        hunt.selected_party = [self.diver, self.shore_helper]
        deep = self.expedition_buttons()[-1]
        self.assertTrue(deep.enabled)
        food_before = self.world.food_stores
        with (
            patch("core.sim.seawing.random.random", side_effect=(0.0, 0.9, 0.0)),
            patch("core.sim.seawing.random.randint", side_effect=lambda low, high: low),
        ):
            self.app.handle_event(pygame.event.Event(
                pygame.MOUSEBUTTONUP, button=1, pos=deep.rect.center
            ))
            expected = round(21 * 1.12) + 2
            self.assertEqual(self.world.food_stores, food_before + expected)
            self.assertEqual(hunt.get_dragon_fatigue(self.diver), 2)
            self.assertEqual(hunt.get_dragon_fatigue(self.shore_helper), 1)
            self.assertEqual(hunt.get_hunts_remaining(), 1)

            hunt.selected_party = [self.shore_helper]
            hunt.run_hunt("shallow_reef")
        self.assertEqual(hunt.get_dragon_fatigue(self.shore_helper), 2)
        self.assertEqual(hunt.get_hunts_remaining(), 0)
        self.assertTrue(all(not button.enabled for button in self.expedition_buttons()))

    def test_storm_survives_save_and_three_responses_have_distinct_costs(self):
        with patch("core.sim.seawing.random.random", return_value=0.0), redirect_stdout(io.StringIO()):
            self.assertTrue(advance_moon(self.world))
        choice = self.world.pending_choice
        self.assertEqual(choice["type"], "seawing_reef_storm")
        self.assertEqual(choice["shore_id"], self.shore_helper.id)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slot.json"
            save_world(self.world, path)
            dive, shore, wait = [load_world(path) for _ in range(3)]

        self.assertEqual(dive.pending_choice, choice)
        food = self.world.food_stores
        stranded_id = choice["stranded_id"]
        tension = self.world.tension

        with redirect_stdout(io.StringIO()):
            app = PygameApp(world=dive)
        app.current_screen.open_pending_choice()
        if app.current_screen_name == "locations":
            app.current_screen.enter_notice_location()
        self.assertEqual(app.current_screen_name, "hunting_grounds")
        app.check_pending_choice()
        app.decision_popup.draw(app.game_surface)
        app.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=app.decision_popup.button_rects[0].center
        ))
        self.assertIsNone(dive.pending_choice)
        self.assertEqual(dive.food_stores, food + 8)
        self.assertEqual(dive.world_flags["dragon_fatigue"][str(choice["diver_ids"][0])], 2)
        rescued = next(dragon for dragon in dive.dragons if dragon.id == stranded_id)
        self.assertTrue(any(memory.type == "helped_ashore_at_reef" for memory in rescued.memories))

        resolve_choice(shore, "shore")
        self.assertEqual(shore.food_stores, food)
        self.assertEqual(shore.world_flags["dragon_fatigue"][str(self.shore_helper.id)], 1)
        resolve_choice(wait, "wait")
        self.assertEqual(wait.food_stores, food)
        self.assertEqual(wait.world_flags["dragon_fatigue"][str(stranded_id)], 2)
        self.assertAlmostEqual(wait.tension, min(5, tension + 0.15))
        self.assertFalse(try_reef_storm(wait))

    def test_other_tribes_keep_land_hunts_and_cannot_generate_reef_storms(self):
        world = generate_starting_world("mudwing")
        with redirect_stdout(io.StringIO()):
            self.app = PygameApp(world=world)
        self.app.change_screen("hunting_grounds")
        self.assertEqual(len(self.expedition_buttons()), 3)
        self.app.current_screen.run_hunt("shallow_reef")
        self.assertEqual(self.app.current_screen.get_hunts_remaining(), 2)
        self.assertFalse(try_reef_storm(world))

    def test_aquatic_warning_needs_second_seawing_and_resolves_after_reload(self):
        self.app.change_screen("hunting_grounds")
        hunt = self.app.current_screen
        hunt.hunt_party_mode = "party"
        hunt.selected_party = [self.diver, self.shore_helper]
        with patch("core.sim.seawing.random.random", return_value=0.0):
            hunt.run_hunt("deep_reef")
        self.assertEqual(
            [option["id"] for option in self.world.pending_choice["options"]], ["recall", "wait"]
        )
        resolve_choice(self.world, "recall")
        self.assertEqual(hunt.get_hunts_remaining(), 1)

        interpreter = self.world.dragons[2]
        interpreter.role = "Scout"
        interpreter.health = "Healthy"
        hunt.selected_party.append(interpreter)
        original_food = self.world.food_stores
        with patch("core.sim.seawing.random.random", return_value=0.0):
            hunt.run_hunt("deep_reef")
        choice = self.world.pending_choice
        self.assertEqual(choice["type"], "seawing_aquatic_warning")
        self.assertEqual(choice["interpreter_id"], interpreter.id)
        self.assertEqual(self.world.food_stores, original_food)
        self.assertEqual(hunt.get_hunts_remaining(), 0)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slot.json"
            save_world(self.world, path)
            relay, recall, wait = [load_world(path) for _ in range(3)]

        self.assertEqual(relay.pending_choice, choice)
        with redirect_stdout(io.StringIO()):
            app = PygameApp(world=relay)
        app.current_screen.open_pending_choice()
        if app.current_screen_name == "locations":
            app.current_screen.enter_notice_location()
        self.assertEqual(app.current_screen_name, "hunting_grounds")
        app.check_pending_choice()
        app.decision_popup.draw(app.game_surface)
        app.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=app.decision_popup.button_rects[0].center
        ))
        self.assertIsNone(relay.pending_choice)
        self.assertEqual(relay.food_stores, original_food + choice["food"])
        self.assertEqual(relay.world_flags["dragon_fatigue"][str(interpreter.id)], 3)
        self.assertEqual(relay.dragons[1].trust[interpreter.id], 0.5)
        resolve_choice(recall, "recall")
        self.assertEqual(recall.food_stores, original_food + choice["shore_food"])
        resolve_choice(wait, "wait")
        self.assertEqual(wait.food_stores, original_food + choice["wait_food"])
        self.assertEqual(wait.world_flags["dragon_fatigue"][str(self.diver.id)], 5)

    def test_seawing_roster_can_get_the_warning_with_a_visiting_crew(self):
        self.shore_helper.tribe = "SeaWing"
        self.app.change_screen("hunting_grounds")
        hunt = self.app.current_screen
        hunt.hunt_party_mode = "party"
        hunt.selected_party = [self.diver, self.shore_helper]
        with patch("core.sim.seawing.random.random", return_value=0.0):
            hunt.run_hunt("deep_reef")
        choice = self.world.pending_choice
        self.assertIn("visiting shore crew", choice["text"])
        self.assertEqual(choice["options"][0]["id"], "relay")
        self.assertEqual(choice["shore_food"], 0)
