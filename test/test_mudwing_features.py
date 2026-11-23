import io
import random
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pygame

from core.generator import generate_dragonet, generate_starting_world
from core.save_manager import load_world, save_world
from core.sim.choices import resolve_choice
from core.sim.eggs import create_egg
from core.sim.family import are_family
from core.sim.injury import escort_injured_sib
from core.sim.mates import can_become_mates
from core.sim.mudwing import (
    maintain_bigwings, rest_sibs_at_wallow, try_marsh_fire, try_mudwing_sib_decision,
    try_sib_adoption,
)
from core.simulation import advance_moon
from ui_pygame.app import PygameApp
from ui_pygame.screens.dragon_profile import DragonProfileScreen
from ui_pygame.screens.locations import LocationsScreen


class MudWingFeatureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        cls.addClassCleanup(pygame.display.quit)
        pygame.display.set_mode((1000, 700))
        pygame.font.init()
        cls.addClassCleanup(pygame.font.quit)

    def setUp(self):
        state = random.getstate()
        self.addCleanup(random.setstate, state)
        random.seed(7)
        self.world = generate_starting_world("mudwing")
        self.bigwings, self.second, self.third, self.fourth = self.world.dragons[:4]
        for dragon in self.world.dragons:
            dragon.role = "Warrior"

    def reload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world.json"
            save_world(self.world, path)
            return load_world(path)

    def test_moon_advance_passes_bigwings_duties_and_preserves_birth_order(self):
        self.bigwings.age_moons = 260
        with patch("core.sim.death.random.random", return_value=0.15), redirect_stdout(io.StringIO()):
            self.assertTrue(advance_moon(self.world))

        group = self.reload().dragons[:4]
        self.assertEqual(group[0].status, "Dead")
        self.assertEqual([dragon.birth_order for dragon in group], [1, 2, 3, 4])
        self.assertEqual(
            [dragon.id for dragon in group if dragon.status == "Alive" and dragon.is_bigwings],
            [self.second.id],
        )
        self.assertTrue(any(
            memory.type == "took_up_bigwings_duties" and memory.other_id == self.bigwings.id
            for memory in group[1].memories
        ))

    def test_mudwing_profile_shows_sibs_and_hatch_traits(self):
        self.bigwings.egg_type = "blood_red"
        self.bigwings.fire_resistant = True
        for dragon in self.world.dragons[:4]:
            dragon.sib_group_id = "mudwing-clutch-9"
        self.second.location = "mud_wallow"
        screen = DragonProfileScreen(self.world, lambda _: None)
        screen.select_dragon(self.bigwings)
        screen.set_profile_tab("Sibs")
        with (
            patch.object(screen, "draw_wrapped_text", wraps=screen.draw_wrapped_text) as lines,
            patch.object(screen, "draw_tag", wraps=screen.draw_tag) as tags,
        ):
            screen.draw(pygame.display.get_surface())
        content = " ".join(call.args[1] for call in lines.call_args_list)
        for fragment in ("Hatch order 1", "Blood-red egg origin", "Fire-resistant scales",
                         self.second.name, "Mud Wallow"):
            self.assertIn(fragment, content)
        self.assertTrue(any(call.args[3] == "BigWings" for call in tags.call_args_list))

    def test_wallow_rest_via_map_and_button_persists_usage(self):
        fatigue = {str(dragon.id): 4 for dragon in self.world.dragons[:4]}
        self.world.world_flags["dragon_fatigue"] = fatigue
        self.fourth.health = "Injured"
        trust = self.bigwings.trust[self.second.id]

        with redirect_stdout(io.StringIO()):
            app = PygameApp(world=self.world)
        app.current_screen.draw(app.game_surface)
        app.current_screen.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=(450, 385)
        ))
        screen = app.current_screen
        screen.draw(app.game_surface)
        button = next(button for button in screen.buttons if button.label == "REST TOGETHER")
        screen.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=button.rect.center
        ))

        loaded = self.reload()
        self.assertEqual(app.current_screen_name, "mud_wallow")
        self.assertEqual(loaded.dragons[0].location, "mud_wallow")
        self.assertEqual(loaded.world_flags["dragon_fatigue"][str(self.bigwings.id)], 2)
        self.assertEqual(loaded.world_flags["dragon_fatigue"][str(self.fourth.id)], 4)
        self.assertAlmostEqual(loaded.dragons[0].trust[self.second.id], trust + 0.15)
        self.assertFalse(rest_sibs_at_wallow(loaded, self.bigwings.sib_group_id))
        loaded.moon += 1
        self.assertTrue(rest_sibs_at_wallow(loaded, self.bigwings.sib_group_id))

    def test_marsh_fire_routes_to_wallow_and_resistance_reduces_burn_risk(self):
        self.bigwings.fire_resistant = True
        self.bigwings.egg_type = "blood_red"
        with (
            patch("core.sim.mudwing.random.random", return_value=0.01),
            patch("core.sim.mudwing.random.choice", side_effect=lambda options: options[0]),
        ):
            self.assertTrue(try_marsh_fire(self.world))
        ordinary_world = self.reload()
        with redirect_stdout(io.StringIO()):
            app = PygameApp(world=self.world)
        app.check_pending_choice()
        self.assertIsNone(app.decision_popup)
        app.current_screen.open_pending_choice()
        app.check_pending_choice()
        self.assertIsNotNone(app.decision_popup)
        app.decision_popup.draw(app.game_surface)

        with patch("core.sim.mudwing.random.random", return_value=0.25):
            app.decision_popup.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1))
            outcome = resolve_choice(ordinary_world, f"rescue_{self.second.id}")
        self.assertEqual(self.bigwings.health, "Healthy")
        self.assertEqual(ordinary_world.dragons[1].health, "Injured")
        self.assertIn("suffered burns", outcome)
        self.assertEqual(self.world.food_stores, 94)
        self.assertIsNone(self.world.pending_choice)
        self.assertFalse(try_marsh_fire(self.world))

    def test_non_mudwing_tribe_has_no_wallow_or_marsh_fire(self):
        world = generate_starting_world("skywing")
        with redirect_stdout(io.StringIO()):
            screen = LocationsScreen(world, lambda _: None)
        self.assertFalse(any(location["id"] == "mud_wallow" for location in screen.locations))
        self.assertFalse(try_marsh_fire(world))
        self.assertFalse(try_mudwing_sib_decision(world))

    def test_sib_rations_routes_to_village_and_preserves_communal_reserve_choice(self):
        self.world.food_stores = 22
        self.world.tension = 1
        with (
            patch("core.sim.mudwing.random.random", return_value=0.09),
            patch("core.sim.mudwing.random.choice", side_effect=lambda options: options[0]),
            redirect_stdout(io.StringIO()),
        ):
            self.assertTrue(advance_moon(self.world))
        self.assertEqual(self.world.pending_choice["type"], "mudwing_sib_rations")
        reserved = self.reload()
        food = self.world.food_stores
        tension = self.world.tension
        trust = self.second.trust[self.bigwings.id]
        with redirect_stdout(io.StringIO()):
            app = PygameApp(world=self.world)
        app.current_screen.open_pending_choice()
        if app.current_screen_name == "locations":
            app.current_screen.enter_notice_location()
        app.check_pending_choice()
        self.assertEqual(app.current_screen_name, "village")
        app.decision_popup.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1))
        self.assertEqual(self.world.food_stores, food - 4)
        self.assertAlmostEqual(self.world.tension, tension - 0.2)
        self.assertAlmostEqual(self.second.trust[self.bigwings.id], trust + 0.5)
        resolve_choice(reserved, "reserve")
        self.assertEqual(reserved.food_stores, food)
        self.assertAlmostEqual(reserved.dragons[1].trust[self.bigwings.id], trust)

    def test_wallow_flood_costs_fatigue_or_disables_rest_until_reopening(self):
        for dragon in self.world.dragons[:4]:
            dragon.location = "mud_wallow"
        with (
            patch("core.sim.mudwing.random.random", return_value=0.01),
            patch("core.sim.mudwing.random.choice", side_effect=lambda options: options[0]),
        ):
            self.assertTrue(try_mudwing_sib_decision(self.world))
        self.assertEqual(self.world.pending_choice["type"], "mudwing_wallow_flood")
        cleared = self.reload()
        resolve_choice(cleared, "clear")
        self.assertEqual(cleared.world_flags["dragon_fatigue"][str(self.bigwings.id)], 2)
        self.assertEqual(cleared.world_flags["dragon_fatigue"][str(self.second.id)], 2)
        self.assertTrue(rest_sibs_at_wallow(cleared, self.bigwings.sib_group_id))

        with redirect_stdout(io.StringIO()):
            app = PygameApp(world=self.world)
        app.current_screen.open_pending_choice()
        app.check_pending_choice()
        self.assertEqual(app.current_screen_name, "mud_wallow")
        app.decision_popup.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2))
        closed = self.reload()
        self.assertEqual(closed.dragons[0].location, "village_center")
        app.current_screen.draw(app.game_surface)
        self.assertFalse(any(button.label == "REST TOGETHER" for button in app.current_screen.buttons))
        closed.moon += 1
        self.assertFalse(rest_sibs_at_wallow(closed, self.bigwings.sib_group_id))
        closed.moon += 1
        self.assertTrue(rest_sibs_at_wallow(closed, self.bigwings.sib_group_id))

    def lone_dragonet(self):
        dragon = generate_dragonet(50, "MudWing")
        dragon.age_moons = 5
        self.world.dragons.append(dragon)
        for group, age in enumerate((6, 10, 25)):
            for sib in self.world.dragons[group * 4:group * 4 + 4]:
                sib.age_moons = age
        return dragon

    def test_adoption_routes_to_hatchery_and_preserves_birth_history(self):
        dragon = self.lone_dragonet()
        dragon.sib_group_id = "mudwing-clutch-99"
        dragon.birth_order = 2
        dragon.parents = [self.world.dragons[8].id, self.world.dragons[9].id]
        dragon.egg_type = "blood_red"
        dragon.fire_resistant = True
        fallen_sib = generate_dragonet(51, "MudWing")
        fallen_sib.sib_group_id = dragon.sib_group_id
        fallen_sib.status = "Dead"
        self.world.dragons.append(fallen_sib)

        with redirect_stdout(io.StringIO()):
            self.assertTrue(advance_moon(self.world))
        loaded = self.reload()
        self.assertEqual(loaded.pending_choice["sib_group_id"], self.bigwings.sib_group_id)
        with redirect_stdout(io.StringIO()):
            app = PygameApp(world=loaded)
        app.current_screen.open_pending_choice()
        app.check_pending_choice()
        self.assertEqual(app.current_screen_name, "hatchery")
        app.decision_popup.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1))
        self.world = loaded
        loaded = self.reload()
        adopted, original_sib = loaded.dragons[-2:]
        bigwings = loaded.dragons[0]

        self.assertEqual(adopted.sib_group_id, bigwings.sib_group_id)
        self.assertTrue(bigwings.is_bigwings)
        self.assertFalse(adopted.is_bigwings)
        self.assertEqual(adopted.birth_sib_group_id, "mudwing-clutch-99")
        self.assertEqual(adopted.birth_order, 2)
        self.assertEqual(adopted.parents, dragon.parents)
        self.assertTrue(adopted.fire_resistant)
        self.assertEqual(adopted.egg_type, "blood_red")
        self.assertTrue(are_family(adopted, original_sib))
        self.assertTrue(are_family(adopted, bigwings))
        self.assertGreaterEqual(adopted.trust[bigwings.id], 0.5)
        self.assertTrue(any(memory.type == "welcomed_as_sibs" for memory in bigwings.memories))
        self.assertTrue(any(
            event["type"] == "hatchery" and "adopted sib" in event["text"] for event in loaded.event_log
        ))
        adopted.role = "Warrior"
        self.assertFalse(can_become_mates(adopted, bigwings))

        profile = DragonProfileScreen(loaded, lambda _: None)
        profile.select_dragon(adopted)
        profile.set_profile_tab("Sibs")
        with patch.object(profile, "draw_wrapped_text", wraps=profile.draw_wrapped_text) as lines:
            profile.draw(pygame.display.get_surface())
        content = " ".join(call.args[1] for call in lines.call_args_list)
        self.assertIn("Adopted sib", content)
        self.assertIn("Born into clutch 99", content)
        self.assertTrue(rest_sibs_at_wallow(loaded, adopted.sib_group_id))
        self.assertEqual(adopted.location, "mud_wallow")
        adopted.health = "Injured"
        self.assertIs(escort_injured_sib(loaded, adopted, [adopted, bigwings]), bigwings)

    def test_deferral_persists_and_incubating_birth_sibs_prevent_adoption(self):
        dragon = self.lone_dragonet()
        self.assertTrue(try_sib_adoption(self.world))
        resolve_choice(self.world, "wait")
        self.world = self.reload()
        self.world.moon = 2
        self.assertFalse(try_sib_adoption(self.world))
        self.world.moon = 3
        self.assertTrue(try_sib_adoption(self.world))
        self.world.pending_choice = None
        dragon = self.world.dragons[-1]
        dragon.sib_group_id = "mudwing-clutch-22"
        self.world.eggs.append(create_egg(self.bigwings, self.second, clutch_id=dragon.sib_group_id))
        self.assertFalse(try_sib_adoption(self.world))

    def test_adoptee_can_succeed_after_birth_sibs_and_does_not_count_in_hatch_order(self):
        adopted = self.lone_dragonet()
        adopted.sib_group_id = "mudwing-clutch-88"
        adopted.birth_order = 1
        self.assertTrue(try_sib_adoption(self.world))
        resolve_choice(self.world, "accept")
        group_id = self.bigwings.sib_group_id
        egg = create_egg(self.bigwings, self.second, clutch_id=group_id, hatch_time=1)
        egg["condition_score"] = 95
        self.world.eggs.append(egg)
        with redirect_stdout(io.StringIO()):
            self.assertTrue(advance_moon(self.world))
        hatchling = self.world.dragons[-1]
        self.assertNotEqual(hatchling.id, adopted.id)
        self.assertEqual(hatchling.sib_group_id, group_id)
        self.assertEqual(hatchling.birth_order, 5)

        self.bigwings.status = "Dead"
        maintain_bigwings(self.world)
        self.assertTrue(self.second.is_bigwings)
        self.assertFalse(adopted.is_bigwings)
        for sib in (self.second, self.third, self.fourth, hatchling):
            sib.status = "Dead"
        maintain_bigwings(self.world)
        self.assertTrue(adopted.is_bigwings)
