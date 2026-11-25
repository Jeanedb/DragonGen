import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pygame

from core.generator import generate_starting_world
from core.save_manager import load_world, save_world
from core.sim.choice_generation.personal import create_injured_patrol_choice
from core.sim.choices import resolve_choice
from core.sim.death import handle_possible_death
from core.sim.logging import log_event
from core.sim.memory import Memory, add_memory
from core.sim.life_story import life_story_paragraph
from ui_pygame.app import PygameApp
from ui_pygame.screens.scroll_library import ScrollLibraryScreen
from ui_pygame.screens.dragon_profile import DragonProfileScreen
from ui_pygame.screens.training_grounds import TrainingGroundsScreen


class LifeStoryTest(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.addCleanup(pygame.quit)
        self.surface = pygame.display.set_mode((1000, 700))
        self.world = generate_starting_world("seawing")

    def roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "slot.json"
            save_world(self.world, path)
            return load_world(path)

    def test_mentorship_returns_as_patrol_rescue_and_survives_log_eviction(self):
        mentor, student = self.world.dragons[:2]
        screen = TrainingGroundsScreen(self.world, lambda _: None)
        screen.training_group_a, screen.training_group_b = [mentor], [student]

        def choose_mentor_outcome(outcomes):
            return next(outcome for outcome in outcomes if outcome[0] == "mentor")

        with (
            patch("ui_pygame.screens.training_grounds.random.random", return_value=0),
            patch("ui_pygame.screens.training_grounds.random.choice", side_effect=choose_mentor_outcome),
        ):
            screen.run_training("mentor")
        self.world = self.roundtrip()
        mentor, student = self.world.dragons[:2]
        self.world.moon += 3
        with (
            patch("core.sim.choice_generation.personal.get_most_hostile_relation", return_value=(None, 0)),
            patch("core.sim.choice_generation.personal.random.choices", return_value=[(mentor, student)]),
        ):
            self.assertTrue(create_injured_patrol_choice(self.world))
        self.assertIn("chance to return the favour", self.world.pending_choice["text"])
        trust = mentor.trust.get(student.id, 0)
        with patch("core.sim.choice_handlers.personal.random.random", return_value=0.9):
            outcome = resolve_choice(self.world, "stay_and_help")
        self.assertIn("Both will remember the rescue.", outcome.splitlines()[0])
        self.assertAlmostEqual(mentor.trust[student.id], trust + 3)
        self.assertTrue(any(m.type == "helped_by_former_student" for m in mentor.memories))

        mentor.age_moons = 260
        with patch("core.sim.death.random.random", return_value=0):
            self.assertTrue(handle_possible_death(self.world, mentor))
        self.assertGreater(student.grief_level, 0)
        self.world.event_log.clear()
        self.world = self.roundtrip()
        profile = DragonProfileScreen(self.world, lambda _: None)
        story = profile.get_dragon_events(self.world.dragons[1])
        self.assertEqual(
            [event["type"] for event in story],
            ["returned_mentor_help", "lost_mentor", "mentored_by"],
        )
        self.assertTrue(all(mentor.name in event["text"] for event in story))

        student = self.world.dragons[1]
        other = self.world.dragons[2]
        other.name = "Unrelated Dragon"
        add_memory(student, Memory("mentored_by", 2, other.id, importance=10))
        paragraph = life_story_paragraph(student, self.world)
        self.assertNotIn(other.name, paragraph)
        self.assertLess(paragraph.index("learned from"), paragraph.index("stayed to help"))
        self.assertLess(paragraph.index("stayed to help"), paragraph.index("mourned"))
        library = ScrollLibraryScreen(self.world, lambda _: None)
        library.select_dragon(student)
        with patch.object(library, "draw_wrapped", wraps=library.draw_wrapped) as render:
            library.draw_biography_tab(self.surface, pygame.Rect(323, 180, 649, 425))
        sections = [call.args[1] for call in render.call_args_list]
        at = sections.index("LIFE STORY")
        self.assertEqual(sections[at + 1], paragraph)
        self.assertEqual(sections[at + 2], "ABOUT THIS DRAGON")

    def test_new_dragon_has_no_invented_life_story(self):
        self.assertEqual(life_story_paragraph(self.world.dragons[0], self.world), "")

    def test_chronicle_link_opens_fallen_dragon_and_back_restores_view(self):
        first, mentor = self.world.dragons[:2]
        mentor.status = "Dead"
        self.world.world_flags["followed_dragons"] = [first.id]
        add_memory(first, Memory("mentored_by", 0, mentor.id, importance=4))
        for moon in range(1, 8):
            self.world.moon = moon
            log_event(self.world, "A quiet patrol.", [first.id], "border", importance=2)
        app = PygameApp(world=self.world)
        app.change_screen("dragon_profile")
        profile = app.current_screen
        profile.set_status_filter("Following")
        profile.set_profile_tab("History")
        profile.set_history_mode("Full Chronicle")
        profile.draw(app.game_surface)
        self.assertFalse(any(
            424 <= button.rect.x < 930 and 379 <= button.rect.y < 604
            for button in profile.buttons
        ))

        profile.detail_scroll = -(profile.detail_content_height - profile.detail_view_height)
        original_scroll = profile.detail_scroll
        profile.draw(app.game_surface)
        link = next(button for button in profile.buttons if 424 <= button.rect.x < 930
                    and 379 <= button.rect.y < 604)
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=link.rect.center))
        self.assertEqual(profile.selected_dragon.id, mentor.id)
        self.assertEqual(profile.history_mode, "Full Chronicle")
        self.assertEqual(profile.detail_scroll, 0)
        self.assertEqual(profile.status_filter, "All")

        profile.draw(app.game_surface)
        back = next(button for button in profile.buttons if getattr(button, "label", "") == f"BACK TO {first.name}")
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=back.rect.center))
        self.assertEqual(profile.selected_dragon.id, first.id)
        self.assertEqual(profile.detail_scroll, original_scroll)
        self.assertEqual(profile.status_filter, "Following")

    def test_follow_from_rescue_result_and_keep_continue_independent(self):
        injured, helper = self.world.dragons[:2]
        app = PygameApp(world=self.world)
        app.change_screen("healer_den")

        def rescue():
            self.world.pending_choice = {
                "type": "injured_patrol_choice", "location": "healer_den",
                "injured_id": injured.id, "helper_id": helper.id,
                "options": [{"id": "stay_and_help", "text": "Stay and help"}],
            }
            app.check_pending_choice()
            with patch("core.sim.choice_handlers.personal.random.random", return_value=0.9):
                app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1))

        rescue()
        self.assertEqual(app.decision_popup.options[1]["text"], f"Follow {helper.name}")
        app.decision_popup.draw(app.game_surface)
        app.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=app.decision_popup.button_rects[1].center,
        ))
        self.assertEqual(app.decision_popup.options[1]["text"], f"Following {helper.name}")
        app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2))
        self.assertEqual(self.world.world_flags["followed_dragons"], [helper.id])
        app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        self.assertIsNone(app.decision_popup)
        rescue()
        self.assertEqual([option["id"] for option in app.decision_popup.options], ["continue"])
        loaded = self.roundtrip()
        profile = DragonProfileScreen(loaded, lambda _: None)
        profile.set_status_filter("Following")
        self.assertEqual([dragon.id for dragon in profile.get_filtered_dragons()], [helper.id])

    def test_unremarkable_result_has_no_follow_prompt(self):
        app = PygameApp(world=self.world)
        app.change_screen("healer_den")
        injured, helper = self.world.dragons[:2]
        self.world.pending_choice = {
            "type": "injured_patrol_choice", "location": "healer_den",
            "injured_id": injured.id, "helper_id": helper.id,
            "options": [{"id": "run_for_help", "text": "Go for help"}],
        }
        app.check_pending_choice()
        with patch("core.sim.choice_handlers.personal.random.random", return_value=0.9):
            app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1))
        self.assertEqual([option["id"] for option in app.decision_popup.options], ["continue"])

    def test_following_filter_keeps_fallen_dragons_after_reload(self):
        dragon = self.world.dragons[0]
        profile = DragonProfileScreen(self.world, lambda _: None)
        profile.select_dragon(dragon)
        profile.draw(self.surface)
        for label in ("FOLLOW", "FOLLOWING"):
            button = next(button for button in profile.buttons if getattr(button, "label", "") == label)
            profile.handle_event(pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, button=1, pos=button.rect.center
            ))
            profile.draw(self.surface)
        self.assertEqual([d.id for d in profile.get_filtered_dragons()], [dragon.id])
        dragon.status = "Dead"
        reloaded = DragonProfileScreen(self.roundtrip(), lambda _: None)
        reloaded.set_status_filter("Following")
        self.assertEqual([d.id for d in reloaded.get_filtered_dragons()], [dragon.id])

    def test_overview_surfaces_recent_major_events_and_opens_fallen_history(self):
        followed, mentor, other = self.world.dragons[:3]
        self.world.moon = 7
        self.world.world_flags["followed_dragons"] = [followed.id]
        add_memory(followed, Memory("mentored_by", 6, mentor.id, importance=4))
        log_event(self.world, "An ordinary patrol.", [followed.id], "border", importance=2)
        log_event(self.world, "Unfollowed dragon gained a title.", [other.id], "title_gain", importance=6)
        log_event(self.world, f"{followed.name} died.", [followed.id], "death", importance=5)
        followed.status = "Dead"
        app = PygameApp(world=self.roundtrip())
        app.change_screen("dashboard")
        dashboard = app.current_screen
        entries = dashboard.get_followed_updates()
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0][3], f"{followed.name} died.")
        self.assertIn(mentor.name, entries[1][3])
        dashboard.draw(app.game_surface)
        app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(500, 155)))
        self.assertEqual(app.current_screen_name, "dragon_profile")
        self.assertEqual(app.current_screen.selected_dragon.id, followed.id)
        self.assertEqual(app.current_screen.profile_tab, "History")
        self.assertEqual(app.current_screen.history_mode, "Full Chronicle")
