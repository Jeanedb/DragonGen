import random
import pygame
from pathlib import Path

from core.sim.memory import Memory, add_memory, current_moon
from core.sim.relationships import strengthen_relationship, weaken_relationship
from core.sim.behavior import get_behavior_score
from core.sim.logging import log_event
from ui_pygame.core.base_screen import BaseScreen

WIDTH, HEIGHT = 1000, 700

TEXT = (236, 222, 196)
MUTED = (176, 158, 132)
GOLD = (227, 183, 84)
BRONZE = (133, 91, 53)
RED = (205, 82, 66)
GREEN = (111, 178, 120)
CREAM = (248, 230, 192)
TEAM_A = (211, 158, 65)
TEAM_B = (182, 71, 59)

def world_moon_safe(world):
    return getattr(world, "moon", 0)


def find_project_root():
    """Find the project folder without depending on this file's depth."""
    file_path = Path(__file__).resolve()
    candidates = [file_path.parent, *file_path.parents, Path.cwd(), *Path.cwd().parents]
    checked = set()

    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in checked:
            continue
        checked.add(candidate)
        if (candidate / "assets").is_dir():
            return candidate

    return file_path.parents[2]


class ClickTarget:
    def __init__(self, rect, callback):
        self.rect = pygame.Rect(rect)
        self.callback = callback

    def handle_event(self, event):
        if (
            event.type == pygame.MOUSEBUTTONUP
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        ):
            self.callback()


class TrainingButton(ClickTarget):
    def __init__(self, rect, label, callback, enabled=True, primary=False, selected=False):
        super().__init__(rect, callback)
        self.label = label
        self.enabled = enabled
        self.primary = primary
        self.selected = selected

    def handle_event(self, event):
        if self.enabled:
            super().handle_event(event)

    def draw(self, screen, font, mouse_pos):
        hovered = self.enabled and self.rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (8, 5, 4), self.rect.move(0, 4), border_radius=8)

        if not self.enabled:
            edge, fill, text_color = (78, 70, 61), (43, 40, 36), (120, 113, 101)
        elif self.selected:
            edge, fill, text_color = GOLD, (87, 55, 29), CREAM
        elif self.primary:
            edge = GOLD if hovered else (177, 121, 53)
            fill = (105, 62, 29) if hovered else (74, 47, 28)
            text_color = CREAM
        else:
            edge = GOLD if hovered else (111, 80, 55)
            fill = (64, 48, 36) if hovered else (43, 36, 32)
            text_color = TEXT

        pygame.draw.rect(screen, edge, self.rect, border_radius=8)
        inner = self.rect.inflate(-5, -5)
        pygame.draw.rect(screen, fill, inner, border_radius=6)
        pygame.draw.line(
            screen,
            (213, 167, 94) if self.enabled else (76, 70, 62),
            (inner.left + 8, inner.top + 3),
            (inner.right - 8, inner.top + 3),
            1,
        )
        image = font.render(self.label, True, text_color)
        screen.blit(image, image.get_rect(center=self.rect.center))

