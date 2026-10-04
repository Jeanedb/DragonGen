import random
from pathlib import Path

import pygame

from core.sim.behavior import get_behavior_score
from core.sim.injury import add_injury
from core.sim.logging import log_event
from core.sim.memory import Memory, add_memory, current_moon
from ui_pygame.core.base_screen import BaseScreen


WIDTH, HEIGHT = 1000, 700

TEXT = (236, 222, 196)
MUTED = (176, 158, 132)
GOLD = (227, 183, 84)
BRONZE = (133, 91, 53)
CREAM = (248, 230, 192)
RED = (205, 82, 66)
GREEN = (111, 178, 120)
BLUE = (104, 157, 184)
PANEL = (31, 25, 20)


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def find_project_root():
    """Find the project root even when this screen is moved or renamed."""
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
    """Simple invisible click target compatible with BaseScreen.buttons."""

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


class BorderButton(ClickTarget):
    def __init__(self, rect, label, callback, enabled=True, primary=False):
        super().__init__(rect, callback, enabled)
        self.label = label
        self.primary = primary

    def draw(self, screen, font, mouse_pos):
        hovered = self.enabled and self.rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (7, 5, 4), self.rect.move(0, 4), border_radius=8)

        if not self.enabled:
            edge, fill, color = (76, 69, 61), (42, 39, 35), (118, 109, 97)
        elif self.primary:
            edge = GOLD if hovered else (177, 121, 53)
            fill = (107, 63, 29) if hovered else (76, 48, 28)
            color = CREAM
        else:
            edge = GOLD if hovered else (111, 80, 55)
            fill = (65, 48, 36) if hovered else (43, 36, 32)
            color = TEXT

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
        image = font.render(self.label, True, color)
        screen.blit(image, image.get_rect(center=self.rect.center))


