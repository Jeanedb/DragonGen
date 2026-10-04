import random
import pygame
from pathlib import Path

from ui_pygame.core.base_screen import BaseScreen
from ui_pygame.widgets.button import Button
from core.sim.behavior import get_behavior_score
from core.sim.memory import Memory, add_memory, current_moon
from core.sim.logging import log_event

WIDTH, HEIGHT = 1000, 700

TEXT = (236, 222, 196)
MUTED = (176, 158, 132)
GOLD = (227, 183, 84)
BRONZE = (133, 91, 53)
CREAM = (248, 230, 192)
RED = (205, 82, 66)
GREEN = (111, 178, 120)
INK = (24, 18, 14)
PANEL = (31, 25, 20)


def find_project_root():
    """Find the project folder even if this screen is moved later."""
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
    """Simple invisible target compatible with BaseScreen.buttons."""

    def __init__(self, rect, callback, enabled=True):
        self.rect = pygame.Rect(rect)
        self.callback = callback
        self.enabled = enabled

    def handle_event(self, event):
        if (
            self.enabled
            and event.type == pygame.MOUSEBUTTONUP
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        ):
            self.callback()


class HuntButton(ClickTarget):
    def __init__(
        self,
        rect,
        label,
        callback,
        enabled=True,
        primary=False,
        selected=False,
    ):
        super().__init__(rect, callback, enabled)
        self.label = label
        self.primary = primary
        self.selected = selected

    def draw(self, screen, font, mouse_pos):
        hovered = self.enabled and self.rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (7, 5, 4), self.rect.move(0, 4), border_radius=8)

        if not self.enabled:
            edge, fill, text_color = (76, 69, 61), (42, 39, 35), (118, 109, 97)
        elif self.selected:
            edge, fill, text_color = GOLD, (90, 57, 29), CREAM
        elif self.primary:
            edge = GOLD if hovered else (177, 121, 53)
            fill = (107, 63, 29) if hovered else (76, 48, 28)
            text_color = CREAM
        else:
            edge = GOLD if hovered else (111, 80, 55)
            fill = (65, 48, 36) if hovered else (43, 36, 32)
            text_color = TEXT

        pygame.draw.rect(screen, edge, self.rect, border_radius=8)
        inner = self.rect.inflate(-5, -5)
        pygame.draw.rect(screen, fill, inner, border_radius=6)
        pygame.draw.line(
            screen,
            (213, 167, 94) if self.enabled else (74, 68, 60),
            (inner.left + 8, inner.top + 3),
            (inner.right - 8, inner.top + 3),
            1,
        )
        image = font.render(self.label, True, text_color)
        screen.blit(image, image.get_rect(center=self.rect.center))


