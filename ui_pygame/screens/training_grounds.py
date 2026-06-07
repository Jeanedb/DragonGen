import random
import pygame
from pathlib import Path

from ui_pygame.core.base_screen import BaseScreen
from ui_pygame.widgets.button import Button

WIDTH, HEIGHT = 1000, 700

TEXT = (230, 230, 230)
MUTED = (180, 180, 180)
GOLD = (242, 201, 76)
RED = (235, 87, 87)


class TrainingGroundsScreen(BaseScreen):

    def __init__(self, world, change_screen):
        super().__init__()

        self.training_mode = "sparring"

        self.training_group_a = []
        self.training_group_b = []
        self.training_mode = "sparring"

        self.world = world
        self.change_screen = change_screen
        self.log_scroll = 0

        self.selected_dragon = None
        self.list_scroll = 0

        self.selected_partner = None

        project_root = Path(__file__).resolve().parents[2]
        bg_path = project_root / "assets" / "menu" / "training_bg.png"

        try:
            self.bg_image = pygame.image.load(str(bg_path)).convert()
            self.bg_image = pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT))
        except Exception:
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

    def add_training_event(self, text):
        if not hasattr(self.world, "event_log"):
            self.world.event_log = []

        self.world.event_log.append({
            "text": text,
            "type": "training",
        })

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

        if random.random() < success_bias:
            good_outcomes = [o for o in outcomes if o[0] in {"impress", "bond", "mentor"}]
            chosen = random.choice(good_outcomes)
        else:
            bad_outcomes = [o for o in outcomes if o[0] in {"strain", "challenge", "embarrass"}]
            chosen = random.choice(bad_outcomes or outcomes)

        outcome_type = chosen[0]
        text = chosen[1]
        effect_text = chosen[2] if len(chosen) > 2 else self.get_training_effect_text(a, b, outcome_type)

        self.apply_training_effect(a, b, outcome_type)
        self.add_training_event(
            f"{text}\n    {effect_text}"
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


    def apply_training_effect(self, a, b, outcome_type):

        if outcome_type == "bond":
            a.trust[b.id] = a.trust.get(b.id, 0) + 0.4
            b.trust[a.id] = b.trust.get(a.id, 0) + 0.4

        elif outcome_type == "embarrass":
            b.resentment[a.id] = b.resentment.get(a.id, 0) + 0.5
            a.reputation["harsh"] = a.reputation.get("harsh", 0) + 0.2

        elif outcome_type == "strain":
            self.world.tension += 0.08
            a.reputation["harsh"] = a.reputation.get("harsh", 0) + 0.1

        elif outcome_type == "challenge":
            a.resentment[b.id] = a.resentment.get(b.id, 0) + 0.3
            b.resentment[a.id] = b.resentment.get(a.id, 0) + 0.3

        elif outcome_type == "impress":
            a.reputation["kind"] = a.reputation.get("kind", 0) + 0.2
            
            if a.combat_skill < 20:
                a.combat_skill += 1

        elif outcome_type == "mentor":
            a.reputation["kind"] = a.reputation.get("kind", 0) + 0.3

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

    def draw_panel(self, screen, rect, alpha=185):
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

    def draw(self, screen):

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
            MUTED
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
                    (center.x + 55, start_y),
                    (center.x + 155, start_y),
                    (center.x + 55, start_y + 24),
                    (center.x + 155, start_y + 24),
                ]

                for i, dragon in enumerate(team[:4]):
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
                center.centerx - 15,
                center.y + 135,
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

        start_btn = Button(
            (center.x + 55, center.y + 425, 190, 42),
            "Begin Training",
            lambda: self.run_training(self.training_mode)
        )

        self.buttons.append(start_btn)
        start_btn.draw(screen, self.font)

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
            mouse_x, mouse_y = pygame.mouse.get_pos()

            dragon_list_rect = pygame.Rect(
                80,
                240,
                200,
                305
            )

            if dragon_list_rect.collidepoint(mouse_x, mouse_y):
                total_height = len(self.get_dragons()) * 34
                visible_height = dragon_list_rect.height
                max_scroll = max(0, total_height - visible_height)

                self.list_scroll += event.y * 25
                self.list_scroll = min(0, self.list_scroll)
                self.list_scroll = max(-max_scroll, self.list_scroll)

            else:
                self.log_scroll += event.y * 25
                self.log_scroll = min(0, self.log_scroll)
                self.log_scroll = max(-800, self.log_scroll)

        for button in self.buttons:
            button.handle_event(event)