class BorderRoutesScreen(BaseScreen):

    MISSION_DATA = {
        "scout": {
            "title": "SCOUT ROUTE",
            "risk": "LOW RISK",
            "description": "Reveal movement, tracks, and hidden approaches.",
            "reward": "Primary effect: Intel",
            "difficulty": 12,
            "fatigue": 1,
        },
        "patrol": {
            "title": "SECURE BORDER",
            "risk": "MODERATE RISK",
            "description": "Challenge intruders and reinforce vulnerable routes.",
            "reward": "Primary effect: Security",
            "difficulty": 0,
            "fatigue": 1,
        },
        "expedition": {
            "title": "DISTANT EXPEDITION",
            "risk": "HIGH RISK",
            "description": "Travel beyond the border in search of answers.",
            "reward": "Intel, resources, and rare encounters",
            "difficulty": -18,
            "fatigue": 2,
        },
    }

    def __init__(self, world, change_screen):
        super().__init__()
        self.world = world
        self.change_screen = change_screen
        self.selected_party = []
        self.list_scroll = 0
        self.log_scroll = 0
        self._list_content_height = 0
        self._log_content_height = 0
        self._dragon_list_rect = pygame.Rect(42, 315, 238, 280)
        self._log_rect = pygame.Rect(715, 355, 238, 239)

        self.title_font_fantasy = pygame.font.SysFont("georgia", 29, bold=True)
        self.heading_font = pygame.font.SysFont("georgia", 17, bold=True)
        self.body_font = pygame.font.SysFont("georgia", 13)
        self.body_bold = pygame.font.SysFont("georgia", 13, bold=True)
        self.small_font = pygame.font.SysFont("georgia", 11)
        self.tiny_font = pygame.font.SysFont("georgia", 10)
        self.medallion_font = pygame.font.SysFont("georgia", 13, bold=True)

        self.ensure_border_state()

        project_root = find_project_root()
        tribe_slug = (
            str(getattr(self.world, "tribe_name", ""))
            .lower()
            .replace(" tribe", "")
            .replace(" ", "")
        )
        background_candidates = [
            project_root / "assets" / tribe_slug / "border_bg.png",
            project_root / "assets" / tribe_slug / "location_map.png",
            project_root / "assets" / "menu" / "border_bg.png",
            project_root / "assets" / "menu" / "training_bg.png",
        ]
        background_path = next(
            (path for path in background_candidates if path.exists()),
            background_candidates[-1],
        )
        try:
            self.bg_image = pygame.image.load(str(background_path)).convert()
            self.bg_image = pygame.transform.scale(self.bg_image, (WIDTH, HEIGHT))
        except Exception as error:
            print(f"Could not load border background: {error}")
            self.bg_image = None

    # Persistent state -------------------------------------------------

    def get_flags(self):
        if not hasattr(self.world, "world_flags") or self.world.world_flags is None:
            self.world.world_flags = {}
        return self.world.world_flags

    def ensure_border_state(self):
        flags = self.get_flags()
        flags.setdefault("border_security", 55)
        flags.setdefault("border_intel", 25)
        flags.setdefault("border_threat", 20)
        flags.setdefault("border_actions_used", 0)
        flags.setdefault("border_action_moon", getattr(self.world, "moon", 0))
        for key in ("border_security", "border_intel", "border_threat"):
            flags[key] = int(clamp(int(flags.get(key, 0)), 0, 100))
        return flags

    def get_border_value(self, key):
        return int(self.ensure_border_state().get(f"border_{key}", 0))

    def change_border_value(self, key, amount):
        flags = self.ensure_border_state()
        flag_key = f"border_{key}"
        flags[flag_key] = int(clamp(int(flags.get(flag_key, 0)) + amount, 0, 100))

    def get_actions_remaining(self):
        flags = self.ensure_border_state()
        moon = getattr(self.world, "moon", 0)
        if flags.get("border_action_moon") != moon:
            flags["border_action_moon"] = moon
            flags["border_actions_used"] = 0
        return max(0, 2 - int(flags.get("border_actions_used", 0)))

    def use_action(self):
        flags = self.ensure_border_state()
        flags["border_actions_used"] = int(flags.get("border_actions_used", 0)) + 1

    def get_fatigue_map(self):
        flags = self.get_flags()
        fatigue = flags.setdefault("dragon_fatigue", {})
        if not isinstance(fatigue, dict):
            fatigue = {}
            flags["dragon_fatigue"] = fatigue
        return fatigue

    def get_dragon_fatigue(self, dragon):
        fatigue = self.get_fatigue_map()
        return max(0, int(fatigue.get(str(dragon.id), fatigue.get(dragon.id, 0))))

    def add_patrol_fatigue(self, party, mission_type):
        cost = self.MISSION_DATA[mission_type]["fatigue"]
        fatigue = self.get_fatigue_map()
        for dragon in party:
            key = str(dragon.id)
            fatigue[key] = min(6, self.get_dragon_fatigue(dragon) + cost)

    # Party and mission rules -----------------------------------------

    def get_dragons(self):
        return [
            dragon
            for dragon in getattr(self.world, "dragons", [])
            if getattr(dragon, "status", "") == "Alive"
            and str(getattr(dragon, "health", "Healthy")).lower() != "injured"
            and getattr(dragon, "role", "") != "Dragonet"
        ]

    def get_party(self):
        available = self.get_dragons()
        self.selected_party = [dragon for dragon in self.selected_party if dragon in available]
        return self.selected_party

    def toggle_party_member(self, dragon):
        if dragon in self.selected_party:
            self.selected_party.remove(dragon)
        elif len(self.selected_party) < 3:
            self.selected_party.append(dragon)

    def get_dragon_readiness(self, dragon):
        role = str(getattr(dragon, "role", "")).lower()
        skill = max(0, min(20, int(getattr(dragon, "combat_skill", 0))))
        score = 34 + skill * 2
        score += {
            "scout": 17,
            "warrior": 15,
            "hunter": 9,
            "healer": 3,
            "leader": 5,
            "deputy": 6,
        }.get(role, 0)
        score -= self.get_dragon_fatigue(dragon) * 7
        score = int(clamp(score, 10, 95))
        if score >= 75:
            label, color = "Strong", GREEN
        elif score >= 55:
            label, color = "Capable", GOLD
        elif score >= 38:
            label, color = "Unsteady", MUTED
        else:
            label, color = "Exhausted", RED
        return score, label, color

    def get_party_profile(self, mission_type):
        party = self.get_party()
        if not party:
            return {"success": 0, "injury_protection": 0.0, "roles": []}

        roles = [str(getattr(dragon, "role", "")).lower() for dragon in party]
        average = sum(self.get_dragon_readiness(dragon)[0] for dragon in party) / len(party)
        average += (len(party) - 1) * 5

        if len(party) > 1:
            cooperation = sum(get_behavior_score(dragon, "cooperation") for dragon in party) / len(party)
            average += (cooperation - 0.5) * 16

        if mission_type == "scout":
            average += roles.count("scout") * 12 + roles.count("hunter") * 5
        elif mission_type == "patrol":
            average += roles.count("warrior") * 10 + roles.count("scout") * 4
        else:
            average += (
                roles.count("scout") * 7
                + roles.count("warrior") * 6
                + roles.count("hunter") * 5
                + roles.count("healer") * 3
            )

        average += self.MISSION_DATA[mission_type]["difficulty"]
        protection = min(
            0.55,
            roles.count("warrior") * 0.12 + roles.count("healer") * 0.18,
        )
        return {
            "success": int(clamp(round(average), 8, 95)),
            "injury_protection": protection,
            "roles": roles,
        }

    def get_role_bonus_text(self):
        roles = [str(getattr(dragon, "role", "")).lower() for dragon in self.get_party()]
        labels = []
        if "scout" in roles:
            labels.append("Detection")
        if "warrior" in roles:
            labels.append("Protection")
        if "hunter" in roles:
            labels.append("Tracking")
        if "healer" in roles:
            labels.append("Field aid")
        return " • ".join(labels) if labels else "No role bonuses"

    def get_party_readiness_text(self):
        """Return a quick, readable warning or endorsement for the selected patrol."""
        party = self.get_party()
        if not party:
            return "NO PARTY SELECTED", MUTED

        average = sum(self.get_dragon_readiness(dragon)[0] for dragon in party) / len(party)
        fatigued = sum(self.get_dragon_fatigue(dragon) >= 2 for dragon in party)
        if average >= 72 and not fatigued:
            return "PATROL READY", GREEN
        if average >= 52 and fatigued <= 1:
            return "PATROL CAPABLE", GOLD
        if fatigued:
            return "CAUTION: FATIGUED PARTY", RED
        return "CAUTION: WEAK PARTY", RED

    def get_chance_note(self, mission_type):
        """Explain the largest visible influences on a mission's success chance."""
        party = self.get_party()
        if not party:
            return "Odds update with party", MUTED

        roles = [str(getattr(dragon, "role", "")).lower() for dragon in party]
        preferred_roles = {
            "scout": {"scout", "hunter"},
            "patrol": {"warrior", "scout"},
            "expedition": {"scout", "warrior", "hunter", "healer"},
        }[mission_type]
        role_matches = sum(role in preferred_roles for role in roles)
        total_fatigue = sum(self.get_dragon_fatigue(dragon) for dragon in party)

        parts = []
        if role_matches:
            parts.append(f"Role fit +{role_matches}")
        else:
            parts.append("No role fit")
        if len(party) > 1:
            parts.append(f"Size +{len(party) - 1}")
        if total_fatigue:
            parts.append(f"Fatigue -{total_fatigue}")

        color = RED if role_matches == 0 or total_fatigue >= 5 else MUTED
        return " • ".join(parts), color

    def get_border_condition(self):
        threat = self.get_border_value("threat")
        if threat >= 70:
            return "Critical activity", RED
        if threat >= 45:
            return "Border unsettled", GOLD
        return "Routes quiet", GREEN

    def apply_relationship_result(self, party, success):
        if len(party) < 2:
            return
        first, second = random.sample(party, 2)
        if success:
            first.trust[second.id] = first.trust.get(second.id, 0) + 0.25
            second.trust[first.id] = second.trust.get(first.id, 0) + 0.25
        elif random.random() < 0.45:
            first.resentment[second.id] = first.resentment.get(second.id, 0) + 0.18
            second.resentment[first.id] = second.resentment.get(first.id, 0) + 0.12

    def create_border_encounter(self, party, mission_type):
        if getattr(self.world, "pending_choice", None) is not None:
            return False

        threat = self.get_border_value("threat")
        intel = self.get_border_value("intel")
        base_chance = {"scout": 0.15, "patrol": 0.22, "expedition": 0.38}[mission_type]
        encounter_chance = min(0.68, base_chance + threat / 350 + intel / 650)
        if random.random() >= encounter_chance:
            return False

        encounter_pools = {
            "scout": ["border_crossing", "spying_signs", "abandoned_egg"],
            "patrol": ["border_crossing", "wounded_outsider", "patrol_dispute"],
            "expedition": [
                "border_crossing",
                "wounded_outsider",
                "spying_signs",
                "abandoned_egg",
                "aid_request",
                "patrol_dispute",
            ],
        }
        incident = random.choice(encounter_pools[mission_type])
        encounter_data = {
            "border_crossing": (
                "The patrol has cornered an unfamiliar dragon crossing into tribal territory. "
                "The stranger claims to be lost, but their story is difficult to verify.",
                [
                    ("question_stranger", "Question the stranger before deciding"),
                    ("escort_away", "Escort them beyond the border"),
                    ("detain_stranger", "Detain them as a possible threat"),
                ],
            ),
            "wounded_outsider": (
                "A badly wounded outsider has collapsed beside the border trail and is asking "
                "the patrol for protection.",
                [
                    ("offer_sanctuary", "Bring the outsider into the village"),
                    ("limited_aid", "Provide supplies but keep the border closed"),
                    ("turn_away", "Turn the outsider away"),
                ],
            ),
            "spying_signs": (
                "The patrol discovered concealed tracks and observation points overlooking the "
                "tribe's territory. Someone may be studying the border.",
                [
                    ("lay_trap", "Lay a trap for the suspected spies"),
                    ("reinforce_routes", "Quietly reinforce the vulnerable routes"),
                    ("observe_spies", "Watch and gather more information"),
                ],
            ),
            "abandoned_egg": (
                "A cold, unattended dragon egg has been found in a sheltered hollow just beyond "
                "the recognised border.",
                [
                    ("rescue_egg", "Bring the egg to the hatchery"),
                    ("search_for_parents", "Search the surrounding territory first"),
                    ("leave_egg", "Leave it where it was found"),
                ],
            ),
            "aid_request": (
                "Messengers from a neighbouring tribe report a dangerous route collapse and ask "
                "for immediate assistance.",
                [
                    ("send_supplies", "Send food and emergency supplies"),
                    ("send_escort", "Send part of the patrol to assist"),
                    ("refuse_aid", "Refuse and protect your own border"),
                ],
            ),
            "patrol_dispute": (
                "The patrol has located an armed group near the boundary, but its members disagree "
                "over whether to confront them.",
                [
                    ("engage_group", "Confront the group immediately"),
                    ("shadow_group", "Follow them without being seen"),
                    ("withdraw_report", "Withdraw and report to the tribe"),
                ],
            ),
        }
        text, options = encounter_data[incident]
        self.world.pending_choice = {
            "type": "border_crisis",
            "location": "border",
            "incident": incident,
            "party_ids": [dragon.id for dragon in party],
            "text": text,
            "options": [{"id": option_id, "text": label} for option_id, label in options],
        }
        log_event(
            self.world,
            "A border patrol has encountered a situation requiring the tribe's attention.",
            involved_ids=[dragon.id for dragon in party],
            event_type="border",
            importance=5,
        )
        return True

    def dispatch_mission(self, mission_type):
        party = self.get_party()
        if not party or self.get_actions_remaining() <= 0:
            return

        profile = self.get_party_profile(mission_type)
        success = random.randint(1, 100) <= profile["success"]
        leader = random.choice(party)

        if mission_type == "scout":
            if success:
                self.change_border_value("intel", 12)
                self.change_border_value("threat", -2)
                text = f"{leader.name}'s patrol mapped hidden approaches and returned with a clear report."
                effect = "Border intelligence improved substantially."
            else:
                self.change_border_value("intel", 3)
                self.change_border_value("threat", 5)
                text = f"{leader.name}'s patrol lost the trail and returned with an incomplete report."
                effect = "Uncertainty and unseen movement increased along the border."
        elif mission_type == "patrol":
            if success:
                self.change_border_value("security", 10)
                self.change_border_value("threat", -8)
                text = f"{leader.name}'s patrol secured the vulnerable routes without incident."
                effect = "The border is safer and hostile activity has receded."
            else:
                self.change_border_value("security", -6)
                self.change_border_value("threat", 8)
                text = f"{leader.name}'s patrol was forced away from a contested route."
                effect = "The failed patrol weakened border control and emboldened outside threats."
        else:
            if success:
                found_food = random.randint(5, 14)
                self.world.food_stores = getattr(self.world, "food_stores", 0) + found_food
                self.change_border_value("intel", 8)
                self.change_border_value("security", 4)
                self.change_border_value("threat", -4)
                text = f"{leader.name}'s expedition returned safely from beyond the known routes."
                effect = f"The patrol brought back valuable intelligence and {found_food} food."
            else:
                self.change_border_value("security", -5)
                self.change_border_value("threat", 12)
                self.world.tension = getattr(self.world, "tension", 0) + 0.08
                text = f"{leader.name}'s expedition encountered danger and retreated in disorder."
                effect = "The expedition exposed weaknesses and left the tribe unsettled."

        injury_text = ""
        if not success and mission_type in {"patrol", "expedition"}:
            base_risk = 0.16 if mission_type == "patrol" else 0.38
            injury_risk = base_risk * (1.0 - profile["injury_protection"])
            if random.random() < injury_risk:
                injured = random.choice(party)
                if add_injury(self.world, injured):
                    injury_text = f" {injured.name} was injured and taken to the healer's den."

        self.apply_relationship_result(party, success)
        self.add_patrol_fatigue(party, mission_type)
        memory_type = f"border_{mission_type}_{'success' if success else 'failure'}"
        for dragon in party:
            add_memory(
                dragon,
                Memory(
                    type=memory_type,
                    moon=current_moon(self.world),
                    importance={"scout": 2, "patrol": 3, "expedition": 5}[mission_type],
                    reflection_weight=1.4 if mission_type == "expedition" else 1.0,
                    tags=["border", mission_type, "success" if success else "failure"],
                ),
            )

        log_event(
            self.world,
            f"{text}\n    {effect}{injury_text}",
            involved_ids=[dragon.id for dragon in party],
            event_type="border",
            importance=4 if mission_type == "expedition" else 3,
        )
        self.use_action()
        self.create_border_encounter(party, mission_type)

    # Drawing helpers -------------------------------------------------

    def draw_text_line(self, screen, text, x, y, font, color=TEXT, center=False):
        image = font.render(str(text), True, color)
        rect = image.get_rect()
        if center:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        screen.blit(image, rect)
        return rect

    def wrap_lines(self, text, font, width):
        lines = []
        for paragraph in str(text).split("\n"):
            words = paragraph.split()
            if not words:
                lines.append("")
                continue
            current = words[0]
            for word in words[1:]:
                candidate = f"{current} {word}"
                if font.size(candidate)[0] <= width:
                    current = candidate
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
        return lines

    def draw_wrapped(self, screen, text, rect, font, color=TEXT, line_height=None):
        line_height = line_height or font.get_linesize()
        y = rect.y
        for line in self.wrap_lines(text, font, rect.width):
            if y + line_height > rect.bottom:
                break
            self.draw_text_line(screen, line, rect.x, y, font, color)
            y += line_height
        return y

    def draw_panel(self, screen, rect, title=None, alpha=228):
        shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (5, 3, 2, 190), shadow.get_rect(), border_radius=12)
        screen.blit(shadow, (rect.x + 5, rect.y + 6))
        panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(panel, (*PANEL, alpha), panel.get_rect(), border_radius=12)
        screen.blit(panel, rect.topleft)
        pygame.draw.rect(screen, BRONZE, rect, 2, border_radius=12)
        pygame.draw.rect(screen, (61, 42, 31), rect.inflate(-8, -8), 1, border_radius=9)
        if title:
            self.draw_text_line(screen, title, rect.x + 16, rect.y + 13, self.heading_font, GOLD)

    def draw_medallion(self, screen, center, text, selected=False, radius=16):
        edge = GOLD if selected else BRONZE
        pygame.draw.circle(screen, (8, 5, 4), (center[0] + 2, center[1] + 3), radius + 3)
        pygame.draw.circle(screen, edge, center, radius + 2)
        pygame.draw.circle(screen, (76, 50, 34), center, radius - 1)
        image = self.medallion_font.render(text, True, CREAM)
        screen.blit(image, image.get_rect(center=center))

    def get_initials(self, name):
        words = str(name).split()
        if len(words) > 1:
            return "".join(word[0] for word in words[:2]).upper()
        return str(name)[:2].upper()

    def draw_gauge(self, screen, x, y, width, label, value, color):
        self.draw_text_line(screen, label, x, y, self.small_font, TEXT)
        value_image = self.small_font.render(f"{value}%", True, color)
        screen.blit(value_image, (x + width + 25 - value_image.get_width(), y))
        track = pygame.Rect(x, y + 17, width + 25, 9)
        pygame.draw.rect(screen, (23, 19, 17), track, border_radius=4)
        fill = pygame.Rect(track.x, track.y, int(track.width * value / 100), track.height)
        if fill.width > 0:
            pygame.draw.rect(screen, color, fill, border_radius=4)
        pygame.draw.rect(screen, (84, 63, 45), track, 1, border_radius=4)

    def draw_roster(self, screen, rect, mouse_pos):
        self.draw_panel(screen, rect, title="Patrol Roster")
        party = self.get_party()
        self.draw_text_line(
            screen,
            f"SELECTED PARTY  {len(party)}/3",
            rect.x + 16,
            rect.y + 48,
            self.small_font,
            GOLD,
        )
        names = ", ".join(dragon.name for dragon in party) if party else "Choose up to three dragons"
        self.draw_wrapped(
            screen,
            names,
            pygame.Rect(rect.x + 16, rect.y + 68, rect.width - 32, 42),
            self.small_font,
            TEXT if party else MUTED,
            15,
        )
        self.draw_text_line(
            screen,
            self.get_role_bonus_text(),
            rect.x + 16,
            rect.y + 109,
            self.tiny_font,
            MUTED,
        )
        readiness_text, readiness_color = self.get_party_readiness_text()
        self.draw_text_line(
            screen,
            readiness_text,
            rect.x + 16,
            rect.y + 126,
            self.tiny_font,
            readiness_color,
        )
        pygame.draw.line(screen, BRONZE, (rect.x + 16, rect.y + 149), (rect.right - 16, rect.y + 149), 1)
        self.draw_text_line(screen, "AVAILABLE DRAGONS", rect.x + 16, rect.y + 159, self.tiny_font, MUTED)

        list_rect = pygame.Rect(rect.x + 10, rect.y + 180, rect.width - 20, rect.height - 193)
        self._dragon_list_rect = list_rect
        old_clip = screen.get_clip()
        screen.set_clip(list_rect)

        dragons = self.get_dragons()
        row_height = 49
        self._list_content_height = len(dragons) * row_height
        y = list_rect.y + self.list_scroll
        for dragon in dragons:
            row = pygame.Rect(list_rect.x + 3, y + 3, list_rect.width - 6, 42)
            selected = dragon in party
            hovered = row.collidepoint(mouse_pos)
            if row.bottom >= list_rect.top and row.top <= list_rect.bottom:
                fill = (71, 49, 31) if hovered else (39, 31, 26)
                edge = GOLD if selected else ((151, 105, 57) if hovered else (73, 54, 40))
                pygame.draw.rect(screen, fill, row, border_radius=8)
                pygame.draw.rect(screen, edge, row, 2 if selected else 1, border_radius=8)
                self.draw_medallion(
                    screen,
                    (row.x + 22, row.centery),
                    self.get_initials(dragon.name),
                    selected,
                    14,
                )
                _, readiness, readiness_color = self.get_dragon_readiness(dragon)
                self.draw_text_line(screen, dragon.name, row.x + 43, row.y + 5, self.body_bold, CREAM)
                self.draw_text_line(
                    screen,
                    f"{dragon.role} • {readiness} • Fatigue {self.get_dragon_fatigue(dragon)}",
                    row.x + 43,
                    row.y + 23,
                    self.tiny_font,
                    readiness_color,
                )
                self.buttons.append(ClickTarget(row, lambda d=dragon: self.toggle_party_member(d)))
            y += row_height
        screen.set_clip(old_clip)

    def draw_missions(self, screen, rect, mouse_pos):
        self.draw_panel(screen, rect, title="Choose a Route")
        actions = self.get_actions_remaining()
        y = rect.y + 51
        risk_colors = {"scout": GREEN, "patrol": GOLD, "expedition": RED}
        for mission_type in ("scout", "patrol", "expedition"):
            data = self.MISSION_DATA[mission_type]
            card = pygame.Rect(rect.x + 14, y, rect.width - 28, 116)
            pygame.draw.rect(screen, (39, 31, 26), card, border_radius=9)
            pygame.draw.rect(screen, (84, 60, 42), card, 1, border_radius=9)
            pygame.draw.rect(screen, risk_colors[mission_type], (card.x, card.y, 5, card.height), border_radius=3)

            self.draw_text_line(screen, data["title"], card.x + 15, card.y + 10, self.body_bold, CREAM)
            risk_image = self.tiny_font.render(data["risk"], True, risk_colors[mission_type])
            screen.blit(risk_image, (card.right - 12 - risk_image.get_width(), card.y + 12))
            self.draw_wrapped(
                screen,
                data["description"],
                pygame.Rect(card.x + 15, card.y + 31, card.width - 30, 34),
                self.small_font,
                MUTED,
                14,
            )
            self.draw_text_line(screen, data["reward"], card.x + 15, card.y + 70, self.tiny_font, TEXT)

            chance_note, note_color = self.get_chance_note(mission_type)
            self.draw_text_line(
                screen,
                chance_note,
                card.x + 15,
                card.y + 91,
                self.tiny_font,
                note_color,
            )

            chance = self.get_party_profile(mission_type)["success"]
            enabled = bool(self.get_party()) and actions > 0
            if not actions:
                label = "No patrols"
            elif self.get_party():
                label = f"Dispatch • {chance}%"
            else:
                label = "Select party"
            button = BorderButton(
                pygame.Rect(card.x + 205, card.y + 82, 120, 28),
                label,
                lambda m=mission_type: self.dispatch_mission(m),
                enabled=enabled,
                primary=True,
            )
            self.buttons.append(button)
            button.draw(screen, self.small_font, mouse_pos)
            y += 126

    def draw_status(self, screen, rect, mouse_pos):
        self.draw_panel(screen, rect, title="Border Watch")
        security = self.get_border_value("security")
        intel = self.get_border_value("intel")
        threat = self.get_border_value("threat")
        self.draw_gauge(screen, rect.x + 17, rect.y + 50, 175, "SECURITY", security, GREEN)
        self.draw_gauge(screen, rect.x + 17, rect.y + 88, 175, "INTEL", intel, BLUE)
        self.draw_gauge(screen, rect.x + 17, rect.y + 126, 175, "THREAT", threat, RED)

        if threat >= 70:
            condition, condition_color = "CRITICAL ACTIVITY", RED
        elif threat >= 45:
            condition, condition_color = "BORDER UNSETTLED", GOLD
        else:
            condition, condition_color = "ROUTES QUIET", GREEN
        self.draw_text_line(screen, condition, rect.centerx, rect.y + 176, self.body_bold, condition_color, center=True)

        pygame.draw.line(screen, BRONZE, (rect.x + 15, rect.y + 199), (rect.right - 15, rect.y + 199), 1)
        self.draw_text_line(screen, "RECENT DISPATCHES", rect.x + 17, rect.y + 211, self.tiny_font, MUTED)
        log_rect = pygame.Rect(rect.x + 11, rect.y + 232, rect.width - 22, rect.height - 245)
        self._log_rect = log_rect
        pygame.draw.rect(screen, (20, 17, 15), log_rect, border_radius=8)
        pygame.draw.rect(screen, (72, 53, 40), log_rect, 1, border_radius=8)

        events = [
            event
            for event in getattr(self.world, "event_log", [])
            if isinstance(event, dict) and event.get("type") == "border"
        ][-25:]
        lines_by_event = []
        for event in reversed(events):
            lines = self.wrap_lines(f"• {event.get('text', '')}", self.tiny_font, log_rect.width - 22)
            lines_by_event.append(lines)
        self._log_content_height = sum(max(34, len(lines) * 14 + 12) for lines in lines_by_event)

        old_clip = screen.get_clip()
        screen.set_clip(log_rect)
        y = log_rect.y + 10 + self.log_scroll
        if not lines_by_event:
            self.draw_text_line(screen, "No patrol reports yet.", log_rect.x + 10, y, self.small_font, MUTED)
        for lines in lines_by_event:
            for line in lines:
                self.draw_text_line(screen, line, log_rect.x + 10, y, self.tiny_font, TEXT)
                y += 14
            y += 12
        screen.set_clip(old_clip)

    def draw(self, screen):
        self.buttons.clear()
        mouse_pos = pygame.mouse.get_pos()

        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill((22, 18, 15))
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((10, 7, 5, 142))
        screen.blit(veil, (0, 0))

        pygame.draw.rect(screen, (25, 17, 12), (18, 18, 964, 624), border_radius=18)
        pygame.draw.rect(screen, BRONZE, (18, 18, 964, 624), 3, border_radius=18)
        pygame.draw.rect(screen, (73, 49, 34), (27, 27, 946, 606), 1, border_radius=15)

        header = pygame.Rect(306, 28, 388, 82)
        self.draw_panel(screen, header, alpha=240)
        self.draw_text_line(screen, "BORDER ROUTES", header.centerx, header.y + 29, self.title_font_fantasy, CREAM, center=True)
        self.draw_text_line(
            screen,
            "Guard the territory. Learn what waits beyond it.",
            header.centerx,
            header.y + 57,
            self.small_font,
            MUTED,
            center=True,
        )

        condition_text, condition_color = self.get_border_condition()
        threat = self.get_border_value("threat")
        actions = self.get_actions_remaining()
        for badge, heading, value, detail, value_color in (
            (
                pygame.Rect(48, 40, 225, 58),
                "BORDER THREAT",
                f"{threat}%",
                condition_text,
                condition_color,
            ),
            (
                pygame.Rect(727, 40, 225, 58),
                "PATROLS REMAINING",
                f"{actions} / 2",
                "This moon",
                GOLD if actions else RED,
            ),
        ):
            self.draw_panel(screen, badge, alpha=235)
            self.draw_text_line(screen, heading, badge.x + 15, badge.y + 9, self.tiny_font, MUTED)
            value_image = self.heading_font.render(value, True, value_color)
            screen.blit(value_image, (badge.x + 15, badge.y + 27))
            detail_image = self.tiny_font.render(detail, True, MUTED)
            screen.blit(detail_image, (badge.x + 67, badge.y + 32))

        self.draw_roster(screen, pygame.Rect(28, 128, 270, 495), mouse_pos)
        self.draw_missions(screen, pygame.Rect(313, 128, 370, 495), mouse_pos)
        self.draw_status(screen, pygame.Rect(698, 128, 274, 495), mouse_pos)

        return_button = BorderButton(
            pygame.Rect(422, 651, 156, 36),
            "RETURN TO MAP",
            lambda: self.change_screen("locations"),
        )
        self.buttons.append(return_button)
        return_button.draw(screen, self.small_font, mouse_pos)

    def update(self, dt):
        pass

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()
            if self._dragon_list_rect.collidepoint(mouse_pos):
                visible = self._dragon_list_rect.height
                maximum = max(0, self._list_content_height - visible)
                self.list_scroll = clamp(self.list_scroll + event.y * 28, -maximum, 0)
            elif self._log_rect.collidepoint(mouse_pos):
                visible = self._log_rect.height
                maximum = max(0, self._log_content_height - visible + 20)
                self.log_scroll = clamp(self.log_scroll + event.y * 28, -maximum, 0)

        for button in self.buttons:
            button.handle_event(event)