class TrainingGroundsScreen(BaseScreen):

    def __init__(self, world, change_screen):
        super().__init__()

        self.training_group_a = []
        self.training_group_b = []
        self.training_mode = "sparring"

        self.world = world
        self.change_screen = change_screen
        self.log_scroll = 0

        self.selected_dragon = None
        self.list_scroll = 0

        self.selected_partner = None

        self.fantasy_title = pygame.font.SysFont("georgia", 30, bold=True)
        self.fantasy_heading = pygame.font.SysFont("georgia", 18, bold=True)
        self.fantasy_body = pygame.font.SysFont("georgia", 14)
        self.fantasy_body_bold = pygame.font.SysFont("georgia", 14, bold=True)
        self.fantasy_small = pygame.font.SysFont("georgia", 12)
        self.fantasy_tiny = pygame.font.SysFont("georgia", 11)
        self.medallion_font = pygame.font.SysFont("georgia", 16, bold=True)

        project_root = find_project_root()
        tribe_slug = (
            str(getattr(self.world, "tribe_name", ""))
            .lower()
            .replace(" tribe", "")
            .replace(" ", "")
        )
        tribe_bg = project_root / "assets" / tribe_slug / "training_grounds_bg.png"
        default_bg = project_root / "assets" / "menu" / "training_bg.png"
        bg_path = tribe_bg if tribe_bg.exists() else default_bg

        try:
            self.bg_image = pygame.image.load(str(bg_path)).convert()
            self.bg_image = pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT))
        except Exception as error:
            print(f"Could not load training background: {error}")
            self.bg_image = None

    def get_selected_dragon(self):
        dragons = self.get_dragons()

        if self.selected_dragon in dragons:
            return self.selected_dragon

        if dragons:
            self.selected_dragon = dragons[0]
            return self.selected_dragon

        return None

    def get_training_partner(self):
        if self.training_group_b:
            return self.training_group_b[0]

        return None

    def get_dragons(self):
        return [
            d for d in getattr(self.world, "dragons", [])
            if getattr(d, "status", "") == "Alive"
            and getattr(d, "role", "") != "Dragonet"
        ]

    def add_training_event(self, text, involved_ids=None, importance=2):
        log_event(
            self.world,
            text,
            involved_ids=involved_ids or [],
            event_type="training",
            importance=importance,
        )

    def run_training(self, training_type):

        dragons = self.get_dragons()

        if training_type == "team":
            if len(self.training_group_a) < 1 or len(self.training_group_b) < 1:
                return
        else:
            if len(self.training_group_a) != 1 or len(self.training_group_b) != 1:
                return

        if len(dragons) < 2:
            return

        a = self.training_group_a[0]

        others = [d for d in dragons if d != a]

        if not a or not others:
            return

        training_score = self.get_training_score(a, training_type)

        b = self.training_group_b[0]

        if not b:
            return

        if training_type == "sparring":
            outcomes = [
                ("impress", f"{a.name} impressed the tribe during sparring drills."),
                ("challenge", f"{a.name} challenged {b.name} aggressively during sparring."),
                (
                    "embarrass",
                    f"{a.name} embarrassed {b.name} in front of the others.",
                    f"{b.name} resents {a.name} more."
                ),
                ("strain", f"{a.name} pushed too hard and the training session turned tense."),
            ]

        elif training_type == "team":
            outcomes = [
                (
                    "bond",
                    f"{a.name} and {b.name} worked well together.",
                    f"{a.name} and {b.name} trust each other more."
                ),
                ("bond", f"{a.name} helped {b.name} recover after a difficult exercise."),
                ("strain", f"The team drills became disorganized and frustration spread."),
            ]

        elif training_type == "mentor":
            outcomes = [
                ("mentor", f"{a.name} took time to mentor younger dragons."),
                ("bond", f"{a.name} and {b.name} grew closer during guided training."),
                ("impress", f"{a.name}'s patience during training was noticed by the tribe."),
            ]

        else:
            return

        success_bias = training_score / 2.0

        if training_type == "team":
            team_dragons = self.training_group_a + self.training_group_b

            cooperation_scores = [
                get_behavior_score(dragon, "cooperation")
                for dragon in team_dragons
            ]

            if cooperation_scores:
                average_cooperation = sum(cooperation_scores) / len(cooperation_scores)

                cooperation_modifier = (average_cooperation - 0.5) * 0.30
                success_bias += cooperation_modifier

        success_bias = max(0.05, min(0.95, success_bias))

        if random.random() < success_bias:
            good_outcomes = [o for o in outcomes if o[0] in {"impress", "bond", "mentor"}]
            chosen = random.choice(good_outcomes)

        else:
            bad_outcomes = [o for o in outcomes if o[0] in {"strain", "challenge", "embarrass"}]

            if training_type == "sparring":
                aggression = get_behavior_score(a, "aggression")

                weights = []

                for outcome in bad_outcomes:
                    if outcome[0] == "challenge":
                        weights.append(0.5 + aggression)
                    elif outcome[0] == "embarrass":
                        weights.append(0.75)
                    else:
                        weights.append(1.0)

                chosen = random.choices(
                    bad_outcomes,
                    weights=weights,
                    k=1
                )[0]

            else:
                chosen = random.choice(bad_outcomes or outcomes)

        outcome_type = chosen[0]
        text = chosen[1]
        effect_text = chosen[2] if len(chosen) > 2 else self.get_training_effect_text(a, b, outcome_type)

        if training_type == "team":
            for team_a_dragon in self.training_group_a:
                for team_b_dragon in self.training_group_b:
                    self.apply_training_effect(team_a_dragon, team_b_dragon, outcome_type)

            skill_a = sum(getattr(d, "combat_skill", 0) for d in self.training_group_a)
            skill_b = sum(getattr(d, "combat_skill", 0) for d in self.training_group_b)

            if skill_a >= skill_b:
                winners = self.training_group_a
                losers = self.training_group_b
                winning_team_name = "Team A"
            else:
                winners = self.training_group_b
                losers = self.training_group_a
                winning_team_name = "Team B"

            for dragon in winners:
                add_memory(
                    dragon,
                    Memory(
                        type="won_team_drill",
                        moon=current_moon(self.world),
                        importance=3,
                        tags=["training", "team", "success"]
                    )
                )

                dragon.reputation["reliable"] = (
                    dragon.reputation.get("reliable", 0) + 0.1
                )

            for dragon in losers:
                add_memory(
                    dragon,
                    Memory(
                        type="lost_team_drill",
                        moon=current_moon(self.world),
                        importance=2,
                        tags=["training", "team", "failure"]
                    )
                )

            text += f" {winning_team_name} performed better overall."
        else:
            self.apply_training_effect(a, b, outcome_type)
        if training_type == "team":
            involved_ids = [
                dragon.id
                for dragon in self.training_group_a + self.training_group_b
            ]
        else:
            involved_ids = [a.id, b.id]

        importance = {
            "impress": 3,
            "bond": 3,
            "mentor": 3,
            "strain": 2,
            "challenge": 3,
            "embarrass": 4,
        }.get(outcome_type, 2)

        self.add_training_event(
            f"{text}\n    {effect_text}",
            involved_ids=list(dict.fromkeys(involved_ids)),
            importance=importance,
        )

    def get_training_effect_text(self, a, b, outcome_type):
        if outcome_type == "bond":
            return f"{a.name} and {b.name} trust each other more."

        if outcome_type == "embarrass":
            return f"{b.name} resents {a.name} more."

        if outcome_type == "strain":
            return "The tribe feels slightly more tense."

        if outcome_type == "challenge":
            return f"Tension between {a.name} and {b.name} increased."

        if outcome_type == "impress":
            return f"{a.name}'s reputation improved."

        if outcome_type == "mentor":
            return f"{a.name} gained respect as a mentor."

        return "The training left a mark."


    def add_memory(self, dragon, memory):
        if not hasattr(dragon, "memory_flags") or dragon.memory_flags is None:
            dragon.memory_flags = []

        if memory not in dragon.memory_flags:
            dragon.memory_flags.append(memory)


    def apply_training_effect(self, a, b, outcome_type):

        if outcome_type == "bond":
            a.trust[b.id] = a.trust.get(b.id, 0) + 0.4
            b.trust[a.id] = b.trust.get(a.id, 0) + 0.4

            memory_a = Memory(
                type="trained_well_with",
                moon=current_moon(self.world),
                other_id=b.id,
                importance=2,
                tags=["training", "bond"]
            )

            memory_b = Memory(
                type="trained_well_with",
                moon=current_moon(self.world),
                other_id=a.id,
                importance=2,
                tags=["training", "bond"]
            )

            add_memory(a, memory_a)
            add_memory(b, memory_b)

            strengthen_relationship(a, b.id, 0.4, self.world, "bond", memory_a)
            strengthen_relationship(b, a.id, 0.4, self.world, "bond", memory_b)

        elif outcome_type == "embarrass":
            embarrasser_memory = Memory(
                type="embarrassed",
                moon=current_moon(self.world),
                other_id=b.id,
                importance=3,
                tags=["training", "humiliation", "rivalry"]
            )

            victim_memory = Memory(
                type="was_embarrassed_by",
                moon=current_moon(self.world),
                other_id=a.id,
                importance=4,
                tags=["training", "humiliation", "rivalry"]
            )

            add_memory(a, embarrasser_memory)
            add_memory(b, victim_memory)

            weaken_relationship(b, a.id, 0.3, self.world, "bond", victim_memory)
            strengthen_relationship(b, a.id, 0.5, self.world, "rivalry", victim_memory)

        elif outcome_type == "strain":
            self.world.tension += 0.08
            a.reputation["harsh"] = a.reputation.get("harsh", 0) + 0.1

        elif outcome_type == "challenge":
            a.resentment[b.id] = a.resentment.get(b.id, 0) + 0.3
            b.resentment[a.id] = b.resentment.get(a.id, 0) + 0.3

            challenger_memory = Memory(
                type="challenged",
                moon=current_moon(self.world),
                other_id=b.id,
                importance=3,
                tags=["training", "challenge", "rivalry"]
            )

            challenged_memory = Memory(
                type="was_challenged_by",
                moon=current_moon(self.world),
                other_id=a.id,
                importance=3,
                tags=["training", "challenge", "rivalry"]
            )

            add_memory(a, challenger_memory)
            add_memory(b, challenged_memory)

            strengthen_relationship(
                a,
                b.id,
                0.3,
                self.world,
                "rivalry",
                challenger_memory
            )

            strengthen_relationship(
                b,
                a.id,
                0.3,
                self.world,
                "rivalry",
                challenged_memory
            )

        elif outcome_type == "impress":
            a.reputation["kind"] = a.reputation.get("kind", 0) + 0.2
            
            if a.combat_skill < 20:
                a.combat_skill += 1

        elif outcome_type == "mentor":

            a.reputation["kind"] = a.reputation.get("kind", 0) + 0.3
            b.trust[a.id] = b.trust.get(a.id, 0) + 0.6

            mentor_memory = Memory(
                type="mentored",
                moon=current_moon(self.world),
                other_id=b.id,
                importance=3,
                tags=["training", "mentor"]
            )

            student_memory = Memory(
                type="mentored_by",
                moon=current_moon(self.world),
                other_id=a.id,
                importance=4,
                tags=["training", "mentor"]
            )

            add_memory(a, mentor_memory)
            add_memory(b, student_memory)

            strengthen_relationship(a, b.id, 0.5, self.world, "mentor", mentor_memory)
            strengthen_relationship(b, a.id, 0.7, self.world, "student", student_memory)



    def get_training_score(self, dragon, training_type):
        score = 1.0

        if dragon.role == "Warrior":
            score += 0.6
        elif dragon.role == "Hunter":
            score += 0.2
        elif dragon.role == "Scout":
            score += 0.15
        elif dragon.role == "Healer":
            score -= 0.1
        elif dragon.role == "Elder":
            score -= 0.2
        elif dragon.role == "Dragonet":
            score -= 0.8

        if dragon.health == "Injured":
            score -= 0.7

        if training_type == "team":
            score -= 0.1
        elif training_type == "mentor":
            score += 0.1

        return max(0.1, score)

    def draw_panel_legacy(self, screen, rect, alpha=185):
        surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        surf.fill((28, 28, 28, alpha))
        screen.blit(surf, rect.topleft)

        pygame.draw.rect(
            screen,
            (55, 55, 55),
            rect,
            width=1,
            border_radius=14
        )

    def draw_legacy(self, screen):

        self.buttons.clear()

        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill((18, 18, 18))

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 130))
        screen.blit(overlay, (0, 0))

        title = self.title_font.render("Training Grounds", True, TEXT)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 70)))

        subtitle = self.small.render(
            "Train dragons, build rivalries, and strengthen the tribe.",
            True,
            MUTED
        )
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 110)))

        left = pygame.Rect(60, 150, 240, 455)
        center = pygame.Rect(330, 150, 300, 455)
        right = pygame.Rect(660, 150, 280, 455)

        self.draw_panel(screen, left)
        self.draw_panel(screen, center)
        self.draw_panel(screen, right)

        self.draw_text(
            screen,
            "Training Log",
            right.x + 18,
            right.y + 18,
            self.section_font,
            GOLD
        )

        self.draw_text(
            screen,
            "Recent Events",
            right.x + 33,
            right.y + 65,
            self.small,
            GOLD
        )

        self.draw_text(
            screen,
            "Available Dragons",
            left.x + 18,
            left.y + 18,
            self.section_font,
            GOLD
        )

        self.draw_text(
            screen,
            "Training Ring",
            center.x + 18,
            center.y + 18,
            self.section_font,
            GOLD
        )

        arena_rect = pygame.Rect(
            center.x + 30,
            center.y + 65,
            240,
            160
        )

        pygame.draw.rect(
            screen,
            (50, 42, 35),
            arena_rect,
            border_radius=10
        )

        pygame.draw.rect(
            screen,
            GOLD,
            arena_rect,
            width=1,
            border_radius=8
        )

        dragons = self.get_dragons()
        selected = self.get_selected_dragon()
        partner = self.get_training_partner()

        if self.training_group_a or self.training_group_b:

            def draw_team_grid(team, start_y):

                positions = [
                    (center.x + 50,  start_y),
                    (center.x + 140, start_y),
                    (center.x + 50,  start_y + 26),
                ]

                for i, dragon in enumerate(team[:3]):

                    x, y = positions[i]

                    self.draw_text(
                        screen,
                        dragon.name[:10],
                        x,
                        y,
                        self.small,
                        TEXT
                    )

            self.draw_text(
                screen,
                "TEAM A",
                center.centerx - 35,
                center.y + 75,
                self.small,
                GOLD
            )

            draw_team_grid(self.training_group_a, center.y + 98)

            self.draw_text(
                screen,
                "TEAM B",
                center.centerx - 35,
                center.y + 157,
                self.small,
                RED
            )

            self.draw_text(
                screen,
                "VS",
                center.centerx - 23,
                center.y + 125,
                self.section_font,
                GOLD
            )

            draw_team_grid(self.training_group_b, center.y + 178)

            skill_a = sum(getattr(d, "combat_skill", 0) for d in self.training_group_a)
            skill_b = sum(getattr(d, "combat_skill", 0) for d in self.training_group_b)

            self.draw_text(
                screen,
                f"Skill: {skill_a} vs {skill_b}",
                center.x + 100,
                center.y + 230,
                self.small,
                MUTED
            )

        else:
            self.draw_text(
                screen,
                "Select dragons",
                center.x + 85,
                center.y + 180,
                self.font,
                MUTED
            )


        self.draw_text(
            screen,
            "Available Dragons:",
            left.x + 22,
            left.y + 65,
            self.small,
            GOLD
        )

        list_rect = pygame.Rect(left.x + 20, left.y + 90, left.width - 40, 305)
        self.draw_panel(screen, list_rect, alpha=120)

        old_clip = screen.get_clip()
        screen.set_clip(list_rect)

        y = list_rect.y + 8 + self.list_scroll

        for dragon in self.get_dragons():
            btn_rect = pygame.Rect(list_rect.x + 8, y, list_rect.width - 16, 28)

            if btn_rect.bottom >= list_rect.top and btn_rect.top <= list_rect.bottom:
                btn = Button(
                    (btn_rect.x, btn_rect.y, btn_rect.width, btn_rect.height),
                    dragon.name,
                    lambda d=dragon: self.select_dragon(d)
                )
                self.buttons.append(btn)
                btn.draw(screen, self.small)

                if dragon in self.training_group_a:
                    pygame.draw.rect(screen, GOLD, btn_rect, width=2, border_radius=6)
                elif dragon in self.training_group_b:
                    pygame.draw.rect(screen, RED, btn_rect, width=2, border_radius=6)

            y += 34

        screen.set_clip(old_clip)

        buttons = [
            ("Sparring", "sparring"),
            ("Team Drills", "team"),
            ("Mentorship", "mentor"),
        ]

        btn_y = center.y + 250

        for label, training_type in buttons:
            btn = Button(
                (center.x + 55, btn_y, 190, 42),
                label,
                lambda t=training_type: self.set_training_mode(t)
            )

            self.buttons.append(btn)
            btn.draw(screen, self.font)

            if self.training_mode == training_type:
                pygame.draw.rect(
                    screen,
                    GOLD,
                    pygame.Rect(center.x + 55, btn_y, 190, 42),
                    width=2,
                    border_radius=8
                )

            btn_y += 55

        valid_training = False

        if self.training_mode == "team":
            valid_training = (
                len(self.training_group_a) >= 1
                and len(self.training_group_b) >= 1
            )
        else:
            valid_training = (
                len(self.training_group_a) == 1
                and len(self.training_group_b) == 1
            )

        if valid_training:
            start_btn = Button(
                (center.x + 55, center.y + 425, 190, 42),
                "Begin Training",
                lambda: self.run_training(self.training_mode)
            )

            self.buttons.append(start_btn)
            start_btn.draw(screen, self.font)

        else:
            disabled_rect = pygame.Rect(
                center.x + 55,
                center.y + 425,
                190,
                42
            )

            pygame.draw.rect(
                screen,
                (70, 70, 70),
                disabled_rect,
                border_radius=8
            )

            self.draw_text(
                screen,
                "Select Teams",
                disabled_rect.x + 45,
                disabled_rect.y + 10,
                self.font,
                MUTED
            )

        log_rect = pygame.Rect(
            right.x + 18,
            right.y + 60,
            right.width - 36,
            right.height - 78
        )

        self.draw_panel(screen, log_rect, alpha=150)

        events = getattr(self.world, "event_log", [])

        training_events = [
            e for e in events
            if isinstance(e, dict)
            and e.get("type") == "training"
        ]

        old_clip = screen.get_clip()
        screen.set_clip(log_rect)

        y = log_rect.y + 12 + self.log_scroll

        for event in reversed(training_events[-25:]):

            text = f"- {event.get('text', '')}"

            self.draw_wrapped_text(
                screen,
                text,
                log_rect.x + 12,
                y,
                log_rect.width - 24,
                self.small,
                TEXT
            )

            y += 70

        screen.set_clip(old_clip)

        return_btn = Button(
            (410, 635, 140, 38),
            "Return",
            lambda: self.change_screen("locations")
        )

        self.buttons.append(return_btn)
        return_btn.draw(screen, self.font)

    def draw_beveled_panel(self, screen, rect, fill=(28, 23, 20, 224), edge=BRONZE, cut=12):
        rect = pygame.Rect(rect)
        x, y, width, height = rect
        points = [
            (x + cut, y),
            (x + width - cut, y),
            (x + width, y + cut),
            (x + width, y + height - cut),
            (x + width - cut, y + height),
            (x + cut, y + height),
            (x, y + height - cut),
            (x, y + cut),
        ]
        pygame.draw.polygon(screen, (8, 5, 4), [(px, py + 5) for px, py in points])
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        local_points = [(px - x, py - y) for px, py in points]
        pygame.draw.polygon(panel, fill, local_points)
        screen.blit(panel, rect.topleft)
        pygame.draw.lines(screen, edge, True, points, 2)
        pygame.draw.line(
            screen,
            (208, 163, 94),
            (x + cut + 8, y + 5),
            (x + width - cut - 8, y + 5),
            1,
        )

    def draw_medallion(self, screen, center, label, color, radius=20):
        x, y = center
        pygame.draw.circle(screen, (8, 5, 4), (x, y + 3), radius + 5)
        pygame.draw.circle(screen, (121, 87, 55), center, radius + 4)
        pygame.draw.circle(screen, (33, 27, 23), center, radius)
        pygame.draw.circle(screen, color, center, radius - 5)
        pygame.draw.arc(
            screen,
            tuple(min(255, channel + 40) for channel in color),
            (x - radius + 8, y - radius + 8, (radius - 8) * 2, (radius - 8) * 2),
            0.55,
            2.5,
            2,
        )
        image = self.medallion_font.render(label, True, CREAM)
        screen.blit(image, image.get_rect(center=center))

    def draw_scroll_track(self, screen, rect, scroll, content_height, visible_height):
        if content_height <= visible_height:
            return
        pygame.draw.line(screen, (91, 66, 48), rect.midtop, rect.midbottom, 2)
        maximum = content_height - visible_height
        ratio = min(1.0, -scroll / maximum) if maximum else 0
        handle_y = rect.top + int(ratio * rect.height)
        pygame.draw.circle(screen, GOLD, (rect.centerx, handle_y), 4)

    def training_is_ready(self):
        if self.training_mode == "team":
            return len(self.training_group_a) >= 1 and len(self.training_group_b) >= 1
        return len(self.training_group_a) == 1 and len(self.training_group_b) == 1

    def get_mode_description(self):
        descriptions = {
            "sparring": "A focused one-on-one contest. Skill and aggression shape the result.",
            "team": "Up to three dragons per side. Cooperation can matter as much as strength.",
            "mentor": "Pair an experienced dragon with a partner for guided instruction.",
        }
        return descriptions.get(self.training_mode, "Choose a training exercise.")

    def get_training_events(self):
        events = getattr(self.world, "event_log", [])
        return [
            event
            for event in events
            if isinstance(event, dict) and event.get("type") == "training"
        ]

    def draw_roster(self, screen, rect, mouse_pos):
        self.draw_beveled_panel(screen, rect, fill=(27, 23, 21, 230), edge=(111, 76, 50), cut=12)
        dragons = self.get_dragons()

        screen.blit(self.fantasy_heading.render("TRAINING ROSTER", True, GOLD), (rect.x + 16, rect.y + 15))
        screen.blit(
            self.fantasy_small.render(f"{len(dragons)} dragons eligible", True, MUTED),
            (rect.x + 16, rect.y + 42),
        )
        pygame.draw.line(screen, (112, 78, 51), (rect.x + 16, rect.y + 66), (rect.right - 16, rect.y + 66), 1)

        area = pygame.Rect(rect.x + 12, rect.y + 78, rect.width - 24, rect.height - 96)
        old_clip = screen.get_clip()
        screen.set_clip(area)

        if not dragons:
            screen.blit(self.fantasy_body.render("No dragons can train.", True, MUTED), (area.x + 10, area.y + 18))
        else:
            y = area.y + self.list_scroll
            for dragon in dragons:
                row = pygame.Rect(area.x, y, area.width - 5, 55)
                team = "A" if dragon in self.training_group_a else "B" if dragon in self.training_group_b else None
                hovered = row.collidepoint(mouse_pos)

                if team == "A":
                    edge, fill = TEAM_A, (72, 50, 31)
                elif team == "B":
                    edge, fill = TEAM_B, (67, 39, 34)
                else:
                    edge = (128, 82, 52) if hovered else (76, 58, 46)
                    fill = (52, 41, 35) if hovered else (37, 32, 29)

                pygame.draw.rect(screen, fill, row, border_radius=8)
                pygame.draw.rect(screen, edge, row, width=2 if team else 1, border_radius=8)
                badge_color = TEAM_A if team == "A" else TEAM_B if team == "B" else (82, 72, 62)
                self.draw_medallion(screen, (row.x + 27, row.centery), team or "–", badge_color, 16)

                screen.blit(self.fantasy_body_bold.render(str(dragon.name), True, CREAM), (row.x + 51, row.y + 7))
                details = f"{getattr(dragon, 'role', 'Unknown')}  •  Skill {getattr(dragon, 'combat_skill', 0)}"
                screen.blit(self.fantasy_tiny.render(details, True, MUTED), (row.x + 51, row.y + 30))

                if row.colliderect(area):
                    self.buttons.append(ClickTarget(row, lambda selected=dragon: self.select_dragon(selected)))
                y += 64

        screen.set_clip(old_clip)
        self.draw_scroll_track(
            screen,
            pygame.Rect(rect.right - 10, area.y + 4, 2, area.height - 8),
            self.list_scroll,
            len(dragons) * 64,
            area.height,
        )

        hint = self.fantasy_tiny.render("Click: Team A → Team B → remove", True, MUTED)
        screen.blit(hint, hint.get_rect(center=(rect.centerx, rect.bottom - 12)))

    def draw_team_side(self, screen, rect, team, label, color):
        pygame.draw.rect(screen, (38, 31, 27), rect, border_radius=9)
        pygame.draw.rect(screen, color, rect, width=2, border_radius=9)
        label_image = self.fantasy_small.render(label, True, color)
        screen.blit(label_image, label_image.get_rect(center=(rect.centerx, rect.y + 16)))

        if not team:
            empty = self.fantasy_small.render("Unassigned", True, MUTED)
            screen.blit(empty, empty.get_rect(center=(rect.centerx, rect.centery + 8)))
            return

        y = rect.y + 37
        for dragon in team[:3]:
            member = pygame.Rect(rect.x + 8, y, rect.width - 16, 31)
            pygame.draw.rect(screen, (52, 42, 34), member, border_radius=6)
            name = self.fantasy_small.render(str(dragon.name)[:13], True, TEXT)
            skill = self.fantasy_tiny.render(str(getattr(dragon, "combat_skill", 0)), True, color)
            screen.blit(name, (member.x + 8, member.y + 8))
            screen.blit(skill, (member.right - skill.get_width() - 8, member.y + 9))
            y += 35

    def draw_skill_balance(self, screen, rect, skill_a, skill_b):
        total = max(1, skill_a + skill_b)
        split = int(rect.width * skill_a / total)
        pygame.draw.rect(screen, (22, 18, 16), rect, border_radius=5)
        if split:
            pygame.draw.rect(screen, TEAM_A, (rect.x, rect.y, split, rect.height), border_radius=5)
        if rect.width - split:
            pygame.draw.rect(screen, TEAM_B, (rect.x + split, rect.y, rect.width - split, rect.height), border_radius=5)
        pygame.draw.line(screen, CREAM, (rect.centerx, rect.y - 2), (rect.centerx, rect.bottom + 2), 1)

    def draw_arena(self, screen, rect, mouse_pos):
        self.draw_beveled_panel(screen, rect, fill=(29, 24, 21, 235), edge=(124, 85, 51), cut=13)
        screen.blit(self.fantasy_heading.render("THE TRAINING RING", True, GOLD), (rect.x + 18, rect.y + 15))
        pygame.draw.line(screen, (118, 81, 50), (rect.x + 18, rect.y + 43), (rect.right - 18, rect.y + 43), 1)

        ring = pygame.Rect(rect.x + 18, rect.y + 58, rect.width - 36, 232)
        pygame.draw.rect(screen, (43, 32, 25), ring, border_radius=12)
        pygame.draw.rect(screen, (99, 69, 43), ring, width=2, border_radius=12)
        pygame.draw.ellipse(screen, (64, 45, 31), ring.inflate(-28, -20))
        pygame.draw.ellipse(screen, (120, 83, 45), ring.inflate(-28, -20), width=2)
        pygame.draw.ellipse(screen, (39, 29, 24), ring.inflate(-56, -42), width=2)

        side_a = pygame.Rect(ring.x + 14, ring.y + 16, 142, 144)
        side_b = pygame.Rect(ring.right - 156, ring.y + 16, 142, 144)
        self.draw_team_side(screen, side_a, self.training_group_a, "TEAM A", TEAM_A)
        self.draw_team_side(screen, side_b, self.training_group_b, "TEAM B", TEAM_B)
        self.draw_medallion(screen, ring.center, "VS", (91, 61, 39), 25)

        skill_a = sum(getattr(dragon, "combat_skill", 0) for dragon in self.training_group_a)
        skill_b = sum(getattr(dragon, "combat_skill", 0) for dragon in self.training_group_b)
        skill_text = self.fantasy_small.render(f"COMBINED SKILL   {skill_a}  vs  {skill_b}", True, TEXT)
        screen.blit(skill_text, skill_text.get_rect(center=(ring.centerx, ring.bottom - 44)))
        self.draw_skill_balance(screen, pygame.Rect(ring.x + 42, ring.bottom - 23, ring.width - 84, 10), skill_a, skill_b)

        mode_label = self.fantasy_tiny.render("CHOOSE AN EXERCISE", True, GOLD)
        screen.blit(mode_label, (rect.x + 18, rect.y + 307))
        modes = [
            ("SPARRING", "sparring"),
            ("TEAM DRILLS", "team"),
            ("MENTORSHIP", "mentor"),
        ]
        button_x = rect.x + 18
        for label, mode in modes:
            button = TrainingButton(
                (button_x, rect.y + 328, 112, 39),
                label,
                lambda selected_mode=mode: self.set_training_mode(selected_mode),
                selected=self.training_mode == mode,
            )
            self.buttons.append(button)
            button.draw(screen, self.fantasy_tiny, mouse_pos)
            button_x += 121

        description_rect = pygame.Rect(rect.x + 18, rect.y + 382, rect.width - 36, 57)
        pygame.draw.rect(screen, (36, 30, 27), description_rect, border_radius=7)
        pygame.draw.rect(screen, (82, 61, 46), description_rect, width=1, border_radius=7)
        self.draw_wrapped_text(
            screen,
            self.get_mode_description(),
            description_rect.x + 12,
            description_rect.y + 10,
            description_rect.width - 24,
            self.fantasy_small,
            MUTED,
        )

        ready = self.training_is_ready()
        status_text = "THE RING IS READY" if ready else "ASSIGN DRAGONS TO BOTH SIDES"
        status_color = GREEN if ready else GOLD
        status = self.fantasy_tiny.render(status_text, True, status_color)
        screen.blit(status, status.get_rect(center=(rect.centerx, rect.y + 458)))

        start = TrainingButton(
            (rect.centerx - 112, rect.bottom - 58, 224, 42),
            "BEGIN TRAINING" if ready else "SELECT COMBATANTS",
            lambda: self.run_training(self.training_mode),
            enabled=ready,
            primary=True,
        )
        self.buttons.append(start)
        start.draw(screen, self.fantasy_body_bold, mouse_pos)

    def draw_training_log(self, screen, rect):
        self.draw_beveled_panel(screen, rect, fill=(27, 23, 21, 230), edge=(111, 76, 50), cut=12)
        events = self.get_training_events()
        screen.blit(self.fantasy_heading.render("TRAINING CHRONICLE", True, GOLD), (rect.x + 16, rect.y + 15))
        screen.blit(self.fantasy_small.render(f"{len(events)} recorded sessions", True, MUTED), (rect.x + 16, rect.y + 42))
        pygame.draw.line(screen, (112, 78, 51), (rect.x + 16, rect.y + 66), (rect.right - 16, rect.y + 66), 1)

        area = pygame.Rect(rect.x + 12, rect.y + 78, rect.width - 24, rect.height - 94)
        old_clip = screen.get_clip()
        screen.set_clip(area)
        if not events:
            heading = self.fantasy_body.render("No sessions recorded.", True, TEXT)
            note = self.fantasy_small.render("The ring awaits its first match.", True, MUTED)
            screen.blit(heading, (area.x + 10, area.y + 18))
            screen.blit(note, (area.x + 10, area.y + 44))
        else:
            y = area.y + self.log_scroll
            recent = list(reversed(events[-25:]))
            for index, event in enumerate(recent):
                card = pygame.Rect(area.x, y, area.width - 5, 91)
                pygame.draw.rect(screen, (37, 32, 29), card, border_radius=8)
                pygame.draw.rect(screen, (78, 60, 48), card, width=1, border_radius=8)
                marker = self.fantasy_tiny.render(f"SESSION {len(events) - index}", True, GOLD)
                screen.blit(marker, (card.x + 10, card.y + 8))
                text = str(event.get("text", "")).replace("\n", " ").strip()
                self.draw_wrapped_text(
                    screen,
                    text,
                    card.x + 10,
                    card.y + 27,
                    card.width - 20,
                    self.fantasy_tiny,
                    TEXT,
                )
                y += 101
        screen.set_clip(old_clip)
        content_height = len(events[-25:]) * 101
        self.draw_scroll_track(
            screen,
            pygame.Rect(rect.right - 10, area.y + 4, 2, area.height - 8),
            self.log_scroll,
            content_height,
            area.height,
        )

    def draw(self, screen):
        self.buttons.clear()
        mouse_pos = scale_mouse_pos(
            pygame.mouse.get_pos(),
            pygame.display.get_surface().get_size(),
        )

        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill((18, 14, 12))

        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((10, 7, 5, 76))
        screen.blit(veil, (0, 0))
        pygame.draw.rect(screen, (111, 75, 45), (18, 16, 964, 668), width=3, border_radius=18)
        pygame.draw.rect(screen, (38, 28, 25), (25, 23, 950, 654), width=2, border_radius=15)

        self.draw_beveled_panel(
            screen,
            (250, 18, 500, 76),
            fill=(30, 24, 20, 240),
            edge=(145, 95, 52),
            cut=15,
        )
        title = self.fantasy_title.render("TRAINING GROUNDS", True, CREAM)
        screen.blit(title, title.get_rect(center=(500, 45)))
        subtitle = self.fantasy_small.render(
            "Discipline, rivalry, and strength forged in the ring",
            True,
            MUTED,
        )
        screen.blit(subtitle, subtitle.get_rect(center=(500, 72)))

        return_button = TrainingButton(
            (823, 32, 130, 42),
            "RETURN",
            lambda: self.change_screen("locations"),
        )
        self.buttons.append(return_button)
        return_button.draw(screen, self.fantasy_body, mouse_pos)

        self.draw_roster(screen, pygame.Rect(35, 112, 260, 540), mouse_pos)
        self.draw_arena(screen, pygame.Rect(310, 112, 390, 540), mouse_pos)
        self.draw_training_log(screen, pygame.Rect(715, 112, 250, 540))

    def update(self, dt):
        pass

    def set_training_mode(self, mode):
        self.training_mode = mode

        # If switching out of team mode, reduce to 1v1.
        if mode != "team":
            self.training_group_a = self.training_group_a[:1]
            self.training_group_b = self.training_group_b[:1]

        self.selected_dragon = self.training_group_a[0] if self.training_group_a else None
        self.selected_partner = self.training_group_b[0] if self.training_group_b else None

    def select_dragon(self, dragon):

        if self.training_mode == "team":
            max_per_team = 3
        else:
            max_per_team = 1

        if dragon in self.training_group_a:
            self.training_group_a.remove(dragon)

            if len(self.training_group_b) < max_per_team:
                self.training_group_b.append(dragon)

        elif dragon in self.training_group_b:
            self.training_group_b.remove(dragon)

        else:
            if len(self.training_group_a) < max_per_team:
                self.training_group_a.append(dragon)
            elif len(self.training_group_b) < max_per_team:
                self.training_group_b.append(dragon)

        self.selected_dragon = self.training_group_a[0] if self.training_group_a else None
        self.selected_partner = self.training_group_b[0] if self.training_group_b else None

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            mouse_x, mouse_y = scale_mouse_pos(
                pygame.mouse.get_pos(),
                pygame.display.get_surface().get_size(),
            )

            roster_area = pygame.Rect(47, 190, 236, 444)
            log_area = pygame.Rect(727, 190, 226, 446)

            if roster_area.collidepoint(mouse_x, mouse_y):
                total_height = len(self.get_dragons()) * 64
                visible_height = roster_area.height
                max_scroll = max(0, total_height - visible_height)
                self.list_scroll += event.y * 30
                self.list_scroll = min(0, self.list_scroll)
                self.list_scroll = max(-max_scroll, self.list_scroll)
            elif log_area.collidepoint(mouse_x, mouse_y):
                total_height = len(self.get_training_events()[-25:]) * 101
                visible_height = log_area.height
                max_scroll = max(0, total_height - visible_height)
                self.log_scroll += event.y * 30
                self.log_scroll = min(0, self.log_scroll)
                self.log_scroll = max(-max_scroll, self.log_scroll)

        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            scaled_pos = scale_mouse_pos(
                event.pos,
                pygame.display.get_surface().get_size(),
            )
            scaled_event = pygame.event.Event(
                event.type,
                {"pos": scaled_pos, "button": event.button},
            )
            for button in list(self.buttons):
                button.handle_event(scaled_event)
        else:
            for button in list(self.buttons):
                button.handle_event(event)


def scale_mouse_pos(pos, window_size):
    mouse_x, mouse_y = pos
    window_width, window_height = window_size
    return int(mouse_x * WIDTH / window_width), int(mouse_y * HEIGHT / window_height)
