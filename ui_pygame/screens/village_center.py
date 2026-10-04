import random
from pathlib import Path

import pygame

from ui_pygame.core.base_screen import BaseScreen


WIDTH, HEIGHT = 1000, 700
TEXT = (236, 222, 196)
MUTED = (176, 158, 132)
GOLD = (227, 183, 84)
BRONZE = (133, 91, 53)
CREAM = (248, 230, 192)
PANEL = (31, 25, 20)
GREEN = (111, 178, 120)
RED = (196, 83, 68)
BLUE = (112, 158, 185)


def find_project_root():
    source = Path(__file__).resolve()
    candidates = [source.parent, *source.parents, Path.cwd(), *Path.cwd().parents]
    checked = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in checked:
            continue
        checked.add(candidate)
        if (candidate / "assets").is_dir():
            return candidate
    return source.parents[2]


class ClickTarget:
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


class VillageButton(ClickTarget):
    def __init__(self, rect, label, callback, enabled=True, primary=False, warning=False):
        super().__init__(rect, callback, enabled)
        self.label = label
        self.primary = primary
        self.warning = warning

    def draw(self, screen, font, mouse_pos):
        hovered = self.enabled and self.rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (7, 5, 4), self.rect.move(0, 3), border_radius=7)
        if not self.enabled:
            edge, fill, color = (72, 65, 58), (40, 37, 34), (112, 104, 94)
        elif self.warning:
            edge = (224, 132, 92) if hovered else (151, 80, 58)
            fill = (94, 42, 31) if hovered else (66, 34, 28)
            color = CREAM
        elif self.primary:
            edge = GOLD if hovered else (177, 121, 53)
            fill = (111, 66, 31) if hovered else (79, 48, 27)
            color = CREAM
        else:
            edge = GOLD if hovered else (105, 76, 53)
            fill = (61, 45, 34) if hovered else (42, 34, 29)
            color = TEXT
        pygame.draw.rect(screen, edge, self.rect, border_radius=7)
        inner = self.rect.inflate(-5, -5)
        pygame.draw.rect(screen, fill, inner, border_radius=5)
        if self.enabled:
            pygame.draw.line(
                screen,
                (211, 165, 92),
                (inner.x + 7, inner.y + 3),
                (inner.right - 7, inner.y + 3),
                1,
            )
        label = self.label
        while label and font.size(label)[0] > self.rect.width - 14:
            label = label[:-1]
        if label != self.label:
            label = label.rstrip() + "…"
        image = font.render(label, True, color)
        screen.blit(image, image.get_rect(center=self.rect.center))