class HuntingGroundsScreen(BaseScreen):

    def __init__(self, world, change_screen):
        super().__init__()

        self.hunt_mode = "small"

        self.world = world
        self.change_screen = change_screen
        self.log_scroll = 0

        self.selected_dragon = None
        self.list_scroll = 0

        self.selected_party = []
        self.hunt_party_mode = "single"

        self.fantasy_title = pygame.font.SysFont("georgia", 30, bold=True)
        self.fantasy_heading = pygame.font.SysFont("georgia", 18, bold=True)
        self.fantasy_body = pygame.font.SysFont("georgia", 14)
        self.fantasy_body_bold = pygame.font.SysFont("georgia", 14, bold=True)
        self.fantasy_small = pygame.font.SysFont("georgia", 12)
        self.fantasy_tiny = pygame.font.SysFont("georgia", 11)
        self.medallion_font = pygame.font.SysFont("georgia", 15, bold=True)

        self._list_content_height = 0
        self._log_content_height = 0
        self._dragon_list_rect = pygame.Rect(49, 345, 222, 270)
        self._log_rect = pygame.Rect(705, 202, 244, 414)

        project_root = find_project_root()
        tribe_slug = (
            str(getattr(self.world, "tribe_name", ""))
            .lower()
            .replace(" tribe", "")
            .replace(" ", "")
        )
        background_candidates = [
            project_root / "assets" / tribe_slug / "hunting_bg.png",
            project_root / "assets" / tribe_slug / "location_map.png",
            project_root / "assets" / "menu" / "hunting_bg.png",
            project_root / "assets" / "menu" / "training_bg.png",
        ]
        bg_path = next(
            (path for path in background_candidates if path.exists()),
            background_candidates[-1],
        )

        try:
            self.bg_image = pygame.image.load(str(bg_path)).convert()
            self.bg_image = pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT))
        except Exception as error:
            print(f"Could not load hunting background: {error}")
            self.bg_image = None

        forest_path = project_root / "assets" / "hunting" / "forest.png"

        try:
            self.forest_image = pygame.image.load(str(forest_path)).convert()
        except Exception as error:
            print(f"Could not load hunting trail art: {error}")
            self.forest_image = None

    def get_selected_dragon(self):
        dragons = self.get_dragons()

        if self.selected_dragon in dragons:
            return self.selected_dragon

        if dragons:
            self.selected_dragon = dragons[0]
            return self.selected_dragon

        return None

    def get_dragons(self):
        return [
            d for d in getattr(self.world, "dragons", [])
            if getattr(d, "status", "") == "Alive"
            and getattr(d, "role", "") != "Dragonet"
        ]

    def get_hunts_remaining(self):
        maximum_hunts = 2
        current_moon = getattr(self.world, "moon", 0)

        if not hasattr(self.world, "world_flags") or self.world.world_flags is None:
            self.world.world_flags = {}

        hunt_moon = self.world.world_flags.get("hunt_action_moon")

        if hunt_moon != current_moon:
            self.world.world_flags["hunt_action_moon"] = current_moon
            self.world.world_flags["hunts_used"] = 0

        hunts_used = self.world.world_flags.get("hunts_used", 0)

        return max(0, maximum_hunts - hunts_used)

    def add_hunting_event(self, text, involved_ids=None, importance=2):
        log_event(
            self.world,
            text,
            involved_ids=involved_ids or [],
            event_type="hunt",
            importance=importance,
        )

    def get_food_requirement(self):
        """Food consumed at the next moon advance (one per living dragon)."""
        return sum(
            1
            for dragon in getattr(self.world, "dragons", [])
            if getattr(dragon, "status", "") == "Alive"
        )

    def get_food_supply_text(self):
        required = self.get_food_requirement()
        stores = max(0, int(getattr(self.world, "food_stores", 0)))
        if required <= 0:
            return "No current consumption"
        moons = stores // required
        if moons <= 0:
            return f"Need {required} next moon • SHORTFALL"
        return f"Need {required} next moon • {moons} moon{'s' if moons != 1 else ''}"

    def get_fatigue_map(self):
        if not hasattr(self.world, "world_flags") or self.world.world_flags is None:
            self.world.world_flags = {}
        fatigue = self.world.world_flags.setdefault("dragon_fatigue", {})
        if not isinstance(fatigue, dict):
            fatigue = {}
            self.world.world_flags["dragon_fatigue"] = fatigue
        return fatigue

    def get_dragon_fatigue(self, dragon):
        fatigue = self.get_fatigue_map()
        return max(0, int(fatigue.get(str(dragon.id), fatigue.get(dragon.id, 0))))

    def add_hunt_fatigue(self, party, hunt_type):
        fatigue_cost = {"small": 1, "large": 2, "dangerous": 3}.get(hunt_type, 1)
        fatigue = self.get_fatigue_map()
        for dragon in party:
            key = str(dragon.id)
            fatigue[key] = min(6, self.get_dragon_fatigue(dragon) + fatigue_cost)

    def get_party_profile(self, party, hunt_type):
        """Return success, yield bonus and injury protection for this party."""
        if not party:
            return {
                "success": 0.0,
                "yield_multiplier": 1.0,
                "injury_protection": 0.0,
            }

        roles = [str(getattr(dragon, "role", "")).lower() for dragon in party]
        hunters = roles.count("hunter")
        scouts = roles.count("scout")
        warriors = roles.count("warrior")
        healers = roles.count("healer")

        success = sum(self.get_hunting_score(dragon, hunt_type) / 2.0 for dragon in party) / len(party)

        if self.hunt_party_mode == "party" and len(party) > 1:
            average_cooperation = sum(
                get_behavior_score(dragon, "cooperation") for dragon in party
            ) / len(party)
            success += min(0.10, 0.035 * (len(party) - 1))
            success += min(0.12, scouts * 0.06)
            success += (average_cooperation - 0.5) * 0.20

        return {
            "success": max(0.05, min(0.95, success)),
            "yield_multiplier": min(1.45, 1.0 + hunters * 0.12 + scouts * 0.03),
            "injury_protection": min(0.55, warriors * 0.12 + healers * 0.18),
        }

    def get_party_bonus_text(self, party):
        roles = [str(getattr(dragon, "role", "")).lower() for dragon in party]
        bonuses = []
        if "hunter" in roles:
            bonuses.append("Yield")
        if "scout" in roles:
            bonuses.append("Track")
        if "warrior" in roles:
            bonuses.append("Guard")
        if "healer" in roles:
            bonuses.append("Aid")
        return "Bonuses: " + (" • ".join(bonuses) if bonuses else "none")

    def create_hunting_crisis(self, party, injured_dragon, hunt_type):
        if getattr(self.world, "pending_choice", None) is not None:
            return False

        self.world.pending_choice = {
            "type": "hunting_crisis",
            "location": "hunting",
            "hunt_type": hunt_type,
            "injured_id": injured_dragon.id,
            "party_ids": [dragon.id for dragon in party],
            "text": (
                f"{injured_dragon.name} was badly hurt during the expedition. "
                "The prey is still within reach, but the hunting party must decide what matters most."
            ),
            "options": [
                {"id": "retreat_together", "text": "Abandon the hunt and retreat together"},
                {"id": "stabilize_injured", "text": "Protect the injured dragon and send for help"},
                {"id": "press_the_hunt", "text": "Split the party and continue pursuing the prey"},
            ],
        }
        self.add_hunting_event(
            f"{injured_dragon.name} was badly hurt during a {hunt_type} hunt. The party awaits a decision.",
            involved_ids=[dragon.id for dragon in party],
            importance=5,
        )
        return True

    def run_hunt(self, hunt_type):  

        dragons = self.get_dragons()

        if self.get_hunts_remaining() <= 0:
            self.add_hunting_event(
                "No hunting expeditions remain this moon."
            )
            return

        if self.hunt_party_mode == "single":
            party = [self.get_selected_dragon()]
        else:
            party = [dragon for dragon in self.selected_party if dragon in dragons]

        party = [dragon for dragon in party if dragon is not None]
        if not party:
            return

        a = random.choice(party)

        if not a:
            return

        party_profile = self.get_party_profile(party, hunt_type)

        # In party mode, interactions should involve another hunter
        # who is actually participating in the hunt.
        if self.hunt_party_mode == "party" and len(party) > 1:
            others = [d for d in party if d != a]
        else:
            # Solo hunts can still create an interaction with another
            # tribe member when the hunter returns.
            others = [d for d in dragons if d != a]

        # A one-dragon tribe may still hunt; in that edge case the hunter is
        # also the only possible narrative subject.
        b = random.choice(others) if others else a

        if hunt_type == "small":

            outcomes = [
                (
                    "impress",
                    f"{a.name} returned with enough prey to feed several families.",
                    f"{a.name}'s reputation improved."
                ),

                (
                    "bond",
                    f"{a.name} and {b.name} worked together effectively on the hunt.",
                    f"{a.name} and {b.name} trust each other more."
                ),

                (
                    "impress",
                    f"{a.name} discovered fresh hunting grounds.",
                    f"The tribe views {a.name} more favorably."
                ),
            ]

        elif hunt_type == "large":

            outcomes = [
                (
                    "impress",
                    f"{a.name} helped bring down a massive prey beast.",
                    f"{a.name}'s reputation improved."
                ),

                (
                    "challenge",
                    f"{a.name} and {b.name} disagreed during the hunt.",
                    f"Tension between them increased."
                ),

                (
                    "bond",
                    f"{a.name} coordinated the hunting party successfully.",
                    f"The hunters trust {a.name} more."
                ),

                (
                    "strain",
                    f"The large hunt became difficult and exhausting.",
                    f"The tribe feels slightly more tense."
                ),
            ]

        elif hunt_type == "dangerous":

            outcomes = [
                (
                    "impress",
                    f"{a.name} returned from a dangerous hunt with an incredible trophy.",
                    f"{a.name}'s reputation improved greatly."
                ),

                (
                    "strain",
                    f"{a.name} narrowly escaped a deadly predator.",
                    f"The tribe is shaken by the close call."
                ),

                (
                    "embarrass",
                    f"{a.name} made a costly mistake during the hunt.",
                    f"Some dragons have lost confidence in {a.name}."
                ),

                (
                    "bond",
                    f"{a.name} and {b.name} survived a dangerous encounter together.",
                    f"Their trust increased significantly."
                ),
            ]

        else:
            return

        success_bias = party_profile["success"]

        if random.random() < success_bias:
            good_outcomes = [o for o in outcomes if o[0] in {"impress", "bond"}]
            chosen = random.choice(good_outcomes)
        else:
            bad_outcomes = [o for o in outcomes if o[0] in {"strain", "challenge", "embarrass"}]
            chosen = random.choice(bad_outcomes or outcomes)

        outcome_type = chosen[0]
        text = chosen[1]
        effect_text = chosen[2] if len(chosen) > 2 else self.get_hunting_effect_text(a, b, outcome_type)

        if b is a and outcome_type in {"bond", "challenge", "embarrass"}:
            outcome_type = "impress"
            text = f"{a.name} completed the expedition alone and returned safely."
            effect_text = f"{a.name}'s reputation improved."

        if outcome_type in {"impress", "bond"}:
            food_ranges = {
                "small": (8, 14),
                "large": (18, 30),
                "dangerous": (30, 50),
            }

            minimum_food, maximum_food = food_ranges[hunt_type]
            food_gained = round(
                random.randint(minimum_food, maximum_food)
                * party_profile["yield_multiplier"]
            )

            self.world.food_stores += food_gained
            effect_text += f"\n    The tribe gained {food_gained} food."

        self.apply_hunting_effect(a, b, outcome_type, hunt_type)
        if self.hunt_party_mode == "party":
            involved_ids = [dragon.id for dragon in party]
        else:
            involved_ids = [a.id]

        if outcome_type in {"bond", "challenge"}:
            involved_ids.append(b.id)

        importance = {
            "impress": 3,
            "bond": 3,
            "strain": 3,
            "challenge": 3,
            "embarrass": 4,
        }.get(outcome_type, 2)

        self.add_hunting_event(
            f"{text}\n    {effect_text}",
            involved_ids=list(dict.fromkeys(involved_ids)),
            importance=importance,
        )

        self.add_hunt_fatigue(party, hunt_type)

        # Serious expeditions can become a player-facing crisis. Warriors and
        # healers reduce this risk; failure and accumulated fatigue increase it.
        if hunt_type in {"large", "dangerous"}:
            base_injury_risk = 0.08 if hunt_type == "large" else 0.22
            if outcome_type not in {"impress", "bond"}:
                base_injury_risk += 0.08 if hunt_type == "large" else 0.12
            average_fatigue = sum(self.get_dragon_fatigue(d) for d in party) / len(party)
            base_injury_risk += max(0.0, average_fatigue - 2) * 0.025
            injury_risk = base_injury_risk * (1.0 - party_profile["injury_protection"])

            if random.random() < injury_risk:
                injured_dragon = random.choice(party)
                self.create_hunting_crisis(party, injured_dragon, hunt_type)

        self.world.world_flags["hunts_used"] = (
            self.world.world_flags.get("hunts_used", 0) + 1
        )

    def get_hunting_effect_text(self, a, b, outcome_type):
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

        return "The hunt left a mark."


    def apply_hunting_effect(self, a, b, outcome_type, hunt_type):

        if outcome_type == "bond":
            a.trust[b.id] = a.trust.get(b.id, 0) + 0.4
            b.trust[a.id] = b.trust.get(a.id, 0) + 0.4

            memory_a = Memory(
                type="hunted_with",
                moon=current_moon(self.world),
                other_id=b.id,
                importance=3,
                tags=["hunting", "bond", "shared_experience"]
            )

            memory_b = Memory(
                type="hunted_with",
                moon=current_moon(self.world),
                other_id=a.id,
                importance=3,
                tags=["hunting", "bond", "shared_experience"]
            )

            add_memory(a, memory_a)
            add_memory(b, memory_b)

            if hunt_type == "dangerous":
                survival_memory_a = Memory(
                    type="survived_dangerous_hunt_with",
                    moon=current_moon(self.world),
                    other_id=b.id,
                    importance=5,
                    reflection_weight=1.5,
                    tags=["hunting", "danger", "survival", "shared_hardship"]
                )

                survival_memory_b = Memory(
                    type="survived_dangerous_hunt_with",
                    moon=current_moon(self.world),
                    other_id=a.id,
                    importance=5,
                    reflection_weight=1.5,
                    tags=["hunting", "danger", "survival", "shared_hardship"]
                )

                add_memory(a, survival_memory_a)
                add_memory(b, survival_memory_b)

        elif outcome_type == "embarrass":
            b.resentment[a.id] = b.resentment.get(a.id, 0) + 0.5
            a.reputation["harsh"] = a.reputation.get("harsh", 0) + 0.2

            memory_a = Memory(
                type="failed_hunt_badly",
                moon=current_moon(self.world),
                importance=3,
                tags=["hunting", "failure", "embarrassment"]
            )

            memory_b = Memory(
                type="witnessed_hunting_failure",
                moon=current_moon(self.world),
                other_id=a.id,
                importance=2,
                tags=["hunting", "failure", "reputation"]
            )

            add_memory(a, memory_a)
            add_memory(b, memory_b)

        elif outcome_type == "strain":
            self.world.tension += 0.08
            a.reputation["harsh"] = a.reputation.get("harsh", 0) + 0.1

        elif outcome_type == "challenge":
            a.resentment[b.id] = a.resentment.get(b.id, 0) + 0.3
            b.resentment[a.id] = b.resentment.get(a.id, 0) + 0.3

        elif outcome_type == "impress":
            a.reputation["kind"] = a.reputation.get("kind", 0) + 0.2

        elif outcome_type == "mentor":
            a.reputation["kind"] = a.reputation.get("kind", 0) + 0.3

    def get_hunting_score(self, dragon, hunt_type):
        score = 1.0

        if dragon.role == "Hunter":
            score += 0.6
        elif dragon.role == "Scout":
            score += 0.25
        elif dragon.role == "Warrior":
            score += 0.15
        elif dragon.role == "Healer":
            score -= 0.1
        elif dragon.role == "Dragonet":
            score -= 0.8

        if dragon.health == "Injured":
            score -= 0.7

        score -= self.get_dragon_fatigue(dragon) * 0.12

        if hunt_type == "large":
            score -= 0.2
        elif hunt_type == "dangerous":
            score -= 0.5

        return max(0.1, score)

    def get_active_party(self):
        """Return the dragons that would actually leave on the next hunt."""
        if self.hunt_party_mode == "single":
            dragon = self.get_selected_dragon()
            return [dragon] if dragon is not None else []
        return [dragon for dragon in self.selected_party if dragon in self.get_dragons()]

    def get_party_strength_text(self):
        party = self.get_active_party()
        if not party:
            return "No Party Selected"

        scores = [
            self.get_hunting_score(d, "small")
            for d in party
        ]

        avg_score = sum(scores) / len(scores)

        if avg_score >= 1.5:
            rating = "Strong"
        elif avg_score >= 1.0:
            rating = "Capable"
        else:
            rating = "Weak"

        return f"Party Strength: {rating}"

    def get_dragon_readiness(self, dragon):
        fatigue = self.get_dragon_fatigue(dragon)
        if fatigue >= 5:
            return "Exhausted", RED
        if fatigue >= 3:
            return "Tired", (214, 135, 74)
        score = self.get_hunting_score(dragon, "small")
        if score >= 1.5:
            return "Strong", GREEN
        if score >= 1.0:
            return "Capable", GOLD
        return "At Risk", RED

    def set_party_mode(self, mode):
        self.hunt_party_mode = mode
        if mode == "single" and self.selected_dragon is None:
            self.get_selected_dragon()

    def wrap_lines(self, text, font, max_width):
        lines = []
        for paragraph in str(text).splitlines() or [""]:
            words = paragraph.split()
            if not words:
                lines.append("")
                continue
            line = words[0]
            for word in words[1:]:
                candidate = f"{line} {word}"
                if font.size(candidate)[0] <= max_width:
                    line = candidate
                else:
                    lines.append(line)
                    line = word
            lines.append(line)
        return lines

    def draw_text_line(self, screen, text, x, y, font, color):
        image = font.render(str(text), True, color)
        screen.blit(image, (x, y))
        return image

    def draw_beveled_panel(self, screen, rect, alpha=225, title=None):
        shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (5, 3, 2, 190), shadow.get_rect(), border_radius=12)
        screen.blit(shadow, (rect.x + 5, rect.y + 7))

        panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(panel, (*PANEL, alpha), panel.get_rect(), border_radius=12)
        pygame.draw.rect(panel, (*BRONZE, min(255, alpha + 20)), panel.get_rect(), 2, 12)
        pygame.draw.rect(panel, (72, 50, 34, alpha), panel.get_rect().inflate(-8, -8), 1, 9)
        screen.blit(panel, rect.topleft)

        if title:
            self.draw_text_line(
                screen,
                title.upper(),
                rect.x + 18,
                rect.y + 14,
                self.fantasy_heading,
                CREAM,
            )
            pygame.draw.line(
                screen,
                BRONZE,
                (rect.x + 18, rect.y + 43),
                (rect.right - 18, rect.y + 43),
                1,
            )

    def draw_medallion(self, screen, center, label, color, selected=False, radius=20):
        pygame.draw.circle(screen, (8, 5, 4), (center[0] + 2, center[1] + 3), radius + 3)
        pygame.draw.circle(screen, GOLD if selected else BRONZE, center, radius + 2)
        pygame.draw.circle(screen, (33, 25, 19), center, radius - 2)
        pygame.draw.circle(screen, color, center, radius - 6)
        image = self.medallion_font.render(label[:2].upper(), True, CREAM)
        screen.blit(image, image.get_rect(center=center))

    def get_initials(self, name):
        pieces = str(name).replace("-", " ").split()
        if len(pieces) >= 2:
            return pieces[0][0] + pieces[1][0]
        return str(name)[:2]

    def estimate_party_success(self, hunt_type):
        """Mirror run_hunt's probability closely enough for an honest preview."""
        party = self.get_active_party()
        return round(self.get_party_profile(party, hunt_type)["success"] * 100)

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

    def _legacy_draw(self, screen):

        self.buttons.clear()

        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill((18, 18, 18))

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 130))
        screen.blit(overlay, (0, 0))

        title = self.title_font.render("Hunting Grounds", True, TEXT)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 70)))



        subtitle = self.small.render(
            "Lead hunting parties and provide food for the tribe.",
            True,
            MUTED
        )
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 110)))

        food_text = self.section_font.render(
            f"Food Stores: {getattr(self.world, 'food_stores', 100)}  |  Hunts Remaining: {self.get_hunts_remaining()}/2",
            True,
            GOLD
        )

        screen.blit(
            food_text,
            food_text.get_rect(center=(WIDTH // 2, 132))
        )

        left = pygame.Rect(60, 150, 240, 455)
        center = pygame.Rect(330, 150, 300, 455)
        right = pygame.Rect(660, 150, 280, 455)
        

        self.draw_panel(screen, left)
        self.draw_panel(screen, center)
        self.draw_panel(screen, right)

        self.draw_text(
            screen,
            "Forest Trail",
            center.x + 18,
            center.y + 18,
            self.section_font,
            GOLD
        )

        self.draw_text(
            screen,
            "Hunting Party",
            left.x + 18,
            left.y + 18,
            self.section_font,
            GOLD
        )

        single_btn = Button(
            (center.x + 35, center.y + 65, 105, 32),
            "Single",
            lambda: setattr(self, "hunt_party_mode", "single")
        )

        party_btn = Button(
            (center.x + 160, center.y + 65, 105, 32),
            "Party",
            lambda: setattr(self, "hunt_party_mode", "party")
        )

        self.buttons.append(single_btn)
        self.buttons.append(party_btn)

        single_btn.draw(screen, self.small)
        party_btn.draw(screen, self.small)

        forest_rect = pygame.Rect(
            center.x + 30,
            center.y + 115,
            240,
            140
        )

        if self.forest_image:
            forest_img = pygame.transform.scale(
                self.forest_image,
                (forest_rect.width, forest_rect.height)
            )
            screen.blit(forest_img, forest_rect.topleft)

            pygame.draw.rect(
                screen,
                GOLD,
                forest_rect,
                width=1,
                border_radius=8
            )
        else:
            pygame.draw.rect(
                screen,
                (40, 70, 40),
                forest_rect,
                border_radius=10
            )

            self.draw_text(
                screen,
                "FOREST",
                center.x + 90,
                center.y + 165,
                self.section_font,
                GOLD
            )

        strength_text = self.get_party_strength_text()

        strength_color = MUTED

        if "Strong" in strength_text:
            strength_color = (111, 207, 151)
        elif "Capable" in strength_text:
            strength_color = GOLD
        elif "Weak" in strength_text:
            strength_color = RED

        text_surface = self.small.render(
            strength_text,
            True,
            strength_color
        )

        strength_bar = pygame.Rect(
            forest_rect.x,
            forest_rect.bottom - 28,
            forest_rect.width,
            28
        )

        overlay = pygame.Surface(
            (strength_bar.width, strength_bar.height),
            pygame.SRCALPHA
        )

        overlay.fill((0, 0, 0, 160))

        screen.blit(
            overlay,
            strength_bar.topleft
        )

        screen.blit(
            text_surface,
            (
                center.centerx - text_surface.get_width() // 2,
                strength_bar.y + 4
            )
        )

        self.draw_text(
            screen,
            "Hunting Log",
            right.x + 18,
            right.y + 18,
            self.section_font,
            GOLD
        )

        dragons = self.get_dragons()

        self.draw_text(
            screen,
            f"Mode: {self.hunt_party_mode.title()}",
            left.x + 22,
            left.y + 62,
            self.small,
            MUTED
        )

        self.draw_text(
            screen,
            f"Party Size: {len(self.selected_party)}",
            left.x + 22,
            left.y + 82,
            self.small,
            TEXT
        )

        self.draw_text(
            screen,
            "Party Members:",
            left.x + 22,
            left.y + 112,
            self.small,
            GOLD
        )

        py = left.y + 137

        if not self.selected_party:
            self.draw_text(screen, "None selected", left.x + 30, py, self.small, MUTED)
            py += 20
        else:
            for dragon in self.selected_party[:6]:
                self.draw_text(
                    screen,
                    f"• {dragon.name} ({dragon.role})",
                    left.x + 30,
                    py,
                    self.small,
                    TEXT
                )
                py += 20

        self.draw_text(
            screen,
            "Available Dragons:",
            left.x + 22,
            left.y + 255,
            self.small,
            GOLD
        )

        list_rect = pygame.Rect(left.x + 20, left.y + 280, left.width - 40, 140)

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

                if dragon in self.selected_party:
                    pygame.draw.rect(screen, GOLD, btn_rect, width=2, border_radius=6)
                elif dragon == self.selected_dragon:
                    pygame.draw.rect(screen, MUTED, btn_rect, width=1, border_radius=6)

            y += 34

        screen.set_clip(old_clip)

        buttons = [
            ("Small Hunt", "small", "Low", "Quick food gathering"),
            ("Large Hunt", "large", "Medium", "Requires coordination"),
            ("Dangerous Hunt", "dangerous", "High", "Rare prey and trophies"),
        ]

        card_y = center.y + 265

        for label, hunt_type, risk, desc in buttons:

            card_rect = pygame.Rect(
                center.x + 15,
                card_y,
                270,
                48
            )

            pygame.draw.rect(
                screen,
                (35, 35, 35),
                card_rect,
                border_radius=8
            )

            pygame.draw.rect(
                screen,
                (60, 60, 60),
                card_rect,
                width=1,
                border_radius=8
            )

            self.draw_text(
                screen,
                f"{risk} Risk • {desc}",
                card_rect.x + 12,
                card_rect.y + 16,
                self.small,
                MUTED
            )

            btn = Button(
                (
                    card_rect.right - 120,
                    card_rect.y + 8,
                    105,
                    30
                ),
                label,
                lambda t=hunt_type: self.run_hunt(t)
            )

            self.buttons.append(btn)
            btn.draw(screen, self.small)

            card_y += 58

        log_rect = pygame.Rect(
            right.x + 18,
            right.y + 60,
            right.width - 36,
            right.height - 78
        )

        self.draw_panel(screen, log_rect, alpha=150)

        events = getattr(self.world, "event_log", [])

        hunt_events = [
            e for e in events
            if isinstance(e, dict)
            and e.get("type") == "hunt"
        ]

        old_clip = screen.get_clip()
        screen.set_clip(log_rect)

        y = log_rect.y + 12 + self.log_scroll

        for event in reversed(hunt_events[-25:]):

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

            y += 120
        

        screen.set_clip(old_clip)

        return_btn = Button(
            (430, 655, 140, 34),
            "Return",
            lambda: self.change_screen("locations")
        )

        self.buttons.append(return_btn)
        return_btn.draw(screen, self.font)

    def draw_roster(self, screen, rect, mouse_pos):
        self.draw_beveled_panel(screen, rect, title="Hunting Party")

        mode_y = rect.y + 56
        single_button = HuntButton(
            (rect.x + 16, mode_y, 101, 34),
            "SOLO",
            lambda: self.set_party_mode("single"),
            selected=self.hunt_party_mode == "single",
        )
        party_button = HuntButton(
            (rect.x + 132, mode_y, 101, 34),
            "PARTY",
            lambda: self.set_party_mode("party"),
            selected=self.hunt_party_mode == "party",
        )
        for button in (single_button, party_button):
            self.buttons.append(button)
            button.draw(screen, self.fantasy_small, mouse_pos)

        active_party = self.get_active_party()
        self.draw_text_line(
            screen,
            f"ACTIVE {self.hunt_party_mode.upper()}  •  {len(active_party)} DRAGON"
            f"{'S' if len(active_party) != 1 else ''}",
            rect.x + 18,
            rect.y + 104,
            self.fantasy_tiny,
            GOLD,
        )

        if active_party:
            names = ", ".join(dragon.name for dragon in active_party[:3])
            if len(active_party) > 3:
                names += f"  +{len(active_party) - 3} more"
            name_lines = self.wrap_lines(names, self.fantasy_body, rect.width - 36)[:2]
            for line_index, line in enumerate(name_lines):
                self.draw_text_line(
                    screen,
                    line,
                    rect.x + 18,
                    rect.y + 124 + line_index * 18,
                    self.fantasy_body,
                    TEXT,
                )
            self.draw_text_line(
                screen,
                self.get_party_bonus_text(active_party),
                rect.x + 18,
                rect.y + 148,
                self.fantasy_tiny,
                MUTED,
            )
        else:
            self.draw_text_line(
                screen,
                "Choose dragons from the roster below.",
                rect.x + 18,
                rect.y + 126,
                self.fantasy_small,
                MUTED,
            )

        pygame.draw.line(
            screen,
            BRONZE,
            (rect.x + 18, rect.y + 165),
            (rect.right - 18, rect.y + 165),
            1,
        )
        self.draw_text_line(
            screen,
            "AVAILABLE HUNTERS",
            rect.x + 18,
            rect.y + 177,
            self.fantasy_tiny,
            MUTED,
        )

        list_rect = pygame.Rect(rect.x + 10, rect.y + 201, rect.width - 20, rect.height - 213)
        self._dragon_list_rect = list_rect
        old_clip = screen.get_clip()
        screen.set_clip(list_rect)

        row_h = 50
        dragons = self.get_dragons()
        self._list_content_height = len(dragons) * row_h
        y = list_rect.y + self.list_scroll

        for dragon in dragons:
            row = pygame.Rect(list_rect.x + 4, y + 3, list_rect.width - 8, 43)
            selected = (
                dragon == self.selected_dragon
                if self.hunt_party_mode == "single"
                else dragon in self.selected_party
            )
            hovered = row.collidepoint(mouse_pos)

            if row.bottom >= list_rect.top and row.top <= list_rect.bottom:
                fill = (71, 49, 31) if hovered else (39, 31, 26)
                edge = GOLD if selected else ((151, 105, 57) if hovered else (73, 54, 40))
                pygame.draw.rect(screen, fill, row, border_radius=8)
                pygame.draw.rect(screen, edge, row, 2 if selected else 1, 8)

                readiness, readiness_color = self.get_dragon_readiness(dragon)
                self.draw_medallion(
                    screen,
                    (row.x + 24, row.centery),
                    self.get_initials(dragon.name),
                    (92, 61, 38),
                    selected=selected,
                    radius=16,
                )
                self.draw_text_line(
                    screen,
                    dragon.name,
                    row.x + 47,
                    row.y + 6,
                    self.fantasy_body_bold,
                    CREAM if selected else TEXT,
                )
                self.draw_text_line(
                    screen,
                    f"{dragon.role}  •  {readiness}  •  Fatigue {self.get_dragon_fatigue(dragon)}",
                    row.x + 47,
                    row.y + 24,
                    self.fantasy_tiny,
                    readiness_color,
                )
                self.buttons.append(ClickTarget(row, lambda d=dragon: self.select_dragon(d)))
            y += row_h

        screen.set_clip(old_clip)

    def draw_expedition(self, screen, rect, mouse_pos):
        self.draw_beveled_panel(screen, rect, title="Choose an Expedition")

        art_rect = pygame.Rect(rect.x + 18, rect.y + 55, rect.width - 36, 145)
        if self.forest_image:
            forest = pygame.transform.smoothscale(self.forest_image, art_rect.size)
            screen.blit(forest, art_rect)
        else:
            pygame.draw.rect(screen, (37, 62, 39), art_rect, border_radius=9)
        pygame.draw.rect(screen, BRONZE, art_rect, 2, 9)

        strength_text = self.get_party_strength_text()
        strength_color = MUTED
        if "Strong" in strength_text:
            strength_color = GREEN
        elif "Capable" in strength_text:
            strength_color = GOLD
        elif "Weak" in strength_text:
            strength_color = RED

        strength_bar = pygame.Surface((art_rect.width, 31), pygame.SRCALPHA)
        strength_bar.fill((12, 8, 6, 205))
        screen.blit(strength_bar, (art_rect.x, art_rect.bottom - 31))
        strength_image = self.fantasy_body_bold.render(strength_text, True, strength_color)
        screen.blit(
            strength_image,
            strength_image.get_rect(center=(art_rect.centerx, art_rect.bottom - 16)),
        )

        hunt_definitions = [
            ("SMALL HUNT", "small", "LOW RISK", 8, 14, GREEN),
            ("LARGE HUNT", "large", "MEDIUM RISK", 18, 30, GOLD),
            ("DANGEROUS HUNT", "dangerous", "HIGH RISK", 30, 50, RED),
        ]
        active_party = self.get_active_party()
        enabled = bool(active_party) and self.get_hunts_remaining() > 0
        card_y = art_rect.bottom + 14

        for title, hunt_type, risk, minimum_food, maximum_food, risk_color in hunt_definitions:
            card = pygame.Rect(rect.x + 14, card_y, rect.width - 28, 70)
            pygame.draw.rect(screen, (38, 30, 25), card, border_radius=9)
            pygame.draw.rect(screen, (82, 59, 41), card, 1, 9)
            pygame.draw.rect(screen, risk_color, (card.x, card.y, 5, card.height), border_radius=3)

            yield_multiplier = self.get_party_profile(active_party, hunt_type)["yield_multiplier"]
            reward = (
                f"{round(minimum_food * yield_multiplier)}–"
                f"{round(maximum_food * yield_multiplier)} food"
            )
            self.draw_text_line(screen, title, card.x + 16, card.y + 10, self.fantasy_body_bold, CREAM)
            self.draw_text_line(
                screen,
                f"{risk}  •  {reward}  •  {self.estimate_party_success(hunt_type)}% success",
                card.x + 16,
                card.y + 36,
                self.fantasy_tiny,
                MUTED if enabled else (106, 98, 89),
            )

            button = HuntButton(
                (card.right - 88, card.y + 15, 74, 39),
                "BEGIN",
                lambda t=hunt_type: self.run_hunt(t),
                enabled=enabled,
                primary=hunt_type == "large",
            )
            self.buttons.append(button)
            button.draw(screen, self.fantasy_tiny, mouse_pos)
            card_y += 78

    def draw_hunting_log(self, screen, rect):
        self.draw_beveled_panel(screen, rect, title="Hunting Journal")
        log_rect = pygame.Rect(rect.x + 10, rect.y + 55, rect.width - 20, rect.height - 85)
        self._log_rect = log_rect

        events = [
            event
            for event in getattr(self.world, "event_log", [])
            if isinstance(event, dict) and event.get("type") == "hunt"
        ]

        old_clip = screen.get_clip()
        screen.set_clip(log_rect)
        y = log_rect.y + 3 + self.log_scroll
        content_height = 0

        if not events:
            self.draw_text_line(
                screen,
                "No expeditions recorded this moon.",
                log_rect.x + 12,
                log_rect.y + 16,
                self.fantasy_small,
                MUTED,
            )

        for event in reversed(events[-30:]):
            event_text = str(event.get("text", "")).replace("    ", " ").strip()
            lines = self.wrap_lines(event_text, self.fantasy_small, log_rect.width - 30)
            card_h = 36 + len(lines) * 17
            card = pygame.Rect(log_rect.x + 3, y, log_rect.width - 6, card_h)

            if card.bottom >= log_rect.top and card.top <= log_rect.bottom:
                card_surface = pygame.Surface(card.size, pygame.SRCALPHA)
                pygame.draw.rect(card_surface, (44, 34, 27, 220), card_surface.get_rect(), border_radius=8)
                pygame.draw.rect(card_surface, (91, 65, 43, 235), card_surface.get_rect(), 1, 8)
                screen.blit(card_surface, card.topleft)
                pygame.draw.circle(screen, GOLD, (card.x + 12, card.y + 14), 3)

                moon = event.get("moon")
                heading = f"MOON {moon}" if moon is not None else "HUNT REPORT"
                self.draw_text_line(
                    screen,
                    heading,
                    card.x + 22,
                    card.y + 7,
                    self.fantasy_tiny,
                    GOLD,
                )
                for line_index, line in enumerate(lines):
                    self.draw_text_line(
                        screen,
                        line,
                        card.x + 12,
                        card.y + 27 + line_index * 17,
                        self.fantasy_small,
                        TEXT,
                    )

            y += card_h + 9
            content_height += card_h + 9

        self._log_content_height = content_height
        screen.set_clip(old_clip)
        self.draw_text_line(
            screen,
            "Scroll to review earlier expeditions",
            rect.x + 20,
            rect.bottom - 23,
            self.fantasy_tiny,
            MUTED,
        )

    def draw(self, screen):
        self.buttons.clear()
        mouse_pos = pygame.mouse.get_pos()

        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill((26, 20, 15))

        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((13, 8, 5, 142))
        screen.blit(veil, (0, 0))

        pygame.draw.rect(screen, (26, 18, 13), (23, 23, 954, 653), border_radius=18)
        pygame.draw.rect(screen, BRONZE, (27, 27, 946, 645), 3, 16)
        pygame.draw.rect(screen, (75, 50, 31), (34, 34, 932, 631), 1, 13)

        title_panel = pygame.Rect(306, 34, 388, 94)
        self.draw_beveled_panel(screen, title_panel, alpha=242)
        title = self.fantasy_title.render("THE HUNTING GROUNDS", True, CREAM)
        screen.blit(title, title.get_rect(center=(title_panel.centerx, title_panel.y + 35)))
        subtitle = self.fantasy_small.render(
            "Gather the tribe's hunters. Choose the risk. Bring home prey.",
            True,
            MUTED,
        )
        screen.blit(subtitle, subtitle.get_rect(center=(title_panel.centerx, title_panel.y + 66)))

        for badge, heading, value in (
            (pygame.Rect(48, 51, 225, 58), "FOOD STORES", str(getattr(self.world, "food_stores", 100))),
            (pygame.Rect(727, 51, 225, 58), "HUNTS REMAINING", f"{self.get_hunts_remaining()} / 2"),
        ):
            self.draw_beveled_panel(screen, badge, alpha=235)
            self.draw_text_line(screen, heading, badge.x + 15, badge.y + 10, self.fantasy_tiny, MUTED)
            value_image = self.fantasy_heading.render(value, True, GOLD)
            screen.blit(value_image, (badge.x + 15, badge.y + 27))
            if heading == "FOOD STORES":
                supply = self.fantasy_tiny.render(self.get_food_supply_text(), True, MUTED)
                screen.blit(supply, (badge.x + 54, badge.y + 32))

        left = pygame.Rect(40, 145, 250, 475)
        center = pygame.Rect(305, 145, 380, 475)
        right = pygame.Rect(700, 145, 260, 475)
        self.draw_roster(screen, left, mouse_pos)
        self.draw_expedition(screen, center, mouse_pos)
        self.draw_hunting_log(screen, right)

        return_button = HuntButton(
            (430, 635, 140, 34),
            "RETURN TO MAP",
            lambda: self.change_screen("locations"),
        )
        self.buttons.append(return_button)
        return_button.draw(screen, self.fantasy_tiny, mouse_pos)

    def update(self, dt):
        pass

    def select_dragon(self, dragon):

        if self.hunt_party_mode == "single":
            self.selected_dragon = dragon
            self.selected_party = [dragon]

        else:
            self.selected_dragon = dragon


            if dragon in self.selected_party:
                self.selected_party.remove(dragon)
            else:
                self.selected_party.append(dragon)

            if not self.selected_party:
                self.selected_dragon = None

    def handle_event(self, event):

        if event.type == pygame.MOUSEWHEEL:
            mouse_x, mouse_y = pygame.mouse.get_pos()

            if self._dragon_list_rect.collidepoint(mouse_x, mouse_y):
                visible_height = self._dragon_list_rect.height
                max_scroll = max(0, self._list_content_height - visible_height)

                self.list_scroll += event.y * 25
                self.list_scroll = min(0, self.list_scroll)
                self.list_scroll = max(-max_scroll, self.list_scroll)

            elif self._log_rect.collidepoint(mouse_x, mouse_y):
                max_scroll = max(0, self._log_content_height - self._log_rect.height)
                self.log_scroll += event.y * 25
                self.log_scroll = min(0, self.log_scroll)
                self.log_scroll = max(-max_scroll, self.log_scroll)

        for button in self.buttons:
            button.handle_event(event)
