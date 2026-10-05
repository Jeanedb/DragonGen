"""Village Center v2.2 test: expanded social-scene viewer.

Place this file beside ``ui_pygame/screens/village_center.py`` and import
``VillageCenterScreen`` from this module while testing.  Version two subclasses
the existing screen so the original remains available as a safe fallback.

This test build keeps every v2 system intact and adds an observational scene
overlay.  The overlay does not spend actions or change relationships; the
existing Village Activity choices remain the only way to resolve a situation.

All persistent state is stored in ``world.world_flags`` and ``world.event_log``;
the existing save manager therefore saves and restores it without a schema
change.  The open overlay is deliberately transient and is not saved.
"""

import random

import pygame

from ui_pygame.screens.village_center import (
    BLUE,
    BRONZE,
    CREAM,
    GOLD,
    GREEN,
    HEIGHT,
    MUTED,
    PANEL,
    RED,
    TEXT,
    WIDTH,
    ClickTarget,
    VillageButton,
    VillageCenterScreen as LegacyVillageCenterScreen,
)


class VillageCenterScreen(LegacyVillageCenterScreen):
    """A social-story hub built on top of the original Village Center."""

    MAX_THREADS = 3
    MAX_ACTIVE_RUMOURS = 3

    def __init__(self, world, change_screen):
        self.gathering_plan = None
        self.selected_thread_id = None
        self.scene_view_thread_id = None
        super().__init__(world, change_screen)
        self.ensure_v2_state()
        threads = self.get_threads()
        unresolved = next((thread for thread in threads if not thread.get("resolved")), None)
        chosen = unresolved or (threads[0] if threads else None)
        self.selected_thread_id = chosen.get("id") if chosen else None

    # Persistent v2 state ------------------------------------------

    def current_moon(self):
        return int(getattr(self.world, "moon", 0) or 0)

    def stable_rng(self, key):
        return random.Random(f"village-v2:{self.current_moon()}:{key}")

    def dragon_is_injured(self, dragon):
        """Keep patients in the healer's den instead of treating them as visitors."""
        if bool(getattr(dragon, "injured", False)):
            return True
        injuries = getattr(dragon, "injuries", None)
        if isinstance(injuries, (list, tuple, set, dict)) and len(injuries) > 0:
            return True
        health = " ".join(
            str(getattr(dragon, attribute, ""))
            for attribute in ("health", "health_status", "condition")
        ).lower()
        return any(word in health for word in ("injured", "wounded", "critical"))

    def visitor_weight(self, dragon):
        """Weight social attendance without changing a dragon's real work location."""
        weight = 1.0
        personality = str(getattr(dragon, "personality", "")).lower()
        role = str(getattr(dragon, "role", "")).lower()

        if any(word in personality for word in ("kind", "loyal", "friendly", "social", "outgoing", "caring")):
            weight += 0.75
        if any(word in personality for word in ("solitary", "aloof", "shy", "suspicious", "withdrawn")):
            weight -= 0.42
        if role in {"dragonet", "elder", "caretaker"}:
            weight += 0.32
        if float(getattr(dragon, "grief_level", 0) or 0) > 0:
            weight += 0.28
        if self.relation_ids(dragon, "friends") or self.relation_ids(dragon, "rivals"):
            weight += 0.18
        return max(0.15, weight)

    def socially_relevant_ids(self):
        relevant = set()
        for rumour in self.world.world_flags.get("village_rumours", []) or []:
            if rumour.get("resolved"):
                continue
            for key in ("subject_id", "affected_id", "originator_id"):
                if rumour.get(key) is not None:
                    relevant.add(str(rumour.get(key)))
        for dragon in self.get_dragons():
            if float(getattr(dragon, "grief_level", 0) or 0) > 0:
                relevant.add(str(self.dragon_id(dragon)))
        return relevant

    def ensure_village_visitors(self):
        """Choose stable, moon-long visitors while preserving primary assignments."""
        if not hasattr(self.world, "world_flags") or self.world.world_flags is None:
            self.world.world_flags = {}
        flags = self.world.world_flags
        moon = self.current_moon()
        existing = flags.get("village_visitor_ids")
        if flags.get("village_visitors_moon") == moon and isinstance(existing, list):
            return

        living = self.get_dragons()
        primary = [
            dragon
            for dragon in living
            if getattr(dragon, "location", None) in self.VILLAGE_ALIASES
        ]
        target = min(len(living), max(2, min(6, round(len(living) * 0.32))))
        selected_ids = {str(self.dragon_id(dragon)) for dragon in primary}
        relevant_ids = self.socially_relevant_ids()

        candidates = []
        for dragon in living:
            dragon_key = str(self.dragon_id(dragon))
            if dragon_key in selected_ids:
                continue
            location = str(getattr(dragon, "location", "")).lower()
            if self.dragon_is_injured(dragon) and location in {"healer_den", "healer's den", "healers_den"}:
                continue
            weight = self.visitor_weight(dragon)
            if dragon_key in relevant_ids:
                weight += 1.1
            candidates.append((dragon, weight))

        # Weighted sampling without replacement, seeded by moon for save/load stability.
        rng = self.stable_rng("monthly-visitors")
        ranked = []
        for dragon, weight in candidates:
            key = rng.random() ** (1.0 / max(0.01, weight))
            ranked.append((key, dragon))
        ranked.sort(key=lambda item: item[0], reverse=True)
        for _, dragon in ranked:
            if len(selected_ids) >= target:
                break
            selected_ids.add(str(self.dragon_id(dragon)))

        # Retain the original ID type so relationship lookups remain natural.
        visitor_ids = [
            self.dragon_id(dragon)
            for dragon in living
            if str(self.dragon_id(dragon)) in selected_ids
            and getattr(dragon, "location", None) not in self.VILLAGE_ALIASES
        ]
        flags["village_visitors_moon"] = moon
        flags["village_visitor_ids"] = visitor_ids
        flags["village_attendance_target"] = target

    def get_dragons_at_village(self):
        """Return residents plus social visitors; never rewrite primary locations."""
        self.ensure_village_visitors()
        visitor_ids = {
            str(value)
            for value in self.world.world_flags.get("village_visitor_ids", []) or []
        }
        return [
            dragon
            for dragon in self.get_dragons()
            if getattr(dragon, "location", None) in self.VILLAGE_ALIASES
            or str(self.dragon_id(dragon)) in visitor_ids
        ]

    def ensure_v2_state(self):
        flags = self.world.world_flags
        flags.setdefault("village_rumours", [])
        flags.setdefault("village_rumour_counter", 0)

        self.ensure_village_visitors()

        moon = self.current_moon()
        if flags.get("village_rumour_processed_moon") != moon:
            self.advance_rumours()
            self.generate_rumour_if_needed()
            flags["village_rumour_processed_moon"] = moon

        if flags.get("village_v2_thread_moon") != moon:
            flags["village_v2_thread_moon"] = moon
            flags["village_v2_threads"] = self.build_threads()
        elif not isinstance(flags.get("village_v2_threads"), list):
            flags["village_v2_threads"] = self.build_threads()

    def get_threads(self):
        return self.world.world_flags.setdefault("village_v2_threads", [])

    def active_rumours(self):
        rumours = self.world.world_flags.setdefault("village_rumours", [])
        return [rumour for rumour in rumours if not rumour.get("resolved")]

    def find_rumour(self, rumour_id):
        return next(
            (
                rumour
                for rumour in self.world.world_flags.get("village_rumours", [])
                if str(rumour.get("id")) == str(rumour_id)
            ),
            None,
        )

    def rumour_status(self, rumour):
        if rumour.get("resolved"):
            return str(rumour.get("resolution", "settled")).upper()
        stage = int(rumour.get("stage", 1) or 1)
        if stage >= 3:
            return "WIDELY BELIEVED"
        if stage == 2:
            return "CIRCULATING"
        return "WHISPER"

    def create_rumour(
        self,
        claim,
        truth,
        subject_id,
        *,
        originator_id=None,
        affected_id=None,
        source_key=None,
        related_event="",
    ):
        flags = self.world.world_flags
        rumours = flags.setdefault("village_rumours", [])
        source_key = source_key or claim.lower().strip()
        if any(str(item.get("source_key")) == str(source_key) for item in rumours):
            return None

        flags["village_rumour_counter"] = int(flags.get("village_rumour_counter", 0) or 0) + 1
        rumour = {
            "id": f"rumour-{self.current_moon()}-{flags['village_rumour_counter']}",
            "claim": claim,
            "truth": truth,
            "subject_id": subject_id,
            "originator_id": originator_id,
            "affected_id": affected_id,
            "source_key": source_key,
            "related_event": related_event,
            "started_moon": self.current_moon(),
            "stage": 1,
            "evidence": 0,
            "resolved": False,
            "resolution": None,
        }
        rumours.append(rumour)
        flags["village_rumours"] = rumours[-18:]
        return rumour

    def advance_rumours(self):
        """Advance an existing whisper once per moon, never once per visit."""
        for rumour in self.active_rumours():
            if int(rumour.get("started_moon", self.current_moon())) >= self.current_moon():
                continue
            rng = self.stable_rng(rumour.get("id"))
            if rng.random() < 0.68:
                rumour["stage"] = min(3, int(rumour.get("stage", 1) or 1) + 1)
                self.adjust_public_opinion(rumour.get("subject_id"), -0.025 * rumour["stage"])

    def abandonment_candidates(self):
        candidates = []
        for affected in self.get_dragons():
            for flag in list(getattr(affected, "memory_flags", []) or []):
                if not isinstance(flag, (list, tuple)) or len(flag) < 2:
                    continue
                if str(flag[0]).lower() != "abandoned_by":
                    continue
                accused = self.get_dragon_by_id(flag[1])
                if not accused:
                    continue
                candidates.append((affected, accused))
        return candidates

    def recent_non_social_events(self):
        events = []
        for event in reversed(list(getattr(self.world, "event_log", []) or [])):
            if not isinstance(event, dict):
                continue
            event_type = str(event.get("type", "")).lower()
            tags = {str(tag).lower() for tag in event.get("tags", []) or []}
            if event_type in {"social", "rumour", "rumor"} or "social" in tags:
                continue
            moon = event.get("moon")
            if moon is not None and self.current_moon() - int(moon) > 2:
                continue
            events.append(event)
            if len(events) >= 10:
                break
        return events

    def jealousy_pair(self):
        best = None
        for originator in self.get_dragons():
            for target in self.get_dragons():
                if originator is target:
                    continue
                resentment = self.dict_value(originator, "resentment", self.dragon_id(target))
                if best is None or resentment > best[0]:
                    best = (resentment, originator, target)
        if best and best[0] >= 0.45:
            return best[1], best[2], best[0]
        return None

    def generate_rumour_if_needed(self):
        """Create at most one new data-backed rumour in a moon."""
        if len(self.active_rumours()) >= self.MAX_ACTIVE_RUMOURS:
            return

        # A remembered abandonment is the strongest possible seed.
        for affected, accused in self.abandonment_candidates():
            source_key = f"abandonment:{self.dragon_id(affected)}:{self.dragon_id(accused)}"
            claim = f"Some dragons say {accused.name} abandoned {affected.name} when the patrol turned dangerous."
            created = self.create_rumour(
                claim,
                "true",
                self.dragon_id(accused),
                affected_id=self.dragon_id(affected),
                source_key=source_key,
                related_event="An old abandonment remains unsettled.",
            )
            if created:
                return

        # Recent expedition outcomes create ambiguity without inventing a new event.
        for event in self.recent_non_social_events():
            text = " ".join(str(event.get("text", "")).split())
            lowered = text.lower()
            involved_ids = list(event.get("involved_ids", []) or [])
            involved = [self.get_dragon_by_id(value) for value in involved_ids]
            involved = [dragon for dragon in involved if dragon]
            if not involved:
                continue
            event_key = f"event:{event.get('moon')}:{text[:90]}"
            rng = self.stable_rng(event_key)

            if "injur" in lowered and len(involved) >= 2:
                subject, affected = involved[0], involved[-1]
                claim = (
                    f"A whisper claims {subject.name} ignored warning signs before "
                    f"{affected.name} was injured."
                )
                truth = rng.choice(["distorted", "unverifiable"])
            elif any(word in lowered for word in ("retreated", "failed", "forced away", "disorder")):
                subject, affected = involved[0], None
                claim = f"Some dragons say {subject.name} lost their nerve when the patrol needed resolve."
                truth = rng.choice(["distorted", "false", "unverifiable"])
            elif len(involved) >= 2 and any(word in lowered for word in ("success", "secured", "returned safely", "valuable")):
                subject, affected = involved[0], involved[1]
                claim = f"A few dragons insist {subject.name} took more credit than the patrol deserved."
                truth = rng.choice(["false", "distorted"])
            else:
                continue

            if rng.random() <= 0.62:
                created = self.create_rumour(
                    claim,
                    truth,
                    self.dragon_id(subject),
                    affected_id=self.dragon_id(affected) if affected else None,
                    source_key=event_key,
                    related_event=text[:180],
                )
                if created:
                    return

        # Jealousy can create a wholly false claim, but only where resentment exists.
        jealous = self.jealousy_pair()
        if jealous:
            originator, target, resentment = jealous
            source_key = f"jealousy:{self.current_moon()}:{self.dragon_id(originator)}:{self.dragon_id(target)}"
            rng = self.stable_rng(source_key)
            if resentment >= 1.0 or rng.random() < 0.48:
                self.create_rumour(
                    f"A jealous whisper suggests {target.name} has been claiming credit for another dragon's work.",
                    "false",
                    self.dragon_id(target),
                    originator_id=self.dragon_id(originator),
                    source_key=source_key,
                    related_event=f"Resentment toward {target.name} has been growing.",
                )

    # Contextual social threads ------------------------------------

    def make_thread(self, kind, first=None, second=None, *, rumour_id=None, suffix=""):
        first_id = self.dragon_id(first) if first else None
        second_id = self.dragon_id(second) if second else None
        identity = rumour_id or f"{first_id}:{second_id}:{suffix}"
        return {
            "id": f"{kind}:{self.current_moon()}:{identity}",
            "kind": kind,
            "a_id": first_id,
            "b_id": second_id,
            "rumour_id": rumour_id,
            "resolved": False,
            "result": "",
        }

    def build_threads(self):
        dragons = sorted(self.get_dragons_at_village(), key=lambda dragon: str(getattr(dragon, "name", "")))
        threads = []

        for rumour in sorted(self.active_rumours(), key=lambda item: -int(item.get("stage", 1) or 1)):
            threads.append(
                self.make_thread(
                    "rumour",
                    self.get_dragon_by_id(rumour.get("subject_id")),
                    self.get_dragon_by_id(rumour.get("affected_id")),
                    rumour_id=rumour.get("id"),
                )
            )
            if len(threads) >= self.MAX_THREADS:
                return threads

        if not dragons:
            threads.append(self.make_thread("empty", suffix="quiet"))
            return threads
        if len(dragons) == 1:
            threads.append(self.make_thread("solitude", dragons[0], suffix="alone"))
            return threads

        pair = self.find_pair_from_relation(dragons, "rivals", "resentment", 0.75)
        if pair and len(threads) < self.MAX_THREADS:
            threads.append(self.make_thread("tension", pair[0], pair[1], suffix="rivalry"))

        grieving = [dragon for dragon in dragons if float(getattr(dragon, "grief_level", 0) or 0) > 0]
        if grieving and len(threads) < self.MAX_THREADS:
            mourner = max(grieving, key=lambda dragon: float(getattr(dragon, "grief_level", 0) or 0))
            companion = self.best_companion(mourner, dragons)
            threads.append(self.make_thread("grief", mourner, companion, suffix="grief"))

        pair = self.find_pair_from_relation(dragons, "friends", "trust", 0.75)
        if pair and len(threads) < self.MAX_THREADS:
            existing_pairs = {
                frozenset((str(thread.get("a_id")), str(thread.get("b_id"))))
                for thread in threads
            }
            pair_key = frozenset((str(self.dragon_id(pair[0])), str(self.dragon_id(pair[1]))))
            if pair_key not in existing_pairs:
                threads.append(self.make_thread("bond", pair[0], pair[1], suffix="bond"))

        if len(threads) < self.MAX_THREADS:
            offset = self.current_moon() % len(dragons)
            first = dragons[offset]
            second = dragons[(offset + 1) % len(dragons)]
            existing_pairs = {
                frozenset((str(thread.get("a_id")), str(thread.get("b_id"))))
                for thread in threads
                if thread.get("a_id") is not None and thread.get("b_id") is not None
            }
            casual_key = frozenset((str(self.dragon_id(first)), str(self.dragon_id(second))))
            if casual_key not in existing_pairs:
                threads.append(self.make_thread("casual", first, second, suffix="crossing"))
        return threads[: self.MAX_THREADS]

    def best_companion(self, dragon, candidates):
        others = [candidate for candidate in candidates if candidate is not dragon]
        if not others:
            return None
        return max(
            others,
            key=lambda candidate: self.dict_value(dragon, "trust", self.dragon_id(candidate)),
        )

    def recent_context(self, *dragon_ids):
        wanted = {str(value) for value in dragon_ids if value is not None}
        if not wanted:
            return ""
        for event in reversed(list(getattr(self.world, "event_log", []) or [])):
            if not isinstance(event, dict):
                continue
            if str(event.get("type", "")).lower() in {"social", "rumour", "rumor"}:
                continue
            involved = {str(value) for value in event.get("involved_ids", []) or []}
            if wanted & involved:
                text = " ".join(str(event.get("text", "")).split())
                return text[:165] + ("…" if len(text) > 165 else "")
        return ""

    def personality_line(self, dragon, situation, fallback):
        personality = str(getattr(dragon, "personality", "")).strip().lower()
        lines = {
            "tension": {
                "kind": "I would rather settle this without causing another wound.",
                "loyal": "I will not allow this disagreement to harm the tribe.",
                "ambitious": "I will not stand aside while my judgment is questioned.",
                "suspicious": "You keep avoiding the part of the story that matters.",
                "moody": "I am tired of pretending this does not bother me.",
                "clever": "We are arguing about motives when the facts remain unsettled.",
            },
            "grief": {
                "kind": "I know others mean well. I simply cannot answer them yet.",
                "loyal": "I keep expecting to see them return to their usual place.",
                "ambitious": "There was still so much we intended to accomplish together.",
                "suspicious": "Everyone speaks as though they understand what happened.",
                "moody": "Some moments hurt more sharply than others.",
                "clever": "Understanding the loss has not made it easier to carry.",
            },
            "bond": {
                "kind": "You remembered what I needed before I had to ask.",
                "loyal": "Whatever happens next, you will not face it alone.",
                "ambitious": "Together, we could do more than either of us could manage alone.",
                "suspicious": "There are few dragons whose word I trust without question.",
                "moody": "You are one of the few dragons I do not need to perform for.",
                "clever": "We make a surprisingly effective pair.",
            },
            "casual": {
                "kind": "You look as though the moon has asked too much of you.",
                "loyal": "The village feels steadier when everyone returns safely.",
                "ambitious": "The tribe is changing. I intend to change with it.",
                "suspicious": "Have you noticed how many stories change between retellings?",
                "moody": "It is quieter here than it was yesterday.",
                "clever": "Small conversations often reveal more than formal councils.",
            },
        }
        for keyword, line in lines.get(situation, {}).items():
            if keyword in personality:
                return line
        return fallback

    def thread_content(self, thread):
        first = self.get_dragon_by_id(thread.get("a_id"))
        second = self.get_dragon_by_id(thread.get("b_id"))
        first_name = getattr(first, "name", "A quiet dragon")
        second_name = getattr(second, "name", "another dragon")
        kind = thread.get("kind")

        if kind == "rumour":
            rumour = self.find_rumour(thread.get("rumour_id")) or {}
            related = str(rumour.get("related_event", "")).strip()
            claim = str(rumour.get("claim", "An uncertain claim is spreading through the village."))
            lowered_claim = claim.lower()
            if "abandon" in lowered_claim:
                rumour_title = f"QUESTIONS ABOUT {first_name.upper()}'S PATROL"
            elif "credit" in lowered_claim:
                rumour_title = f"{first_name.upper()} AND DISPUTED CREDIT"
            elif "nerve" in lowered_claim or "courage" in lowered_claim:
                rumour_title = f"DOUBTS ABOUT {first_name.upper()}'S COURAGE"
            else:
                rumour_title = f"A CLAIM ABOUT {first_name.upper()}"
            attending_ids = {str(self.dragon_id(dragon)) for dragon in self.get_dragons_at_village()}
            subject_present = first and str(self.dragon_id(first)) in attending_ids
            response_line = (
                "If my name is being spoken, I deserve to know why."
                if subject_present
                else f"{first_name} is not here to answer the accusation."
            )
            return {
                "category": "RUMOUR",
                "color": (204, 146, 82),
                "title": rumour_title,
                "summary": claim,
                "context": related or "No dragon has yet offered convincing evidence.",
                "lines": [
                    ("Village whisper", "No one agrees on who first told the story."),
                    (first_name if subject_present else "Another voice", response_line),
                ],
                "options": (
                    ("SEEK WITNESSES", "investigate", "Spend an action to search for evidence."),
                    ("ADDRESS IT PUBLICLY", "public", "Act now, but risk strengthening the claim."),
                    ("LET IT CIRCULATE", "ignore", "Spend no action; the rumour may spread."),
                ),
                "status": self.rumour_status(rumour),
            }

        context = self.recent_context(thread.get("a_id"), thread.get("b_id"))
        if kind == "tension":
            return {
                "category": "RIVALRY",
                "color": RED,
                "title": "A DISAGREEMENT DRAWS EYES",
                "summary": f"{first_name} and {second_name} have carried an unresolved disagreement into the centre of village life.",
                "context": context or "The argument has been building through several smaller exchanges.",
                "lines": [
                    (first_name, self.personality_line(first, "tension", "We keep returning to the same disagreement.")),
                    (second_name, self.personality_line(second, "tension", "Because neither of us believes it was settled.")),
                ],
                "options": (
                    ("MEDIATE CALMLY", "mediate", "Reduce resentment, though the cause may remain."),
                    ("HEAR BOTH SIDES", "listen", "Clarify the dispute with a smaller social benefit."),
                    ("SEPARATE THEM", "separate", "Lower public tension without repairing the relationship."),
                ),
                "status": "UNRESOLVED",
            }
        if kind == "grief":
            return {
                "category": "GRIEF",
                "color": BLUE,
                "title": f"{first_name.upper()} SITS APART",
                "summary": f"{first_name} has withdrawn from the bustle. {second_name} notices, but is uncertain whether to approach.",
                "context": context or "The loss continues to shape ordinary moments in the village.",
                "lines": [
                    (second_name, "You do not have to carry all of this alone."),
                    (first_name, self.personality_line(first, "grief", "I know. I simply do not know what to say yet.")),
                ],
                "options": (
                    ("ENCOURAGE SUPPORT", "comfort", "Ease grief and possibly strengthen a bond."),
                    ("INVITE THEM TO THE FIRE", "include", "Reconnect them gently with village life."),
                    ("RESPECT THEIR SOLITUDE", "space", "Offer space without abandoning them."),
                ),
                "status": "PERSONAL",
            }
        if kind == "bond":
            return {
                "category": "BOND",
                "color": GREEN,
                "title": "FAMILIAR COMPANY",
                "summary": f"{first_name} and {second_name} have found an easy rhythm together amid the noise of the village.",
                "context": context or "Their trust has been built through repeated ordinary moments.",
                "lines": [
                    (first_name, self.personality_line(first, "bond", "It is good to have one conversation that does not feel like duty.")),
                    (second_name, self.personality_line(second, "bond", "Then we should make time for more of them.")),
                ],
                "options": (
                    ("ENCOURAGE THE BOND", "encourage", "Strengthen their existing trust."),
                    ("PAIR THEIR NEXT DUTY", "collaborate", "Build reliability as well as friendship."),
                    ("LEAVE THEM TO IT", "leave", "Allow a smaller, private improvement."),
                ),
                "status": "PROMISING",
            }
        if kind == "casual":
            return {
                "category": "ENCOUNTER",
                "color": GOLD,
                "title": "PATHS CROSS IN THE VILLAGE",
                "summary": f"{first_name} and {second_name} pause near the central fire as their duties bring them together.",
                "context": context or "No crisis brought them together; this is simply where village life overlaps.",
                "lines": [
                    (first_name, self.personality_line(first, "casual", "The village feels different every moon.")),
                    (second_name, self.personality_line(second, "casual", "Perhaps we are the ones who keep changing.")),
                ],
                "options": (
                    ("ENCOURAGE CONVERSATION", "introduce", "Create an opening for trust."),
                    ("ASK ABOUT THEIR HOPES", "hopes", "Encourage a more personal exchange."),
                    ("LET IT UNFOLD", "unfold", "A modest benefit without intervention."),
                ),
                "status": "OPEN",
            }
        if kind == "solitude":
            return {
                "category": "QUIET",
                "color": MUTED,
                "title": "A LONELY VILLAGE CENTRE",
                "summary": f"{first_name} is the only dragon lingering here while most of the tribe is occupied elsewhere.",
                "context": "There is no immediate social situation requiring attention.",
                "lines": [],
                "options": (),
                "status": "NO SCENE",
            }
        return {
            "category": "QUIET",
            "color": MUTED,
            "title": "THE CENTRE STANDS QUIET",
            "summary": "No dragons are currently gathered here. The communal fires burn low.",
            "context": "A gathering cannot be organized until dragons return.",
            "lines": [],
            "options": (),
            "status": "EMPTY",
        }

    # Expanded scene viewer ---------------------------------------

    def scene_view_thread(self):
        if self.scene_view_thread_id is None:
            return None
        return next(
            (
                thread
                for thread in self.get_threads()
                if str(thread.get("id")) == str(self.scene_view_thread_id)
            ),
            None,
        )

    def open_scene_view(self, thread_id):
        thread = next(
            (item for item in self.get_threads() if str(item.get("id")) == str(thread_id)),
            None,
        )
        if not thread or not self.thread_content(thread).get("lines"):
            self.notice = "There is no conversation to witness in this situation."
            self.notice_color = MUTED
            return
        self.scene_view_thread_id = thread.get("id")

    def close_scene_view(self):
        self.scene_view_thread_id = None

    def scene_followup_line(self, dragon, situation, fallback):
        """Give the preview a second personality-sensitive beat."""
        personality = str(getattr(dragon, "personality", "")).lower()
        lines = {
            "tension": {
                "kind": "I am willing to listen, but I will not accept blame merely to end this.",
                "loyal": "The tribe should not have to choose between us.",
                "ambitious": "I have worked too hard to let this become the story told about me.",
                "suspicious": "You are leaving something out, and we both know it.",
                "moody": "Every time I think this is finished, someone drags it back into the light.",
                "clever": "If we cannot agree on motives, perhaps we can at least agree on what happened.",
            },
            "grief": {
                "kind": "Staying is enough. You do not need to find the right words.",
                "loyal": "I promised I would remember them. I did not know remembering could hurt like this.",
                "ambitious": "Moving forward feels too much like leaving them behind.",
                "suspicious": "I do not want my grief turned into another village story.",
                "moody": "Some days I can breathe around it. Today is not one of them.",
                "clever": "There is no lesson hidden in this. There is only the absence.",
            },
            "bond": {
                "kind": "Then let us make certain neither of us has to ask twice.",
                "loyal": "You already know where I will stand when things become difficult.",
                "ambitious": "We could become the pair others rely upon when plans begin to fail.",
                "suspicious": "Trust is rare enough that I notice when it survives.",
                "moody": "Do not make me admit how much that matters.",
                "clever": "A reliable ally is worth more than a dozen agreeable acquaintances.",
            },
            "casual": {
                "kind": "Perhaps ordinary moments are how a tribe learns to feel like home.",
                "loyal": "Whatever changes, I hope we still recognize one another when the work is done.",
                "ambitious": "Change is only dangerous when someone else decides its direction.",
                "suspicious": "Nothing changes without a reason, even when no one admits what it is.",
                "moody": "I would settle for one moon that asks nothing unexpected of us.",
                "clever": "The smallest changes are usually the ones everyone notices last.",
            },
            "rumour": {
                "kind": "A dragon's name should not be damaged by a story no one can support.",
                "loyal": "If someone has an accusation, they should make it where the whole tribe can hear it.",
                "ambitious": "I will not let an anonymous whisper decide what my work was worth.",
                "suspicious": "The dragon who began this is hiding because the claim cannot survive scrutiny.",
                "moody": "They repeat it because the story is entertaining, not because it is true.",
                "clever": "Certainty grows remarkably quickly when no one is required to provide evidence.",
            },
        }
        for keyword, line in lines.get(situation, {}).items():
            if keyword in personality:
                return line
        return fallback

    def expanded_scene_lines(self, thread):
        """Return a deterministic 4–6 line scene without changing game state."""
        content = self.thread_content(thread)
        lines = list(content.get("lines", []) or [])
        first = self.get_dragon_by_id(thread.get("a_id"))
        second = self.get_dragon_by_id(thread.get("b_id"))
        first_name = getattr(first, "name", "The first dragon")
        second_name = getattr(second, "name", "The other dragon")
        kind = str(thread.get("kind", "casual"))

        if kind == "rumour":
            other_speaker = second_name if second else "A nearby dragon"
            lines.extend(
                [
                    (other_speaker, "What reached me sounded less certain than the version being repeated now."),
                    (
                        first_name,
                        self.scene_followup_line(
                            first,
                            "rumour",
                            "Then the village should decide whether it values evidence or a satisfying story.",
                        ),
                    ),
                    ("Village whisper", "By nightfall, even this exchange may become part of the rumour."),
                ]
            )
        elif kind == "tension":
            lines.extend(
                [
                    (first_name, "I remember what happened differently, and I am tired of yielding the account."),
                    (second_name, "Then speak plainly instead of asking everyone else to guess what you mean."),
                    (
                        first_name,
                        self.scene_followup_line(first, "tension", "I want this settled, but not by pretending it never mattered."),
                    ),
                ]
            )
        elif kind == "grief":
            lines.extend(
                [
                    (second_name, "I can remain here without asking anything from you."),
                    (
                        first_name,
                        self.scene_followup_line(first, "grief", "Then stay for a while. Silence may be easier with company."),
                    ),
                    (second_name, "I will stay as long as you need."),
                ]
            )
        elif kind == "bond":
            lines.extend(
                [
                    (second_name, "The next duty may not leave us much time for quiet conversation."),
                    (
                        first_name,
                        self.scene_followup_line(first, "bond", "Then we should remember this moment when the next one becomes difficult."),
                    ),
                    (second_name, "That sounds almost like a promise."),
                ]
            )
        else:
            lines.extend(
                [
                    (second_name, "Most changes seem ordinary until enough moons have passed to name them."),
                    (
                        first_name,
                        self.scene_followup_line(first, "casual", "Perhaps this is one of the ordinary moments we will remember later."),
                    ),
                    (second_name, "Then we should pay attention while it is still happening."),
                ]
            )
        return lines[:6]

    def active_thread(self):
        threads = self.get_threads()
        thread = next(
            (thread for thread in threads if str(thread.get("id")) == str(self.selected_thread_id)),
            None,
        )
        return thread or (threads[0] if threads else None)

    def select_thread(self, thread_id):
        self.selected_thread_id = thread_id
        self.notice = ""

    def cycle_thread(self, direction):
        threads = self.get_threads()
        if len(threads) <= 1:
            return
        current_index = next(
            (
                index
                for index, thread in enumerate(threads)
                if str(thread.get("id")) == str(self.selected_thread_id)
            ),
            0,
        )
        self.selected_thread_id = threads[(current_index + direction) % len(threads)].get("id")
        self.notice = ""

    # Consequences and rumours -------------------------------------

    def append_v2_event(self, text, involved=None, *, importance=2, tags=None, event_type="social"):
        involved_ids = [self.dragon_id(dragon) for dragon in (involved or []) if dragon]
        event_tags = ["social", "village"]
        for tag in tags or []:
            if tag not in event_tags:
                event_tags.append(tag)
        event = {
            "type": event_type,
            "text": text,
            "moon": self.current_moon(),
            "involved_ids": involved_ids,
            "importance": importance,
            "location": "village",
            "tags": event_tags,
        }
        self.world.event_log.append(event)
        self.world.event_log = self.world.event_log[-100:]
        social_log = self.world.world_flags.setdefault("village_social_log", [])
        social_log.append(event)
        self.world.world_flags["village_social_log"] = social_log[-18:]

    def mark_thread_resolved(self, thread, result, involved=None, *, consume=True, tags=None):
        if consume:
            self.consume_action()
        thread["resolved"] = True
        thread["result"] = result
        thread["resolved_moon"] = self.current_moon()
        self.append_v2_event(result, involved or [], importance=3, tags=tags)
        self.notice = "The outcome was recorded in Recent Social Changes."
        self.notice_color = GREEN

    def adjust_public_opinion(self, subject_id, amount):
        subject = self.get_dragon_by_id(subject_id)
        if not subject:
            return
        for dragon in self.get_dragons():
            if dragon is subject:
                continue
            self.change_dict_value(
                dragon,
                "perceived_reputation",
                subject_id,
                amount,
                minimum=-10.0,
                maximum=10.0,
            )

    def settle_rumour(self, rumour, resolution):
        rumour["resolved"] = True
        rumour["resolution"] = resolution
        rumour["resolved_moon"] = self.current_moon()

    def resolve_rumour(self, thread, choice):
        rumour = self.find_rumour(thread.get("rumour_id"))
        if not rumour:
            return
        subject = self.get_dragon_by_id(rumour.get("subject_id"))
        affected = self.get_dragon_by_id(rumour.get("affected_id"))
        originator = self.get_dragon_by_id(rumour.get("originator_id"))
        subject_name = getattr(subject, "name", "the accused dragon")
        truth = str(rumour.get("truth", "unverifiable"))

        if choice == "ignore":
            rumour["stage"] = min(3, int(rumour.get("stage", 1) or 1) + 1)
            self.adjust_public_opinion(rumour.get("subject_id"), -0.05 * rumour["stage"])
            result = (
                f"No one challenges the claim about {subject_name}. It spreads further, "
                "gaining certainty with each retelling."
            )
            self.mark_thread_resolved(
                thread,
                result,
                [subject, affected],
                consume=False,
                tags=["rumour", "unresolved"],
            )
            return

        rumour["evidence"] = int(rumour.get("evidence", 0) or 0) + (2 if choice == "investigate" else 1)
        rng = self.stable_rng(f"resolve:{rumour.get('id')}:{choice}")

        if choice == "investigate":
            if truth == "true":
                self.settle_rumour(rumour, "confirmed")
                self.adjust_public_opinion(rumour.get("subject_id"), -0.18)
                result = f"Witnesses confirm the heart of the accusation against {subject_name}. The whisper becomes accepted history."
            elif truth == "false":
                self.settle_rumour(rumour, "discredited")
                self.adjust_public_opinion(rumour.get("subject_id"), 0.12)
                if subject and originator:
                    self.change_dict_value(subject, "resentment", self.dragon_id(originator), 0.18, maximum=10.0)
                result = f"The accounts do not support the claim about {subject_name}. The rumour is publicly discredited."
            elif truth == "distorted":
                self.settle_rumour(rumour, "disputed")
                self.adjust_public_opinion(rumour.get("subject_id"), 0.03)
                result = f"Part of the story about {subject_name} is true, but important context was stripped away as it spread."
            else:
                rumour["stage"] = max(1, int(rumour.get("stage", 1) or 1) - 1)
                result = f"The witnesses disagree about {subject_name}. The claim remains unproven, but fewer dragons repeat it confidently."
        else:
            if truth == "true":
                self.settle_rumour(rumour, "confirmed")
                self.adjust_public_opinion(rumour.get("subject_id"), -0.24)
                result = f"The public defence of {subject_name} collapses when contradictory details emerge. Confidence in them falls sharply."
            elif truth == "false" and (rumour.get("evidence", 0) >= 2 or rng.random() < 0.55):
                self.settle_rumour(rumour, "discredited")
                self.adjust_public_opinion(rumour.get("subject_id"), 0.08)
                result = f"The village rejects the unsupported accusation against {subject_name}, and the whisper begins to die."
            elif truth == "distorted":
                self.settle_rumour(rumour, "disputed")
                result = f"The public discussion reveals that the claim about {subject_name} contains truth but hides crucial context."
            else:
                rumour["stage"] = min(3, int(rumour.get("stage", 1) or 1) + 1)
                self.adjust_public_opinion(rumour.get("subject_id"), -0.06)
                result = f"Without evidence, the public defence of {subject_name} only gives the rumour a larger audience."

        self.mark_thread_resolved(
            thread,
            result,
            [subject, affected, originator],
            consume=True,
            tags=["rumour", str(rumour.get("resolution") or "unresolved")],
        )

    def resolve_thread(self, thread_id, choice):
        thread = next((item for item in self.get_threads() if item.get("id") == thread_id), None)
        if not thread or thread.get("resolved"):
            return
        if choice != "ignore" and self.actions_remaining() <= 0:
            self.notice = "No community actions remain this moon."
            self.notice_color = RED
            return
        if thread.get("kind") == "rumour":
            self.resolve_rumour(thread, choice)
            return

        first = self.get_dragon_by_id(thread.get("a_id"))
        second = self.get_dragon_by_id(thread.get("b_id"))
        kind = thread.get("kind")
        if kind not in {"tension", "grief", "bond", "casual"}:
            return

        if choice == "mediate":
            self.soften_rivalry(first, second, 0.35)
            result = f"{first.name} and {second.name} leave with less hostility, though the original disagreement is not forgotten."
        elif choice == "listen":
            self.soften_rivalry(first, second, 0.15)
            result = f"{first.name} and {second.name} finally describe the dispute in their own words. The problem remains, but its shape is clearer."
        elif choice == "separate":
            self.world.tension = max(0.0, float(getattr(self.world, "tension", 0) or 0) - 0.35)
            result = f"{first.name} and {second.name} are separated before the argument spreads. Public tension falls, but their rivalry remains."
        elif choice == "comfort":
            first.grief_level = max(0, float(getattr(first, "grief_level", 0) or 0) - 2)
            self.strengthen_bond(first, second, 0.16)
            self.add_reputation(second, "kind", 0.08)
            result = f"{second.name} remains beside {first.name}. The loss remains, but it no longer feels entirely solitary."
        elif choice == "include":
            first.grief_level = max(0, float(getattr(first, "grief_level", 0) or 0) - 1)
            self.strengthen_bond(first, second, 0.10)
            result = f"{first.name} joins the communal fire and quietly returns to village life beside {second.name}."
        elif choice == "space":
            first.grief_level = max(0, float(getattr(first, "grief_level", 0) or 0) - 0.5)
            result = f"The tribe respects {first.name}'s need for quiet without mistaking solitude for abandonment."
        elif choice == "encourage":
            self.strengthen_bond(first, second, 0.14)
            result = f"{first.name} and {second.name} are reminded that their friendship matters beyond this single conversation."
        elif choice == "collaborate":
            self.strengthen_bond(first, second, 0.10)
            self.add_reputation(first, "reliable", 0.06)
            self.add_reputation(second, "reliable", 0.06)
            result = f"{first.name} and {second.name} agree to share their next suitable duty, turning affection into practical trust."
        elif choice == "leave":
            self.strengthen_bond(first, second, 0.04)
            result = f"The private conversation between {first.name} and {second.name} continues without interference."
        elif choice == "introduce":
            self.strengthen_bond(first, second, 0.12)
            result = f"A passing exchange becomes a genuine introduction between {first.name} and {second.name}."
        elif choice == "hopes":
            self.strengthen_bond(first, second, 0.09)
            result = f"{first.name} and {second.name} speak openly about what they want from the moons ahead."
        else:
            self.strengthen_bond(first, second, 0.05)
            result = f"The encounter between {first.name} and {second.name} is allowed to find its own shape."

        self.mark_thread_resolved(thread, result, [first, second], consume=True, tags=[kind])

    # Gathering planner --------------------------------------------

    def rival_pairs_here(self):
        dragons = self.get_dragons_at_village()
        pairs = []
        seen = set()
        for first in dragons:
            for second in dragons:
                if first is second:
                    continue
                key = tuple(sorted((str(self.dragon_id(first)), str(self.dragon_id(second)))))
                if key in seen:
                    continue
                rivalry = (
                    any(self.same_id(value, self.dragon_id(second)) for value in self.relation_ids(first, "rivals"))
                    or self.dict_value(first, "resentment", self.dragon_id(second)) >= 0.75
                    or self.dict_value(second, "resentment", self.dragon_id(first)) >= 0.75
                )
                if rivalry:
                    seen.add(key)
                    pairs.append((first, second))
        return pairs

    def gathering_definitions(self):
        dragons = self.get_dragons_at_village()
        food = int(getattr(self.world, "food_stores", 0) or 0)
        definitions = [
            {
                "kind": "meal",
                "title": "SHARED MEAL",
                "detail": "3+ dragons • 8 food",
                "enabled": len(dragons) >= 3 and food >= 8,
                "reason": "Requires three dragons here and eight food.",
            },
            {
                "kind": "stories",
                "title": "STORY CIRCLE",
                "detail": "Choose the storyteller",
                "enabled": len(dragons) >= 2,
                "reason": "Requires at least two dragons here.",
            },
            {
                "kind": "honour",
                "title": "HONOUR A CONTRIBUTION",
                "detail": "Choose the dragon",
                "enabled": len(dragons) >= 2,
                "reason": "Requires at least two dragons here.",
            },
        ]
        grieving = [dragon for dragon in dragons if float(getattr(dragon, "grief_level", 0) or 0) > 0]
        rival_pairs = self.rival_pairs_here()
        if grieving:
            definitions.append(
                {
                    "kind": "memorial",
                    "title": "MEMORIAL VIGIL",
                    "detail": "Support the grieving",
                    "enabled": len(dragons) >= 2,
                    "reason": "A grieving dragon and company are required.",
                }
            )
        elif rival_pairs:
            definitions.append(
                {
                    "kind": "mediation",
                    "title": "MEDIATION CIRCLE",
                    "detail": "Address an active rivalry",
                    "enabled": True,
                    "reason": "No active rivalry is present here.",
                }
            )
        return definitions

    def gathering_focuses(self, kind):
        dragons = self.get_dragons_at_village()
        if kind == "meal":
            return [
                {"value": "celebrate", "label": "Celebrate a recent success", "description": "Build pride and reinforce shared accomplishment."},
                {"value": "ease", "label": "Ease existing tensions", "description": "Reduce public tension and soften minor resentment."},
                {"value": "welcome", "label": "Renew the sense of belonging", "description": "Strengthen weaker ties among those attending."},
            ]
        if kind == "stories":
            ordered = sorted(
                dragons,
                key=lambda dragon: int(getattr(dragon, "age_moons", getattr(dragon, "age", 0)) or 0),
                reverse=True,
            )
            return [
                {
                    "value": self.dragon_id(dragon),
                    "label": f"{dragon.name} will tell the story",
                    "description": f"{getattr(dragon, 'personality', 'Their')} perspective will shape the telling.",
                }
                for dragon in ordered
            ]
        if kind == "honour":
            return [
                {
                    "value": self.dragon_id(dragon),
                    "label": f"Honour {dragon.name}",
                    "description": "Public recognition may inspire friends and provoke rivals.",
                }
                for dragon in dragons
            ]
        if kind == "memorial":
            return [
                {
                    "value": self.dragon_id(dragon),
                    "label": f"Hold the vigil for {dragon.name}",
                    "description": "The gathering will centre the dragon carrying the deepest grief.",
                }
                for dragon in dragons
                if float(getattr(dragon, "grief_level", 0) or 0) > 0
            ]
        if kind == "mediation":
            return [
                {
                    "value": [self.dragon_id(first), self.dragon_id(second)],
                    "label": f"Mediate {first.name} and {second.name}",
                    "description": "The village will hear both sides of their disagreement.",
                }
                for first, second in self.rival_pairs_here()
            ]
        return []

    def start_gathering(self, definition):
        if self.actions_remaining() <= 0:
            self.notice = "No community actions remain this moon."
            self.notice_color = RED
            return
        if not definition.get("enabled"):
            self.notice = definition.get("reason", "That gathering cannot be held yet.")
            self.notice_color = RED
            return
        focuses = self.gathering_focuses(definition.get("kind"))
        if not focuses:
            self.notice = "There is no suitable focus for that gathering."
            self.notice_color = RED
            return
        self.gathering_plan = {
            "kind": definition.get("kind"),
            "title": definition.get("title"),
            "focuses": focuses,
            "focus_index": 0,
        }
        self.notice = ""

    def cycle_gathering_focus(self, direction):
        if not self.gathering_plan:
            return
        focuses = self.gathering_plan.get("focuses", [])
        if not focuses:
            return
        self.gathering_plan["focus_index"] = (
            int(self.gathering_plan.get("focus_index", 0)) + direction
        ) % len(focuses)

    def maybe_seed_honour_rumour(self, honoured):
        rivals = []
        for dragon in self.get_dragons_at_village():
            if dragon is honoured:
                continue
            if (
                any(self.same_id(value, self.dragon_id(honoured)) for value in self.relation_ids(dragon, "rivals"))
                or self.dict_value(dragon, "resentment", self.dragon_id(honoured)) >= 0.75
            ):
                rivals.append(dragon)
        if not rivals:
            return None
        originator = max(
            rivals,
            key=lambda dragon: self.dict_value(dragon, "resentment", self.dragon_id(honoured)),
        )
        rng = self.stable_rng(f"honour-rumour:{self.dragon_id(honoured)}")
        if rng.random() >= 0.55:
            return None
        return self.create_rumour(
            f"A resentful whisper claims {honoured.name} was praised for work others actually carried.",
            "false",
            self.dragon_id(honoured),
            originator_id=self.dragon_id(originator),
            source_key=f"honour:{self.current_moon()}:{self.dragon_id(honoured)}",
            related_event=f"{honoured.name} was publicly honoured in the Village Center.",
        )

    def confirm_gathering(self):
        plan = self.gathering_plan
        if not plan or self.actions_remaining() <= 0:
            return
        focuses = plan.get("focuses", [])
        if not focuses:
            return
        focus = focuses[int(plan.get("focus_index", 0)) % len(focuses)]
        kind = plan.get("kind")
        dragons = self.get_dragons_at_village()
        involved = list(dragons)

        if kind == "meal":
            food = int(getattr(self.world, "food_stores", 0) or 0)
            if len(dragons) < 3 or food < 8:
                self.notice = "The meal can no longer be held with the available dragons and food."
                self.notice_color = RED
                self.gathering_plan = None
                return
            self.world.food_stores = food - 8
            purpose = focus.get("value")
            for index, first in enumerate(dragons):
                for second in dragons[index + 1 :]:
                    self.strengthen_bond(first, second, 0.035 if purpose != "welcome" else 0.055)
            if purpose == "ease":
                self.world.tension = max(0.0, float(getattr(self.world, "tension", 0) or 0) - 0.55)
                for first, second in self.rival_pairs_here():
                    self.soften_rivalry(first, second, 0.08)
                result = "The shared meal begins stiffly, but ordinary conversation takes the edge from several disagreements. (-8 food)"
            elif purpose == "celebrate":
                for dragon in dragons:
                    self.add_reputation(dragon, "community-minded", 0.025)
                result = "The village celebrates a successful moon together, turning individual accomplishments into shared pride. (-8 food)"
            else:
                result = "The shared meal gives quieter dragons a place within the circle and renews the village's sense of belonging. (-8 food)"
        elif kind == "stories":
            storyteller = self.get_dragon_by_id(focus.get("value"))
            involved = [storyteller] + [dragon for dragon in dragons if dragon is not storyteller]
            self.add_reputation(storyteller, "respected", 0.10)
            for dragon in dragons:
                if dragon is not storyteller:
                    self.change_dict_value(dragon, "trust", self.dragon_id(storyteller), 0.04, maximum=10.0)
            personality = str(getattr(storyteller, "personality", "")).lower()
            if any(word in personality for word in ("ambitious", "boastful", "proud")):
                result = f"{storyteller.name} holds the village's attention, although a few details grow grander with each telling."
            else:
                result = f"{storyteller.name} holds the village's attention with a story shaped by personal memory rather than official history."
        elif kind == "honour":
            honoured = self.get_dragon_by_id(focus.get("value"))
            involved = [honoured] + [dragon for dragon in dragons if dragon is not honoured]
            self.add_reputation(honoured, "respected", 0.14)
            for dragon in dragons:
                if dragon is not honoured:
                    self.change_dict_value(dragon, "trust", self.dragon_id(honoured), 0.025, maximum=10.0)
            seeded = self.maybe_seed_honour_rumour(honoured)
            if seeded:
                result = f"The village honours {honoured.name}'s contribution. Most applaud sincerely, but one dragon leaves with visible resentment."
            else:
                result = f"The village honours {honoured.name}'s contribution, connecting the praise to a deed the tribe remembers."
        elif kind == "memorial":
            mourner = self.get_dragon_by_id(focus.get("value"))
            involved = [mourner] + [dragon for dragon in dragons if dragon is not mourner]
            for dragon in dragons:
                if float(getattr(dragon, "grief_level", 0) or 0) > 0:
                    dragon.grief_level = max(0, float(getattr(dragon, "grief_level", 0) or 0) - 1.5)
            if mourner:
                mourner.grief_level = max(0, float(getattr(mourner, "grief_level", 0) or 0) - 1)
            result = f"The village gathers around {mourner.name}, speaking of the fallen without forcing grief into silence."
        else:
            pair_ids = focus.get("value", [])
            first = self.get_dragon_by_id(pair_ids[0]) if len(pair_ids) > 0 else None
            second = self.get_dragon_by_id(pair_ids[1]) if len(pair_ids) > 1 else None
            involved = [first, second]
            self.soften_rivalry(first, second, 0.38)
            self.world.tension = max(0.0, float(getattr(self.world, "tension", 0) or 0) - 0.2)
            result = f"{first.name} and {second.name} speak before the village. Agreement remains distant, but open hostility weakens."

        self.consume_action()
        self.append_v2_event(result, involved, importance=3, tags=["gathering", kind])
        self.notice = "The gathering was recorded in Recent Social Changes."
        self.notice_color = GREEN
        self.gathering_plan = None

    # Drawing -------------------------------------------------------

    def draw_social_pulse_v2(self, screen, rect):
        self.draw_panel(screen, rect, "SOCIAL PULSE")
        mood, description, mood_color = self.community_mood()
        bonds, rivalries, grieving = self.social_counts()
        village_dragons = self.get_dragons_at_village()

        pygame.draw.circle(screen, mood_color, (rect.x + 21, rect.y + 55), 5)
        self.draw_text(screen, mood, rect.x + 34, rect.y + 47, self.body_bold, mood_color)
        self.draw_wrapped(
            screen,
            description,
            pygame.Rect(rect.x + 15, rect.y + 70, rect.width - 30, 42),
            self.small,
            MUTED,
            14,
            3,
        )

        y = rect.y + 114
        metrics = (
            ("DRAGONS HERE", len(village_dragons), CREAM),
            ("KNOWN BONDS", bonds, GREEN),
            ("ACTIVE RIVALRIES", rivalries, RED),
            ("DRAGONS GRIEVING", grieving, BLUE),
            ("ACTIVE RUMOURS", len(self.active_rumours()), (204, 146, 82)),
        )
        for label, value, color in metrics:
            self.draw_text(screen, label, rect.x + 15, y, self.tiny, MUTED)
            self.draw_text(screen, value, rect.right - 16, y - 2, self.body_bold, color, right=True)
            y += 21

        pygame.draw.line(screen, (91, 65, 43), (rect.x + 15, y + 2), (rect.right - 15, y + 2), 1)
        self.draw_text(screen, "WHO IS HERE", rect.x + 15, y + 14, self.body_bold, GOLD)
        y += 38
        if not village_dragons:
            self.draw_text(screen, "The centre is currently empty.", rect.x + 15, y, self.small, MUTED)
            return
        for dragon in village_dragons[:5]:
            name = self.fit_text(getattr(dragon, "name", "Unknown"), self.body_bold, rect.width - 80)
            attendance = (
                "Resident"
                if getattr(dragon, "location", None) in self.VILLAGE_ALIASES
                else "Visiting"
            )
            role = self.fit_text(
                f"{getattr(dragon, 'role', 'Unknown')}  •  {attendance}",
                self.tiny,
                rect.width - 80,
            )
            pygame.draw.circle(screen, BRONZE, (rect.x + 22, y + 9), 10)
            self.draw_text(screen, str(getattr(dragon, "name", "?"))[:1].upper(), rect.x + 22, y + 9, self.tiny, CREAM, center=True)
            self.draw_text(screen, name, rect.x + 40, y - 1, self.body_bold, TEXT)
            self.draw_text(screen, role, rect.x + 40, y + 14, self.tiny, MUTED)
            y += 33
        if len(village_dragons) > 5:
            self.draw_text(screen, f"+{len(village_dragons) - 5} more gathered here", rect.x + 15, y, self.small, MUTED)

    def draw_thread_card(self, screen, rect, thread, selected, mouse_pos):
        content = self.thread_content(thread)
        hovered = rect.collidepoint(mouse_pos)
        fill = (57, 43, 33) if selected else ((45, 35, 29) if hovered else (33, 28, 24))
        edge = content["color"] if selected else (91, 65, 43)
        pygame.draw.rect(screen, fill, rect, border_radius=6)
        pygame.draw.rect(screen, edge, rect, 1 if not selected else 2, border_radius=6)
        if thread.get("resolved"):
            self.draw_text(screen, "✓", rect.x + 10, rect.y + 8, self.body_bold, GREEN)
            title_x = rect.x + 28
        else:
            pygame.draw.circle(screen, content["color"], (rect.x + 14, rect.centery), 4)
            title_x = rect.x + 25
        label = self.fit_text(content["title"], self.tiny, rect.width - 125)
        self.draw_text(screen, label, title_x, rect.y + 8, self.tiny, TEXT)
        self.draw_text(screen, content["category"], rect.right - 10, rect.y + 8, self.tiny, content["color"], right=True)
        self.buttons.append(ClickTarget(rect, lambda value=thread.get("id"): self.select_thread(value)))

    def draw_participants(self, screen, rect, first, second):
        participants = [dragon for dragon in (first, second) if dragon]
        if not participants:
            return
        spacing = 175 if len(participants) > 1 else 0
        start_x = rect.centerx - spacing // 2
        for index, dragon in enumerate(participants):
            x = start_x + index * spacing
            pygame.draw.circle(screen, (16, 12, 10), (x, rect.centery), 17)
            pygame.draw.circle(screen, BRONZE, (x, rect.centery), 16, 2)
            self.draw_text(screen, str(getattr(dragon, "name", "?"))[:1].upper(), x, rect.centery, self.body_bold, CREAM, center=True)
            name = self.fit_text(getattr(dragon, "name", "Unknown"), self.tiny, 116)
            name_x = x + 24 if index == 0 else x - 24
            self.draw_text(screen, name, name_x, rect.centery - 6, self.tiny, TEXT, right=index == 1)

    def draw_activity(self, screen, rect, mouse_pos):
        self.draw_panel(screen, rect, "VILLAGE ACTIVITY")
        threads = self.get_threads()
        thread = self.active_thread()
        if not thread:
            self.draw_text(screen, "No social situations are currently recorded.", rect.x + 16, rect.y + 55, self.small, MUTED)
            return

        current_index = next(
            (
                index
                for index, item in enumerate(threads)
                if str(item.get("id")) == str(thread.get("id"))
            ),
            0,
        )
        content = self.thread_content(thread)

        navigator = pygame.Rect(rect.x + 14, rect.y + 40, rect.width - 28, 34)
        pygame.draw.rect(screen, (22, 18, 15), navigator, border_radius=7)
        pygame.draw.rect(screen, (78, 55, 38), navigator, 1, border_radius=7)
        previous = VillageButton(
            (navigator.x + 5, navigator.y + 4, 58, 26),
            "PREV",
            lambda: self.cycle_thread(-1),
            enabled=len(threads) > 1,
        )
        following = VillageButton(
            (navigator.right - 63, navigator.y + 4, 58, 26),
            "NEXT",
            lambda: self.cycle_thread(1),
            enabled=len(threads) > 1,
        )
        self.buttons.extend((previous, following))
        previous.draw(screen, self.tiny, mouse_pos)
        following.draw(screen, self.tiny, mouse_pos)
        self.draw_text(
            screen,
            f"{content['category']}  •  {current_index + 1} OF {len(threads)}",
            navigator.centerx,
            navigator.centery,
            self.tiny,
            content["color"],
            center=True,
        )

        y = rect.y + 84
        title = self.fit_text(content["title"], self.body_bold, rect.width - 150)
        self.draw_text(screen, title, rect.x + 16, y, self.body_bold, CREAM)
        self.draw_text(screen, content["status"], rect.right - 16, y + 2, self.tiny, content["color"], right=True)

        first = self.get_dragon_by_id(thread.get("a_id"))
        second = self.get_dragon_by_id(thread.get("b_id"))
        self.draw_participants(screen, pygame.Rect(rect.x + 20, y + 20, rect.width - 40, 34), first, second)

        summary_y = y + 57
        self.draw_wrapped(
            screen,
            content["summary"],
            pygame.Rect(rect.x + 16, summary_y, rect.width - 32, 42),
            self.small,
            TEXT,
            14,
            3,
        )
        context_rect = pygame.Rect(rect.x + 14, summary_y + 43, rect.width - 28, 49)
        pygame.draw.rect(screen, (22, 18, 15), context_rect, border_radius=7)
        pygame.draw.rect(screen, (74, 52, 37), context_rect, 1, border_radius=7)
        self.draw_text(screen, "WHY THIS IS HAPPENING", context_rect.x + 10, context_rect.y + 7, self.tiny, GOLD)
        self.draw_wrapped(
            screen,
            content["context"],
            pygame.Rect(context_rect.x + 10, context_rect.y + 22, context_rect.width - 20, 24),
            self.tiny,
            MUTED,
            12,
            2,
        )

        dialogue_rect = pygame.Rect(rect.x + 14, context_rect.bottom + 6, rect.width - 28, 58)
        pygame.draw.rect(screen, (27, 22, 18), dialogue_rect, border_radius=7)
        pygame.draw.rect(screen, (74, 52, 37), dialogue_rect, 1, border_radius=7)
        lines = list(content.get("lines", []) or [])[:2]
        if lines:
            line_y = dialogue_rect.y + 7
            for speaker, line in lines:
                combined = self.fit_text(f"{speaker}:  {line}", self.tiny, dialogue_rect.width - 116)
                self.draw_text(screen, combined, dialogue_rect.x + 10, line_y, self.tiny, TEXT)
                line_y += 21
            view_button = VillageButton(
                (dialogue_rect.right - 98, dialogue_rect.y + 17, 90, 25),
                "VIEW SCENE",
                lambda thread_id=thread.get("id"): self.open_scene_view(thread_id),
                primary=True,
            )
            self.buttons.append(view_button)
            view_button.draw(screen, self.tiny, mouse_pos)
        else:
            self.draw_text(screen, "No conversation is unfolding here.", dialogue_rect.x + 10, dialogue_rect.y + 20, self.tiny, MUTED)

        action_y = dialogue_rect.bottom + 7
        if thread.get("resolved"):
            self.draw_text(screen, "OUTCOME", rect.x + 16, action_y, self.tiny, GREEN)
            self.draw_wrapped(
                screen,
                thread.get("result", "The matter has been addressed."),
                pygame.Rect(rect.x + 16, action_y + 16, rect.width - 32, 92),
                self.small,
                TEXT,
                14,
                6,
            )
            return
        if not content["options"]:
            self.draw_text(screen, "No immediate intervention is available.", rect.x + 16, action_y + 8, self.small, MUTED)
            return

        self.draw_text(screen, "CHOOSE AN APPROACH", rect.x + 16, action_y, self.tiny, GOLD)
        button_y = action_y + 17
        for label, choice, hint in content["options"]:
            enabled = self.actions_remaining() > 0 or choice == "ignore"
            button = VillageButton(
                (rect.x + 16, button_y, rect.width - 32, 23),
                label,
                lambda thread_id=thread.get("id"), value=choice: self.resolve_thread(thread_id, value),
                enabled=enabled,
                primary=choice in {"mediate", "comfort", "encourage", "introduce", "investigate"},
            )
            self.buttons.append(button)
            button.draw(screen, self.tiny, mouse_pos)
            self.draw_text(screen, self.fit_text(hint, self.tiny, rect.width - 42), rect.x + 21, button_y + 25, self.tiny, MUTED)
            button_y += 38

    def draw_scene_viewer(self, screen, mouse_pos):
        thread = self.scene_view_thread()
        if not thread:
            return

        # This full-screen target prevents clicks outside the modal from reaching
        # the Village Center controls underneath it.
        self.buttons.append(ClickTarget(pygame.Rect(0, 0, WIDTH, HEIGHT), lambda: None))

        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((3, 2, 2, 205))
        screen.blit(veil, (0, 0))

        rect = pygame.Rect(112, 70, 776, 552)
        self.draw_panel(screen, rect)
        content = self.thread_content(thread)
        accent = content.get("color", GOLD)
        first = self.get_dragon_by_id(thread.get("a_id"))
        second = self.get_dragon_by_id(thread.get("b_id"))

        self.draw_text(screen, "WITNESS A SOCIAL SCENE", rect.centerx, rect.y + 27, self.heading, CREAM, center=True)
        self.draw_text(
            screen,
            f"{content.get('category', 'SCENE')}  •  VILLAGE CENTER  •  MOON {self.current_moon()}",
            rect.centerx,
            rect.y + 50,
            self.tiny,
            accent,
            center=True,
        )
        pygame.draw.line(screen, BRONZE, (rect.x + 28, rect.y + 64), (rect.right - 28, rect.y + 64), 1)

        def participant_card(card_rect, dragon, fallback_name):
            pygame.draw.rect(screen, (24, 19, 16), card_rect, border_radius=9)
            pygame.draw.rect(screen, (92, 66, 45), card_rect, 1, border_radius=9)
            name = getattr(dragon, "name", fallback_name)
            role = str(getattr(dragon, "role", "Unknown role")).replace("_", " ").title()
            personality = str(getattr(dragon, "personality", "")).strip().title()
            pygame.draw.circle(screen, (15, 12, 10), (card_rect.x + 37, card_rect.centery), 25)
            pygame.draw.circle(screen, accent, (card_rect.x + 37, card_rect.centery), 24, 2)
            self.draw_text(screen, str(name)[:1].upper(), card_rect.x + 37, card_rect.centery, self.heading, CREAM, center=True)
            self.draw_text(screen, self.fit_text(str(name), self.body_bold, card_rect.width - 88), card_rect.x + 74, card_rect.y + 18, self.body_bold, TEXT)
            details = role + (f"  •  {personality}" if personality else "")
            self.draw_text(screen, self.fit_text(details, self.tiny, card_rect.width - 88), card_rect.x + 74, card_rect.y + 42, self.tiny, MUTED)

        participant_card(pygame.Rect(rect.x + 28, rect.y + 76, 337, 68), first, "A village dragon")
        participant_card(pygame.Rect(rect.right - 365, rect.y + 76, 337, 68), second, "Another voice")

        context_rect = pygame.Rect(rect.x + 28, rect.y + 155, rect.width - 56, 72)
        pygame.draw.rect(screen, (22, 18, 15), context_rect, border_radius=8)
        pygame.draw.rect(screen, (74, 52, 37), context_rect, 1, border_radius=8)
        self.draw_text(screen, self.fit_text(content.get("title", "A VILLAGE ENCOUNTER"), self.body_bold, context_rect.width - 24), context_rect.x + 12, context_rect.y + 10, self.body_bold, CREAM)
        self.draw_wrapped(
            screen,
            content.get("context", "Two dragons find a moment to speak."),
            pygame.Rect(context_rect.x + 12, context_rect.y + 34, context_rect.width - 24, 30),
            self.tiny,
            MUTED,
            12,
            2,
        )

        dialogue_rect = pygame.Rect(rect.x + 28, context_rect.bottom + 10, rect.width - 56, 254)
        pygame.draw.rect(screen, (18, 15, 13), dialogue_rect, border_radius=9)
        pygame.draw.rect(screen, (67, 49, 35), dialogue_rect, 1, border_radius=9)
        self.draw_text(screen, "THE EXCHANGE", dialogue_rect.x + 12, dialogue_rect.y + 9, self.tiny, accent)

        lines = self.expanded_scene_lines(thread)
        second_name = str(getattr(second, "name", ""))
        line_y = dialogue_rect.y + 29
        for index, (speaker, line) in enumerate(lines[:6]):
            from_second = second_name and str(speaker) == second_name
            bubble_width = dialogue_rect.width - 82
            bubble_x = dialogue_rect.right - bubble_width - 14 if from_second else dialogue_rect.x + 14
            bubble = pygame.Rect(bubble_x, line_y, bubble_width, 32)
            bubble_fill = (37, 31, 27) if from_second else (44, 33, 27)
            pygame.draw.rect(screen, bubble_fill, bubble, border_radius=6)
            pygame.draw.rect(screen, (84, 61, 43), bubble, 1, border_radius=6)
            self.draw_text(screen, self.fit_text(f"{speaker}:", self.tiny, 104), bubble.x + 8, bubble.y + 7, self.tiny, accent)
            self.draw_text(screen, self.fit_text(str(line), self.tiny, bubble.width - 122), bubble.x + 112, bubble.y + 7, self.tiny, TEXT)
            line_y += 35

        self.draw_text(
            screen,
            "OBSERVATION ONLY  •  Return to Village Activity to choose a response.",
            rect.centerx,
            rect.bottom - 57,
            self.tiny,
            MUTED,
            center=True,
        )
        close = VillageButton(
            (rect.centerx - 105, rect.bottom - 43, 210, 32),
            "RETURN TO VILLAGE CENTER",
            self.close_scene_view,
            primary=True,
        )
        self.buttons.append(close)
        close.draw(screen, self.tiny, mouse_pos)

    def gathering_color(self, kind):
        return {
            "meal": (196, 132, 65),
            "stories": (116, 153, 190),
            "honour": GOLD,
            "memorial": (146, 126, 181),
            "mediation": (177, 107, 82),
        }.get(kind, GOLD)

    def draw_gathering_icon(self, screen, center, kind, enabled=True, large=False):
        radius = 43 if large else 18
        color = self.gathering_color(kind) if enabled else (91, 84, 76)
        pygame.draw.circle(screen, (18, 14, 12), center, radius)
        pygame.draw.circle(screen, color, center, radius, 2)
        cx, cy = center
        scale = 2 if large else 1

        if kind == "meal":
            bowl = pygame.Rect(cx - 11 * scale, cy - 2 * scale, 22 * scale, 12 * scale)
            pygame.draw.arc(screen, color, bowl, 0, 3.15, max(1, 2 * scale))
            pygame.draw.line(screen, color, (cx - 10 * scale, cy), (cx + 10 * scale, cy), max(1, 2 * scale))
            for offset in (-6, 0, 6):
                pygame.draw.line(screen, color, (cx + offset * scale, cy - 5 * scale), (cx + (offset - 1) * scale, cy - 10 * scale), max(1, scale))
        elif kind == "stories":
            book = pygame.Rect(cx - 11 * scale, cy - 8 * scale, 22 * scale, 16 * scale)
            pygame.draw.rect(screen, color, book, max(1, scale), border_radius=2 * scale)
            pygame.draw.line(screen, color, (cx, cy - 8 * scale), (cx, cy + 8 * scale), max(1, scale))
            pygame.draw.line(screen, color, (cx - 8 * scale, cy - 3 * scale), (cx - 3 * scale, cy - 3 * scale), max(1, scale))
            pygame.draw.line(screen, color, (cx + 3 * scale, cy - 3 * scale), (cx + 8 * scale, cy - 3 * scale), max(1, scale))
        elif kind == "honour":
            points = [
                (cx, cy - 12 * scale),
                (cx + 4 * scale, cy - 4 * scale),
                (cx + 12 * scale, cy),
                (cx + 4 * scale, cy + 4 * scale),
                (cx, cy + 12 * scale),
                (cx - 4 * scale, cy + 4 * scale),
                (cx - 12 * scale, cy),
                (cx - 4 * scale, cy - 4 * scale),
            ]
            pygame.draw.polygon(screen, color, points, max(1, scale))
            pygame.draw.circle(screen, color, center, 3 * scale)
        elif kind == "memorial":
            pygame.draw.rect(screen, color, (cx - 4 * scale, cy - 2 * scale, 8 * scale, 12 * scale), max(1, scale))
            flame = [(cx, cy - 13 * scale), (cx + 5 * scale, cy - 5 * scale), (cx, cy - 1 * scale), (cx - 4 * scale, cy - 5 * scale)]
            pygame.draw.polygon(screen, color, flame, max(1, scale))
        else:
            pygame.draw.line(screen, color, (cx, cy - 10 * scale), (cx, cy + 10 * scale), max(1, 2 * scale))
            pygame.draw.line(screen, color, (cx - 11 * scale, cy - 6 * scale), (cx + 11 * scale, cy - 6 * scale), max(1, 2 * scale))
            pygame.draw.line(screen, color, (cx - 8 * scale, cy - 6 * scale), (cx - 11 * scale, cy + 3 * scale), max(1, scale))
            pygame.draw.line(screen, color, (cx + 8 * scale, cy - 6 * scale), (cx + 11 * scale, cy + 3 * scale), max(1, scale))
            pygame.draw.arc(screen, color, pygame.Rect(cx - 16 * scale, cy, 10 * scale, 7 * scale), 0, 3.15, max(1, scale))
            pygame.draw.arc(screen, color, pygame.Rect(cx + 6 * scale, cy, 10 * scale, 7 * scale), 0, 3.15, max(1, scale))

    def gathering_effects(self, kind, focus):
        if kind == "meal":
            purpose = focus.get("value")
            if purpose == "ease":
                return (("TENSION", "DOWN", GREEN), ("RESENTMENT", "MAY EASE", GREEN), ("FOOD", "-8", RED))
            if purpose == "celebrate":
                return (("SHARED PRIDE", "UP", GREEN), ("TRUST", "UP", GREEN), ("FOOD", "-8", RED))
            return (("BELONGING", "UP", GREEN), ("WEAK BONDS", "STRENGTHEN", GREEN), ("FOOD", "-8", RED))
        if kind == "stories":
            return (("STORYTELLER", "RESPECT UP", GREEN), ("LISTENER TRUST", "UP", GREEN), ("DETAILS", "MAY SHIFT", GOLD))
        if kind == "honour":
            return (("REPUTATION", "UP", GREEN), ("PUBLIC TRUST", "UP", GREEN), ("JEALOUSY", "POSSIBLE", GOLD))
        if kind == "memorial":
            return (("GRIEF", "DOWN", GREEN), ("SUPPORT", "UP", GREEN), ("MEMORY", "RECORDED", BLUE))
        return (("RESENTMENT", "DOWN", GREEN), ("TENSION", "DOWN", GREEN), ("AGREEMENT", "NOT GUARANTEED", GOLD))

    def draw_attendee_medallions(self, screen, rect, dragons):
        visible = list(dragons)[:7]
        if not visible:
            self.draw_text(screen, "No dragons are available to attend.", rect.x, rect.y + 12, self.tiny, MUTED)
            return
        spacing = min(58, max(38, rect.width // max(1, len(visible))))
        total_width = spacing * (len(visible) - 1)
        start_x = rect.centerx - total_width // 2
        for index, dragon in enumerate(visible):
            x = start_x + index * spacing
            pygame.draw.circle(screen, (17, 13, 11), (x, rect.y + 18), 15)
            pygame.draw.circle(screen, BRONZE, (x, rect.y + 18), 14, 2)
            self.draw_text(screen, str(getattr(dragon, "name", "?"))[:1].upper(), x, rect.y + 18, self.tiny, CREAM, center=True)
            name = self.fit_text(getattr(dragon, "name", "Unknown"), self.tiny, spacing + 8)
            self.draw_text(screen, name, x, rect.y + 39, self.tiny, MUTED, center=True)
        if len(dragons) > len(visible):
            self.draw_text(screen, f"+{len(dragons) - len(visible)}", rect.right - 4, rect.y + 11, self.tiny, GOLD, right=True)

    def draw_gatherings_v2(self, screen, rect, mouse_pos):
        self.draw_panel(screen, rect, "GATHERINGS")
        self.draw_wrapped(
            screen,
            "Choose an event, its purpose, and who will shape it.",
            pygame.Rect(rect.x + 14, rect.y + 43, rect.width - 28, 35),
            self.small,
            MUTED,
            13,
            2,
        )
        y = rect.y + 80
        for definition in self.gathering_definitions()[:4]:
            card = pygame.Rect(rect.x + 13, y, rect.width - 26, 51)
            enabled = bool(definition.get("enabled")) and self.actions_remaining() > 0
            hovered = enabled and card.collidepoint(mouse_pos)
            fill = (53, 40, 31) if hovered else ((34, 29, 25) if enabled else (31, 29, 27))
            accent = self.gathering_color(definition["kind"])
            edge = accent if hovered else ((105, 76, 53) if enabled else (67, 61, 55))
            pygame.draw.rect(screen, fill, card, border_radius=7)
            pygame.draw.rect(screen, edge, card, 1, border_radius=7)
            self.draw_gathering_icon(screen, (card.x + 26, card.centery), definition["kind"], enabled=enabled)
            color = TEXT if enabled else (111, 103, 94)
            card_title = {
                "honour": "HONOUR A DRAGON",
            }.get(definition["kind"], definition["title"])
            self.draw_text(screen, self.fit_text(card_title, self.tiny, card.width - 66), card.x + 51, card.y + 7, self.tiny, color)
            locked_details = {
                "meal": "NEEDS 3 DRAGONS • 8 FOOD",
                "stories": "NEEDS 2 DRAGONS",
                "honour": "NEEDS 2 DRAGONS",
                "memorial": "NEEDS COMPANY",
                "mediation": "NEEDS AN ACTIVE RIVALRY",
            }
            detail = definition["detail"] if definition.get("enabled") else locked_details.get(definition["kind"], "UNAVAILABLE")
            self.draw_text(screen, self.fit_text(detail, self.tiny, card.width - 66), card.x + 51, card.y + 26, self.tiny, MUTED)
            self.buttons.append(
                ClickTarget(
                    card,
                    lambda value=definition: self.start_gathering(value),
                    enabled=self.actions_remaining() > 0,
                )
            )
            y += 55

        pygame.draw.line(screen, (91, 65, 43), (rect.x + 14, y + 1), (rect.right - 14, y + 1), 1)
        self.draw_text(screen, "RECENT SOCIAL CHANGES", rect.x + 14, y + 12, self.body_bold, GOLD)
        y += 38
        events = self.recent_social_events(limit=2)
        if not events:
            self.draw_text(screen, "No recent social events recorded.", rect.x + 14, y, self.tiny, MUTED)
        for event in events:
            moon = event.get("moon")
            prefix = f"MOON {moon}  •  " if moon is not None else "•  "
            y = self.draw_wrapped(
                screen,
                prefix + str(event.get("text", "")),
                pygame.Rect(rect.x + 14, y, rect.width - 28, 58),
                self.tiny,
                TEXT,
                12,
                4,
            ) + 6

    def draw_gathering_modal(self, screen, mouse_pos):
        if not self.gathering_plan:
            return
        self.buttons.append(ClickTarget(pygame.Rect(0, 0, WIDTH, HEIGHT), lambda: None))
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((3, 2, 2, 188))
        screen.blit(veil, (0, 0))
        rect = pygame.Rect(170, 112, 660, 468)
        self.draw_panel(screen, rect)
        kind = self.gathering_plan.get("kind", "meal")
        title = self.gathering_plan.get("title", "GATHERING")
        self.draw_text(screen, "PLAN A COMMUNITY GATHERING", rect.centerx, rect.y + 29, self.heading, CREAM, center=True)
        self.draw_text(screen, "Choose the focus before committing this moon's action.", rect.centerx, rect.y + 52, self.tiny, MUTED, center=True)

        focuses = self.gathering_plan.get("focuses", [])
        focus = focuses[int(self.gathering_plan.get("focus_index", 0)) % len(focuses)]

        identity_rect = pygame.Rect(rect.x + 27, rect.y + 76, 170, 245)
        pygame.draw.rect(screen, (24, 19, 16), identity_rect, border_radius=10)
        pygame.draw.rect(screen, self.gathering_color(kind), identity_rect, 1, border_radius=10)
        self.draw_gathering_icon(screen, (identity_rect.centerx, identity_rect.y + 66), kind, enabled=True, large=True)
        self.draw_text(screen, title, identity_rect.centerx, identity_rect.y + 128, self.body_bold, GOLD, center=True)
        gathering_descriptions = {
            "meal": "A shared table can celebrate success, rebuild belonging, or soften tension.",
            "stories": "One dragon's memories become part of the tribe's shared understanding.",
            "honour": "Public recognition strengthens reputation but can expose hidden jealousy.",
            "memorial": "The tribe makes room for grief without asking anyone to carry it alone.",
            "mediation": "Rivals speak before the community without being promised agreement.",
        }
        self.draw_wrapped(
            screen,
            gathering_descriptions.get(kind, "The community gathers around a shared purpose."),
            pygame.Rect(identity_rect.x + 14, identity_rect.y + 151, identity_rect.width - 28, 66),
            self.tiny,
            MUTED,
            13,
            5,
        )
        requirement = "USES 1 COMMUNITY ACTION"
        if kind == "meal":
            requirement += "  •  8 FOOD"
        self.draw_text(screen, requirement, identity_rect.centerx, identity_rect.bottom - 18, self.tiny, self.gathering_color(kind), center=True)

        self.draw_text(screen, "PURPOSE OR FOCUS", rect.x + 220, rect.y + 79, self.tiny, MUTED)
        focus_rect = pygame.Rect(rect.x + 220, rect.y + 97, rect.width - 247, 100)
        pygame.draw.rect(screen, (22, 18, 15), focus_rect, border_radius=8)
        pygame.draw.rect(screen, BRONZE, focus_rect, 1, border_radius=8)
        self.draw_text(screen, self.fit_text(focus.get("label", ""), self.body_bold, focus_rect.width - 30), focus_rect.centerx, focus_rect.y + 27, self.body_bold, TEXT, center=True)
        self.draw_wrapped(
            screen,
            focus.get("description", ""),
            pygame.Rect(focus_rect.x + 18, focus_rect.y + 51, focus_rect.width - 36, 38),
            self.tiny,
            MUTED,
            13,
            3,
        )

        if len(focuses) > 1:
            previous = VillageButton((rect.x + 220, rect.y + 207, 92, 29), "PREVIOUS", lambda: self.cycle_gathering_focus(-1))
            following = VillageButton((rect.right - 119, rect.y + 207, 92, 29), "NEXT", lambda: self.cycle_gathering_focus(1))
            self.buttons.extend((previous, following))
            previous.draw(screen, self.tiny, mouse_pos)
            following.draw(screen, self.tiny, mouse_pos)
            self.draw_text(screen, f"{int(self.gathering_plan.get('focus_index', 0)) + 1} / {len(focuses)}", rect.x + 420, rect.y + 221, self.tiny, MUTED, center=True)

        effects_rect = pygame.Rect(rect.x + 220, rect.y + 247, rect.width - 247, 74)
        pygame.draw.rect(screen, (24, 19, 16), effects_rect, border_radius=8)
        pygame.draw.rect(screen, (74, 52, 37), effects_rect, 1, border_radius=8)
        self.draw_text(screen, "EXPECTED EFFECTS", effects_rect.x + 12, effects_rect.y + 9, self.tiny, GOLD)
        effects = self.gathering_effects(kind, focus)
        badge_width = (effects_rect.width - 32) // 3
        for index, (label, value, color) in enumerate(effects):
            badge = pygame.Rect(effects_rect.x + 10 + index * (badge_width + 6), effects_rect.y + 28, badge_width, 35)
            pygame.draw.rect(screen, (34, 28, 24), badge, border_radius=6)
            pygame.draw.rect(screen, color, badge, 1, border_radius=6)
            self.draw_text(screen, self.fit_text(label, self.tiny, badge.width - 8), badge.centerx, badge.y + 10, self.tiny, MUTED, center=True)
            self.draw_text(screen, self.fit_text(value, self.tiny, badge.width - 8), badge.centerx, badge.y + 24, self.tiny, color, center=True)

        dragons = self.get_dragons_at_village()
        self.draw_text(screen, f"ATTENDING  •  {len(dragons)}", rect.x + 29, rect.y + 338, self.tiny, GOLD)
        self.draw_attendee_medallions(
            screen,
            pygame.Rect(rect.x + 28, rect.y + 352, rect.width - 56, 56),
            dragons,
        )

        cancel = VillageButton((rect.x + 95, rect.bottom - 49, 170, 34), "CANCEL", lambda: setattr(self, "gathering_plan", None))
        confirm = VillageButton((rect.right - 265, rect.bottom - 49, 170, 34), "HOLD GATHERING", self.confirm_gathering, primary=True)
        self.buttons.extend((cancel, confirm))
        cancel.draw(screen, self.small, mouse_pos)
        confirm.draw(screen, self.small, mouse_pos)

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
        self.draw_social_pulse_v2(screen, pygame.Rect(38, 122, 245, 466))
        self.draw_activity(screen, pygame.Rect(298, 122, 414, 466), mouse_pos)
        self.draw_gatherings_v2(screen, pygame.Rect(727, 122, 235, 466), mouse_pos)
        self.draw_notice(screen)

        return_button = VillageButton(
            (420, 646, 160, 38),
            "RETURN TO MAP",
            lambda: self.change_screen("locations"),
        )
        self.buttons.append(return_button)
        return_button.draw(screen, self.small, mouse_pos)

        self.draw_gathering_modal(screen, mouse_pos)
        self.draw_scene_viewer(screen, mouse_pos)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.scene_view_thread_id is not None:
                self.close_scene_view()
            elif self.gathering_plan:
                self.gathering_plan = None
            else:
                self.change_screen("locations")
            return

        # A modal owns the click.  Stop after the first matching control so a
        # click cannot also trigger a covered button on the base screen.
        if self.scene_view_thread_id is not None or self.gathering_plan:
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                for button in reversed(self.buttons):
                    if button.enabled and button.rect.collidepoint(event.pos):
                        button.handle_event(event)
                        return
            return
        for button in reversed(self.buttons):
            button.handle_event(event)