class VillageCenterScreen(BaseScreen):
    MAX_ACTIONS = 2
    VILLAGE_ALIASES = {"village", "village_center", "Village Center"}

    def __init__(self, world, change_screen):
        super().__init__()
        self.world = world
        self.change_screen = change_screen
        self.buttons = []
        self.notice = ""
        self.notice_color = GOLD

        self.title_fantasy = pygame.font.SysFont("georgia", 29, bold=True)
        self.heading = pygame.font.SysFont("georgia", 16, bold=True)
        self.body = pygame.font.SysFont("georgia", 12)
        self.body_bold = pygame.font.SysFont("georgia", 12, bold=True)
        self.small = pygame.font.SysFont("georgia", 10)
        self.tiny = pygame.font.SysFont("georgia", 9)

        self.project_root = find_project_root()
        self.bg_image = self.load_background()
        self.ensure_state()
        self.scene = self.get_or_create_scene()

    # World and social data -----------------------------------------

    def ensure_state(self):
        if not hasattr(self.world, "world_flags") or self.world.world_flags is None:
            self.world.world_flags = {}
        if not hasattr(self.world, "event_log") or self.world.event_log is None:
            self.world.event_log = []

        flags = self.world.world_flags
        current_moon = int(getattr(self.world, "moon", 0) or 0)
        if flags.get("village_action_moon") != current_moon:
            flags["village_action_moon"] = current_moon
            flags["village_actions_used"] = 0
            flags.pop("village_scene", None)
            flags.pop("village_scene_result", None)
            flags.pop("village_scene_resolved_moon", None)
        flags.setdefault("village_actions_used", 0)
        flags.setdefault("village_social_log", [])

    def get_dragons(self):
        dragons = getattr(self.world, "dragons", self.world if self.world is not None else [])
        return [
            dragon
            for dragon in dragons
            if str(getattr(dragon, "status", "Alive")).lower() not in {"dead", "deceased"}
        ]

    def get_dragons_at_village(self):
        return [
            dragon
            for dragon in self.get_dragons()
            if getattr(dragon, "location", None) in self.VILLAGE_ALIASES
        ]

    def dragon_id(self, dragon):
        return getattr(dragon, "id", getattr(dragon, "name", "unknown"))

    def same_id(self, first, second):
        return str(first) == str(second)

    def get_dragon_by_id(self, dragon_id):
        return next(
            (dragon for dragon in self.get_dragons() if self.same_id(self.dragon_id(dragon), dragon_id)),
            None,
        )

    def relation_ids(self, dragon, attribute):
        values = getattr(dragon, attribute, []) or []
        if isinstance(values, (str, int)):
            return [values]
        return list(values)

    def dict_value(self, dragon, attribute, other_id):
        values = getattr(dragon, attribute, {}) or {}
        if not isinstance(values, dict):
            return 0.0
        for key, value in values.items():
            if self.same_id(key, other_id):
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return 0.0
        return 0.0

    def change_dict_value(self, dragon, attribute, other_id, amount, minimum=None, maximum=None):
        values = getattr(dragon, attribute, None)
        if not isinstance(values, dict):
            values = {}
            setattr(dragon, attribute, values)
        key = next((existing for existing in values if self.same_id(existing, other_id)), other_id)
        try:
            current = float(values.get(key, 0.0) or 0.0)
        except (TypeError, ValueError):
            current = 0.0
        updated = current + amount
        if minimum is not None:
            updated = max(minimum, updated)
        if maximum is not None:
            updated = min(maximum, updated)
        values[key] = updated
        return updated

    def add_reputation(self, dragon, trait, amount):
        reputation = getattr(dragon, "reputation", None)
        if not isinstance(reputation, dict):
            reputation = {}
            setattr(dragon, "reputation", reputation)
        reputation[trait] = float(reputation.get(trait, 0.0) or 0.0) + amount

    def actions_used(self):
        return int(self.world.world_flags.get("village_actions_used", 0) or 0)

    def actions_remaining(self):
        return max(0, self.MAX_ACTIONS - self.actions_used())

    def consume_action(self):
        self.world.world_flags["village_actions_used"] = min(
            self.MAX_ACTIONS,
            self.actions_used() + 1,
        )

    def social_counts(self):
        living = self.get_dragons()
        friend_pairs = set()
        rival_pairs = set()
        grieving = 0
        for dragon in living:
            dragon_key = str(self.dragon_id(dragon))
            for other_id in self.relation_ids(dragon, "friends"):
                friend_pairs.add(tuple(sorted((dragon_key, str(other_id)))))
            for other_id in self.relation_ids(dragon, "rivals"):
                rival_pairs.add(tuple(sorted((dragon_key, str(other_id)))))
            if float(getattr(dragon, "grief_level", 0) or 0) > 0:
                grieving += 1
        return len(friend_pairs), len(rival_pairs), grieving

    def community_mood(self):
        bonds, rivalries, grieving = self.social_counts()
        tension = float(getattr(self.world, "tension", 0) or 0)
        if tension >= 7 or rivalries > bonds + 2:
            return "STRAINED", "Old disagreements are close to the surface.", RED
        if grieving:
            return "SOMBER", "The village is carrying recent losses together.", BLUE
        if bonds >= max(2, rivalries * 2):
            return "WARM", "Familiar bonds make the village feel settled.", GREEN
        return "STEADY", "Daily life continues with cautious stability.", GOLD

    # Scene generation ----------------------------------------------

    def find_pair_from_relation(self, dragons, attribute, numeric_attribute, threshold):
        dragon_ids = {str(self.dragon_id(dragon)): dragon for dragon in dragons}
        for dragon in dragons:
            first_id = self.dragon_id(dragon)
            for other_id in self.relation_ids(dragon, attribute):
                other = dragon_ids.get(str(other_id))
                if other and not self.same_id(first_id, other_id):
                    return dragon, other
            for other in dragons:
                if dragon is other:
                    continue
                if self.dict_value(dragon, numeric_attribute, self.dragon_id(other)) >= threshold:
                    return dragon, other
        return None

    def choose_scene(self):
        dragons = sorted(self.get_dragons_at_village(), key=lambda dragon: str(getattr(dragon, "name", "")))
        moon = int(getattr(self.world, "moon", 0) or 0)
        if not dragons:
            return {"moon": moon, "kind": "empty", "a_id": None, "b_id": None}
        if len(dragons) == 1:
            return {
                "moon": moon,
                "kind": "solitude",
                "a_id": self.dragon_id(dragons[0]),
                "b_id": None,
            }

        pair = self.find_pair_from_relation(dragons, "rivals", "resentment", 0.75)
        if pair:
            return {
                "moon": moon,
                "kind": "tension",
                "a_id": self.dragon_id(pair[0]),
                "b_id": self.dragon_id(pair[1]),
            }

        grieving = [dragon for dragon in dragons if float(getattr(dragon, "grief_level", 0) or 0) > 0]
        if grieving:
            mourner = max(grieving, key=lambda dragon: float(getattr(dragon, "grief_level", 0) or 0))
            companion = next((dragon for dragon in dragons if dragon is not mourner), None)
            return {
                "moon": moon,
                "kind": "grief",
                "a_id": self.dragon_id(mourner),
                "b_id": self.dragon_id(companion) if companion else None,
            }

        pair = self.find_pair_from_relation(dragons, "friends", "trust", 0.75)
        if pair:
            return {
                "moon": moon,
                "kind": "bond",
                "a_id": self.dragon_id(pair[0]),
                "b_id": self.dragon_id(pair[1]),
            }

        offset = moon % len(dragons)
        first = dragons[offset]
        second = dragons[(offset + 1) % len(dragons)]
        return {
            "moon": moon,
            "kind": "casual",
            "a_id": self.dragon_id(first),
            "b_id": self.dragon_id(second),
        }

    def get_or_create_scene(self):
        flags = self.world.world_flags
        moon = int(getattr(self.world, "moon", 0) or 0)
        scene = flags.get("village_scene")
        if not isinstance(scene, dict) or scene.get("moon") != moon:
            scene = self.choose_scene()
            flags["village_scene"] = scene
        return scene

    def scene_dragons(self):
        return (
            self.get_dragon_by_id(self.scene.get("a_id")),
            self.get_dragon_by_id(self.scene.get("b_id")),
        )

    def scene_copy(self):
        first, second = self.scene_dragons()
        first_name = getattr(first, "name", "A quiet dragon")
        second_name = getattr(second, "name", "another dragon")
        kind = self.scene.get("kind")
        if kind == "tension":
            return {
                "title": "A DISAGREEMENT DRAWS EYES",
                "summary": f"{first_name} and {second_name} are speaking in careful, clipped voices near the centre of the village.",
                "lines": [
                    (first_name, "We keep circling the same disagreement."),
                    (second_name, "Because neither of us believes it was truly settled."),
                ],
                "options": (
                    ("MEDIATE CALMLY", "mediate"),
                    ("LET THEM SPEAK", "listen"),
                    ("SEPARATE THEM", "separate"),
                ),
            }
        if kind == "grief":
            return {
                "title": "A QUIET MOMENT",
                "summary": f"{first_name} has withdrawn from the bustle. {second_name} notices, but seems uncertain whether to approach.",
                "lines": [
                    (second_name, "You do not have to carry all of this alone."),
                    (first_name, "I know. I simply do not know what to say yet."),
                ],
                "options": (
                    ("ENCOURAGE SUPPORT", "comfort"),
                    ("INVITE THEM TO THE FIRE", "include"),
                    ("GIVE THEM SPACE", "space"),
                ),
            }
        if kind == "bond":
            return {
                "title": "FAMILIAR COMPANY",
                "summary": f"{first_name} and {second_name} have found an easy rhythm together amid the village noise.",
                "lines": [
                    (first_name, "It is good to have one conversation that does not feel like a duty."),
                    (second_name, "Then we should make time for more of them."),
                ],
                "options": (
                    ("ENCOURAGE THE BOND", "encourage"),
                    ("SUGGEST WORKING TOGETHER", "collaborate"),
                    ("LEAVE THEM TO IT", "leave"),
                ),
            }
        if kind == "casual":
            return {
                "title": "PATHS CROSS IN THE VILLAGE",
                "summary": f"{first_name} and {second_name} pause near the central fire as their duties bring them together.",
                "lines": [
                    (first_name, "The village feels different every moon."),
                    (second_name, "Perhaps we are the ones who keep changing."),
                ],
                "options": (
                    ("ENCOURAGE CONVERSATION", "introduce"),
                    ("ASK ABOUT THEIR HOPES", "hopes"),
                    ("LET THE MOMENT UNFOLD", "unfold"),
                ),
            }
        if kind == "solitude":
            return {
                "title": "A LONELY VILLAGE CENTRE",
                "summary": f"{first_name} is the only dragon lingering here. Most of the tribe is occupied elsewhere.",
                "lines": [],
                "options": (),
            }
        return {
            "title": "THE CENTRE STANDS QUIET",
            "summary": "No dragons are currently gathered here. The communal fires burn low while the tribe tends to duties elsewhere.",
            "lines": [],
            "options": (),
        }

    # Social consequences -------------------------------------------

    def append_event(self, text, involved=None, importance=2):
        involved = [self.dragon_id(dragon) for dragon in (involved or []) if dragon]
        event = {
            "type": "social",
            "text": text,
            "moon": int(getattr(self.world, "moon", 0) or 0),
            "involved_ids": involved,
            "importance": importance,
            "location": "village",
            "tags": ["social", "village"],
        }
        self.world.event_log.append(event)
        self.world.event_log = self.world.event_log[-100:]
        social_log = self.world.world_flags.setdefault("village_social_log", [])
        social_log.append(event)
        self.world.world_flags["village_social_log"] = social_log[-12:]

    def set_scene_result(self, result):
        moon = int(getattr(self.world, "moon", 0) or 0)
        self.world.world_flags["village_scene_result"] = result
        self.world.world_flags["village_scene_resolved_moon"] = moon
        self.notice = result
        self.notice_color = GREEN

    def scene_is_resolved(self):
        return self.world.world_flags.get("village_scene_resolved_moon") == int(
            getattr(self.world, "moon", 0) or 0
        )

    def soften_rivalry(self, first, second, amount):
        if not first or not second:
            return
        first_id = self.dragon_id(first)
        second_id = self.dragon_id(second)
        first_resentment = self.change_dict_value(first, "resentment", second_id, -amount, minimum=0.0)
        second_resentment = self.change_dict_value(second, "resentment", first_id, -amount, minimum=0.0)
        self.change_dict_value(first, "trust", second_id, amount * 0.25, maximum=10.0)
        self.change_dict_value(second, "trust", first_id, amount * 0.25, maximum=10.0)
        if max(first_resentment, second_resentment) < 0.5:
            for dragon, other_id in ((first, second_id), (second, first_id)):
                rivals = getattr(dragon, "rivals", None)
                if isinstance(rivals, set):
                    match = next((value for value in rivals if self.same_id(value, other_id)), None)
                    if match is not None:
                        rivals.discard(match)
                elif isinstance(rivals, list):
                    dragon.rivals = [value for value in rivals if not self.same_id(value, other_id)]

    def strengthen_bond(self, first, second, amount):
        if not first or not second:
            return
        first_id = self.dragon_id(first)
        second_id = self.dragon_id(second)
        first_trust = self.change_dict_value(first, "trust", second_id, amount, maximum=10.0)
        second_trust = self.change_dict_value(second, "trust", first_id, amount, maximum=10.0)
        if min(first_trust, second_trust) >= 1.0:
            for dragon, other_id in ((first, second_id), (second, first_id)):
                friends = getattr(dragon, "friends", None)
                if isinstance(friends, set):
                    friends.add(other_id)
                elif isinstance(friends, list):
                    if not any(self.same_id(value, other_id) for value in friends):
                        friends.append(other_id)

    def resolve_scene(self, choice):
        if self.actions_remaining() <= 0 or self.scene_is_resolved():
            self.notice = "No community actions remain this moon."
            self.notice_color = RED
            return
        first, second = self.scene_dragons()
        kind = self.scene.get("kind")
        if kind not in {"tension", "grief", "bond", "casual"}:
            return

        if choice == "mediate":
            self.soften_rivalry(first, second, 0.35)
            result = f"{first.name} and {second.name} leave the discussion with less hostility than they brought to it."
        elif choice == "listen":
            self.soften_rivalry(first, second, 0.14)
            result = f"{first.name} and {second.name} finally say what had been left unspoken. The disagreement remains, but it is clearer."
        elif choice == "separate":
            self.world.tension = max(0.0, float(getattr(self.world, "tension", 0) or 0) - 0.35)
            result = f"{first.name} and {second.name} are sent to cool off before the dispute spreads through the village."
        elif choice == "comfort":
            first.grief_level = max(0, float(getattr(first, "grief_level", 0) or 0) - 2)
            self.strengthen_bond(first, second, 0.16)
            self.add_reputation(second, "kind", 0.08)
            result = f"{second.name} stays with {first.name}. The loss remains, but it no longer feels entirely solitary."
        elif choice == "include":
            first.grief_level = max(0, float(getattr(first, "grief_level", 0) or 0) - 1)
            self.strengthen_bond(first, second, 0.10)
            result = f"{first.name} joins the dragons around the communal fire and quietly returns to village life."
        elif choice == "space":
            first.grief_level = max(0, float(getattr(first, "grief_level", 0) or 0) - 0.5)
            result = f"The tribe respects {first.name}'s need for quiet without forgetting to keep watch over them."
        elif choice == "encourage":
            self.strengthen_bond(first, second, 0.14)
            self.add_reputation(first, "kind", 0.04)
            self.add_reputation(second, "kind", 0.04)
            result = f"{first.name} and {second.name} are reminded that their friendship matters to the wider tribe."
        elif choice == "collaborate":
            self.strengthen_bond(first, second, 0.10)
            self.add_reputation(first, "reliable", 0.06)
            self.add_reputation(second, "reliable", 0.06)
            result = f"{first.name} and {second.name} agree to share their next suitable duty."
        elif choice == "leave":
            self.strengthen_bond(first, second, 0.04)
            result = f"The conversation between {first.name} and {second.name} continues without interruption."
        elif choice == "introduce":
            self.strengthen_bond(first, second, 0.12)
            result = f"A brief exchange becomes a genuine introduction between {first.name} and {second.name}."
        elif choice == "hopes":
            self.strengthen_bond(first, second, 0.09)
            self.add_reputation(first, "kind", 0.03)
            self.add_reputation(second, "kind", 0.03)
            result = f"{first.name} and {second.name} speak more openly than either expected about what they want from the moons ahead."
        else:
            self.strengthen_bond(first, second, 0.05)
            result = f"The chance encounter between {first.name} and {second.name} is allowed to find its own shape."

        self.consume_action()
        self.append_event(result, [first, second])
        self.set_scene_result(result)

    def host_gathering(self, gathering):
        if self.actions_remaining() <= 0:
            self.notice = "No community actions remain this moon."
            self.notice_color = RED
            return
        dragons = self.get_dragons_at_village()
        if not dragons:
            self.notice = "There are no dragons here to gather."
            self.notice_color = RED
            return

        if gathering == "meal":
            cost = 8
            food = int(getattr(self.world, "food_stores", 0) or 0)
            if food < cost:
                self.notice = f"The tribe needs {cost} food to host a shared meal."
                self.notice_color = RED
                return
            self.world.food_stores = food - cost
            for index, first in enumerate(dragons):
                self.add_reputation(first, "kind", 0.02)
                for second in dragons[index + 1:]:
                    self.strengthen_bond(first, second, 0.04)
            self.world.tension = max(0.0, float(getattr(self.world, "tension", 0) or 0) - 0.45)
            result = f"The tribe shares a meal in the Village Center. Familiar faces linger together after the food is gone. (-{cost} food)"
        elif gathering == "stories":
            storyteller = max(
                dragons,
                key=lambda dragon: int(getattr(dragon, "age_moons", getattr(dragon, "age", 0)) or 0),
            )
            self.add_reputation(storyteller, "respected", 0.10)
            for dragon in dragons:
                if dragon is not storyteller:
                    self.change_dict_value(dragon, "trust", self.dragon_id(storyteller), 0.04, maximum=10.0)
            result = f"{storyteller.name} holds the village's attention with stories of earlier moons. Old lessons feel newly relevant."
        else:
            celebrated = max(
                dragons,
                key=lambda dragon: sum(
                    max(0.0, float(value or 0.0))
                    for value in (getattr(dragon, "reputation", {}) or {}).values()
                ),
            )
            self.add_reputation(celebrated, "respected", 0.12)
            for dragon in dragons:
                if dragon is not celebrated:
                    self.change_dict_value(dragon, "trust", self.dragon_id(celebrated), 0.025, maximum=10.0)
            result = f"The tribe publicly recognizes {celebrated.name}'s contributions. The praise carries beyond the gathering."

        self.consume_action()
        self.append_event(result, dragons, importance=3)
        self.notice = result
        self.notice_color = GREEN

    # Background and display data ----------------------------------

    def tribe_slug(self):
        return (
            str(getattr(self.world, "tribe_name", ""))
            .lower()
            .replace(" tribe", "")
            .replace(" ", "")
        )

    def load_background(self):
        slug = self.tribe_slug()
        candidates = [
            self.project_root / "assets" / slug / "village_center_bg.png",
            self.project_root / "assets" / slug / "village_bg.png",
            self.project_root / "assets" / slug / "location_map.png",
            self.project_root / "assets" / "menu" / "village_bg.png",
            self.project_root / "assets" / "menu" / "main_locations_bg.png",
        ]
        for path in candidates:
            if not path.exists():
                continue
            try:
                image = pygame.image.load(str(path)).convert()
                return pygame.transform.scale(image, (WIDTH, HEIGHT))
            except Exception as error:
                print(f"Could not load Village Center background {path}: {error}")
        return None

    def recent_social_events(self, limit=3):
        events = []
        for event in reversed(list(getattr(self.world, "event_log", []) or [])):
            if not isinstance(event, dict):
                continue
            tags = [str(tag).lower() for tag in event.get("tags", []) or []]
            event_type = str(event.get("type", "")).lower()
            if event_type == "social" or "social" in tags or "relationship" in tags:
                events.append(event)
            if len(events) >= limit:
                break
        return events

    # Drawing helpers ------------------------------------------------

    def draw_text(self, screen, text, x, y, font, color=TEXT, center=False, right=False):
        image = font.render(str(text), True, color)
        rect = image.get_rect()
        if center:
            rect.center = (x, y)
        elif right:
            rect.topright = (x, y)
        else:
            rect.topleft = (x, y)
        screen.blit(image, rect)
        return rect

    def fit_text(self, text, font, max_width):
        text = str(text)
        if font.size(text)[0] <= max_width:
            return text
        while text and font.size(text + "…")[0] > max_width:
            text = text[:-1]
        return text + "…"

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

    def draw_wrapped(self, screen, text, rect, font, color=TEXT, line_height=16, max_lines=None):
        y = rect.y
        lines = self.wrap_lines(text, font, rect.width)
        if max_lines is not None:
            lines = lines[:max_lines]
        for line in lines:
            self.draw_text(screen, line, rect.x, y, font, color)
            y += line_height
        return y

    def draw_panel(self, screen, rect, title=None, alpha=226):
        shadow = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow, (5, 3, 2, 190), shadow.get_rect(), border_radius=12)
        screen.blit(shadow, (rect.x + 5, rect.y + 6))
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (*PANEL, alpha), panel.get_rect(), border_radius=12)
        screen.blit(panel, rect.topleft)
        pygame.draw.rect(screen, BRONZE, rect, 2, border_radius=12)
        pygame.draw.rect(screen, (61, 42, 31), rect.inflate(-8, -8), 1, border_radius=9)
        if title:
            self.draw_text(screen, title, rect.x + 15, rect.y + 13, self.heading, GOLD)

    def draw_outer_frame(self, screen):
        outer = pygame.Rect(24, 18, WIDTH - 48, HEIGHT - 36)
        pygame.draw.rect(screen, (20, 13, 9), outer, 8, border_radius=22)
        pygame.draw.rect(screen, BRONZE, outer, 3, border_radius=22)
        pygame.draw.rect(screen, (79, 52, 35), outer.inflate(-12, -12), 2, border_radius=17)

    def draw_title_plaque(self, screen):
        rect = pygame.Rect(275, 25, 450, 82)
        points = [
            (rect.x + 15, rect.y),
            (rect.right - 15, rect.y),
            (rect.right, rect.y + 15),
            (rect.right, rect.bottom - 15),
            (rect.right - 15, rect.bottom),
            (rect.x + 15, rect.bottom),
            (rect.x, rect.bottom - 15),
            (rect.x, rect.y + 15),
        ]
        pygame.draw.polygon(screen, BRONZE, points)
        inner = rect.inflate(-5, -5)
        inner_points = [
            (inner.x + 12, inner.y),
            (inner.right - 12, inner.y),
            (inner.right, inner.y + 12),
            (inner.right, inner.bottom - 12),
            (inner.right - 12, inner.bottom),
            (inner.x + 12, inner.bottom),
            (inner.x, inner.bottom - 12),
            (inner.x, inner.y + 12),
        ]
        pygame.draw.polygon(screen, (30, 23, 18), inner_points)
        self.draw_text(screen, "VILLAGE CENTER", rect.centerx, rect.y + 28, self.title_fantasy, CREAM, center=True)
        self.draw_text(screen, "THE SOCIAL HEART OF THE TRIBE", rect.centerx, rect.y + 58, self.tiny, GOLD, center=True)

    def draw_badges(self, screen):
        food = int(getattr(self.world, "food_stores", 0) or 0)
        left = pygame.Rect(42, 48, 172, 34)
        right = pygame.Rect(786, 48, 172, 34)
        for rect in (left, right):
            pygame.draw.rect(screen, (31, 25, 20), rect, border_radius=8)
            pygame.draw.rect(screen, BRONZE, rect, 1, border_radius=8)
        self.draw_text(screen, f"FOOD STORES  •  {food}", left.centerx, left.centery, self.small, GOLD, center=True)
        self.draw_text(
            screen,
            f"COMMUNITY ACTIONS  •  {self.actions_remaining()}/{self.MAX_ACTIONS}",
            right.centerx,
            right.centery,
            self.tiny,
            GOLD,
            center=True,
        )

    def draw_social_pulse(self, screen, rect):
        self.draw_panel(screen, rect, "SOCIAL PULSE")
        mood, description, mood_color = self.community_mood()
        bonds, rivalries, grieving = self.social_counts()
        village_dragons = self.get_dragons_at_village()

        pygame.draw.circle(screen, mood_color, (rect.x + 21, rect.y + 55), 5)
        self.draw_text(screen, mood, rect.x + 34, rect.y + 47, self.body_bold, mood_color)
        self.draw_wrapped(
            screen,
            description,
            pygame.Rect(rect.x + 15, rect.y + 72, rect.width - 30, 45),
            self.small,
            MUTED,
            14,
            3,
        )

        y = rect.y + 118
        metrics = (
            ("DRAGONS HERE", len(village_dragons), CREAM),
            ("KNOWN BONDS", bonds, GREEN),
            ("ACTIVE RIVALRIES", rivalries, RED),
            ("DRAGONS GRIEVING", grieving, BLUE),
        )
        for label, value, color in metrics:
            self.draw_text(screen, label, rect.x + 15, y, self.tiny, MUTED)
            self.draw_text(screen, value, rect.right - 16, y - 2, self.body_bold, color, right=True)
            y += 24

        pygame.draw.line(screen, (91, 65, 43), (rect.x + 15, y + 2), (rect.right - 15, y + 2), 1)
        self.draw_text(screen, "WHO IS HERE", rect.x + 15, y + 16, self.body_bold, GOLD)
        y += 42
        if not village_dragons:
            self.draw_text(screen, "The centre is currently empty.", rect.x + 15, y, self.small, MUTED)
            return
        for dragon in village_dragons[:5]:
            name = self.fit_text(getattr(dragon, "name", "Unknown"), self.body_bold, rect.width - 80)
            role = self.fit_text(getattr(dragon, "role", "Unknown"), self.tiny, rect.width - 80)
            pygame.draw.circle(screen, BRONZE, (rect.x + 22, y + 10), 10)
            initial = str(getattr(dragon, "name", "?"))[:1].upper()
            self.draw_text(screen, initial, rect.x + 22, y + 10, self.tiny, CREAM, center=True)
            self.draw_text(screen, name, rect.x + 40, y, self.body_bold, TEXT)
            self.draw_text(screen, role, rect.x + 40, y + 16, self.tiny, MUTED)
            y += 37
        if len(village_dragons) > 5:
            self.draw_text(screen, f"+{len(village_dragons) - 5} more gathered here", rect.x + 15, y, self.small, MUTED)

    def draw_scene(self, screen, rect, mouse_pos):
        self.draw_panel(screen, rect, "COMMUNITY SCENE")
        scene = self.scene_copy()
        self.draw_text(screen, scene["title"], rect.x + 16, rect.y + 48, self.body_bold, CREAM)
        y = self.draw_wrapped(
            screen,
            scene["summary"],
            pygame.Rect(rect.x + 16, rect.y + 72, rect.width - 32, 70),
            self.small,
            MUTED,
            15,
            4,
        )
        y += 8
        dialogue_rect = pygame.Rect(rect.x + 14, y, rect.width - 28, 118)
        pygame.draw.rect(screen, (22, 18, 15), dialogue_rect, border_radius=9)
        pygame.draw.rect(screen, (74, 52, 37), dialogue_rect, 1, border_radius=9)
        line_y = dialogue_rect.y + 12
        if not scene["lines"]:
            self.draw_text(screen, "No conversation is unfolding here.", dialogue_rect.x + 12, line_y, self.small, MUTED)
        for speaker, line in scene["lines"]:
            self.draw_text(screen, f"{speaker}:", dialogue_rect.x + 12, line_y, self.body_bold, GOLD)
            line_y = self.draw_wrapped(
                screen,
                line,
                pygame.Rect(dialogue_rect.x + 12, line_y + 17, dialogue_rect.width - 24, 40),
                self.small,
                TEXT,
                14,
                2,
            ) + 7

        result = self.world.world_flags.get("village_scene_result", "") if self.scene_is_resolved() else ""
        action_y = dialogue_rect.bottom + 13
        if result:
            self.draw_text(screen, "OUTCOME", rect.x + 16, action_y, self.tiny, GREEN)
            self.draw_wrapped(
                screen,
                result,
                pygame.Rect(rect.x + 16, action_y + 17, rect.width - 32, 75),
                self.small,
                TEXT,
                15,
                4,
            )
            return

        if not scene["options"]:
            self.draw_text(screen, "A larger gathering may still be organized.", rect.x + 16, action_y + 8, self.small, MUTED)
            return

        self.draw_text(screen, "HOW SHOULD THE TRIBE RESPOND?", rect.x + 16, action_y, self.tiny, GOLD)
        button_y = action_y + 20
        enabled = self.actions_remaining() > 0
        for label, choice in scene["options"]:
            button = VillageButton(
                (rect.x + 16, button_y, rect.width - 32, 35),
                label,
                lambda value=choice: self.resolve_scene(value),
                enabled=enabled,
                primary=choice in {"mediate", "comfort", "encourage", "introduce"},
            )
            self.buttons.append(button)
            button.draw(screen, self.small, mouse_pos)
            button_y += 42

    def draw_gatherings(self, screen, rect, mouse_pos):
        self.draw_panel(screen, rect, "COMMUNITY GATHERINGS")
        self.draw_wrapped(
            screen,
            "Organize one communal moment instead of directing individual lives.",
            pygame.Rect(rect.x + 14, rect.y + 47, rect.width - 28, 50),
            self.small,
            MUTED,
            14,
            3,
        )
        food = int(getattr(self.world, "food_stores", 0) or 0)
        has_dragons = bool(self.get_dragons_at_village())
        actions_available = self.actions_remaining() > 0
        gatherings = (
            ("SHARED MEAL  •  8 FOOD", "meal", actions_available and has_dragons and food >= 8),
            ("STORY CIRCLE", "stories", actions_available and has_dragons),
            ("HONOUR A CONTRIBUTION", "honour", actions_available and has_dragons),
        )
        y = rect.y + 102
        for label, gathering, enabled in gatherings:
            button = VillageButton(
                (rect.x + 14, y, rect.width - 28, 36),
                label,
                lambda value=gathering: self.host_gathering(value),
                enabled=enabled,
                primary=gathering == "meal",
            )
            self.buttons.append(button)
            button.draw(screen, self.tiny, mouse_pos)
            y += 44

        pygame.draw.line(screen, (91, 65, 43), (rect.x + 14, y + 2), (rect.right - 14, y + 2), 1)
        self.draw_text(screen, "RECENT SOCIAL CHANGES", rect.x + 14, y + 17, self.body_bold, GOLD)
        y += 44
        events = self.recent_social_events()
        if not events:
            self.draw_text(screen, "No recent social events recorded.", rect.x + 14, y, self.small, MUTED)
        for event in events:
            moon = event.get("moon")
            prefix = f"MOON {moon}  •  " if moon is not None else "•  "
            text = prefix + str(event.get("text", ""))
            y = self.draw_wrapped(
                screen,
                text,
                pygame.Rect(rect.x + 14, y, rect.width - 28, 62),
                self.tiny,
                TEXT,
                13,
                4,
            ) + 8

    def draw_notice(self, screen):
        if not self.notice:
            return
        rect = pygame.Rect(280, 602, 440, 35)
        surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surface, (23, 18, 15, 235), surface.get_rect(), border_radius=8)
        screen.blit(surface, rect.topleft)
        pygame.draw.rect(screen, self.notice_color, rect, 1, border_radius=8)
        text = self.fit_text(self.notice, self.small, rect.width - 24)
        self.draw_text(screen, text, rect.centerx, rect.centery, self.small, self.notice_color, center=True)

    # Screen lifecycle ----------------------------------------------

    def update(self, dt):
        pass

    def draw(self, screen):
        self.buttons.clear()
        if self.bg_image:
            screen.blit(self.bg_image, (0, 0))
        else:
            screen.fill((27, 20, 16))

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((7, 4, 2, 125))
        screen.blit(overlay, (0, 0))

        self.draw_outer_frame(screen)
        self.draw_title_plaque(screen)
        self.draw_badges(screen)

        mouse_pos = pygame.mouse.get_pos()
        self.draw_social_pulse(screen, pygame.Rect(38, 122, 245, 466))
        self.draw_scene(screen, pygame.Rect(298, 122, 414, 466), mouse_pos)
        self.draw_gatherings(screen, pygame.Rect(727, 122, 235, 466), mouse_pos)
        self.draw_notice(screen)

        return_button = VillageButton(
            (420, 646, 160, 38),
            "RETURN TO MAP",
            lambda: self.change_screen("locations"),
        )
        self.buttons.append(return_button)
        return_button.draw(screen, self.small, mouse_pos)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.change_screen("locations")
            return
        for button in self.buttons:
            button.handle_event(event)
