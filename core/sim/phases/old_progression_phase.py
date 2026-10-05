import random
from core.sim.memory import Memory, add_memory, choose_memory_to_reflect
from core.sim.relationships import strengthen_relationship, weaken_relationship
from core.sim.death import handle_possible_death
from core.sim.progression import tick_dragon_progression
from core.generator import generate_dragonet
from core.sim.logging import log_event


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def egg_condition_label(score):
    if score >= 80:
        return "Healthy"
    if score >= 60:
        return "Stable"
    if score >= 40:
        return "Concerning"
    return "Critical"


def ensure_egg_hatchery_state(world, egg):
    """Add the newer Hatchery fields to both new eggs and older saves."""
    if not hasattr(world, "world_flags") or world.world_flags is None:
        world.world_flags = {}

    if "egg_id" not in egg:
        existing_ids = [
            existing.get("egg_id", 0)
            for existing in getattr(world, "eggs", [])
            if isinstance(existing, dict)
        ]
        next_id = max(
            int(world.world_flags.get("next_egg_id", 1)),
            max(existing_ids, default=0) + 1,
        )
        egg["egg_id"] = next_id
        world.world_flags["next_egg_id"] = next_id + 1

    starting_condition = {
        "healthy": 86,
        "stable": 72,
        "good": 78,
        "concerning": 48,
        "fragile": 42,
        "critical": 28,
        "unknown": 68,
    }.get(str(egg.get("condition", "stable")).lower(), 70)

    egg.setdefault("condition_score", starting_condition)
    egg.setdefault("last_inspected_moon", -1)
    egg.setdefault("last_tended_moon", -1)
    egg.setdefault("last_healer_check_moon", -1)
    egg.setdefault("reinforced_until_moon", -1)
    egg.setdefault("incident_cooldown_until", -1)
    egg.setdefault("pending_incident", False)
    egg.setdefault("care_actions_received", 0)
    egg["condition_score"] = int(clamp(egg["condition_score"], 0, 100))
    egg["condition"] = egg_condition_label(egg["condition_score"])
    return egg


def get_egg_parents(world, egg):
    parent_names = {egg.get("mother"), egg.get("father")}
    return [
        dragon
        for dragon in getattr(world, "dragons", [])
        if getattr(dragon, "name", None) in parent_names
    ]


def get_caretaker_suitability(world, caretaker, egg):
    """Return a 0-100 care score using role, health, bonds, and workload."""
    if caretaker is None or getattr(caretaker, "status", "") != "Alive":
        return 25

    score = 50
    role = str(getattr(caretaker, "role", "")).lower()
    score += {
        "healer": 23,
        "elder": 18,
        "hunter": 7,
        "scout": 5,
        "warrior": 3,
        "deputy": 6,
        "leader": 6,
        "queen": 8,
        "dragonet": -35,
    }.get(role, 0)

    health = str(getattr(caretaker, "health", "Healthy")).lower()
    if health != "healthy":
        score -= 22

    mood = str(getattr(caretaker, "mood", "")).lower()
    if any(word in mood for word in ("angry", "stressed", "strained", "grieving")):
        score -= 10
    elif any(word in mood for word in ("calm", "content", "hopeful")):
        score += 5

    personality = str(getattr(caretaker, "personality", "")).lower()
    if any(word in personality for word in ("patient", "gentle", "loyal", "protective", "caring")):
        score += 10
    if any(word in personality for word in ("aggressive", "impulsive", "selfish", "cruel", "reckless")):
        score -= 12

    parents = get_egg_parents(world, egg)
    if caretaker in parents:
        score += 15

    trust = getattr(caretaker, "trust", {})
    if isinstance(trust, dict) and parents:
        parent_trust = sum(float(trust.get(parent.id, 0)) for parent in parents) / len(parents)
        score += int(clamp(parent_trust * 3, -10, 10))

    workload = sum(
        1
        for other_egg in getattr(world, "eggs", [])
        if other_egg.get("caretaker") == getattr(caretaker, "name", None)
    )
    score -= max(0, workload - 1) * 13
    return int(clamp(score, 10, 95))


def egg_involved_ids(world, egg, caretaker=None):
    dragons = get_egg_parents(world, egg)
    if caretaker is not None and caretaker not in dragons:
        dragons.append(caretaker)
    return [dragon.id for dragon in dragons if getattr(dragon, "id", None) is not None]


def create_hatchery_incident(world, egg, incident_type):
    if getattr(world, "pending_choice", None) is not None:
        return False

    caretaker = next(
        (
            dragon
            for dragon in getattr(world, "dragons", [])
            if getattr(dragon, "name", None) == egg.get("caretaker")
            and getattr(dragon, "status", "") == "Alive"
        ),
        None,
    )
    parent_names = f"{egg.get('mother', 'Unknown')} and {egg.get('father', 'Unknown')}"

    if incident_type == "difficult_hatching":
        text = (
            f"The egg of {parent_names} has begun to crack, but the hatchling appears "
            "to be struggling. The hatchery needs a decision."
        )
        options = [
            {"id": "assist_hatching", "text": "Carefully assist the hatchling"},
            {"id": "call_healer", "text": "Call a healer to supervise"},
            {"id": "wait_naturally", "text": "Allow the hatching to continue naturally"},
        ]
    else:
        text = (
            f"The egg of {parent_names} has become unusually quiet and its condition "
            "is worsening. How should the tribe respond?"
        )
        options = [
            {"id": "call_healer", "text": "Ask a healer to examine the egg"},
            {"id": "warm_nest", "text": "Move it to a warmer, protected nest"},
            {"id": "wait_naturally", "text": "Avoid interfering for now"},
        ]

    egg["pending_incident"] = True
    egg["incident_cooldown_until"] = getattr(world, "moon", 0) + 2
    world.pending_choice = {
        "type": "hatchery_incident",
        "location": "hatchery",
        "incident": incident_type,
        "egg_id": egg.get("egg_id"),
        "text": text,
        "involved_ids": egg_involved_ids(world, egg, caretaker),
        "options": options,
    }
    log_event(
        world,
        f"The egg of {parent_names} requires attention in the hatchery.",
        involved_ids=egg_involved_ids(world, egg, caretaker),
        event_type="hatchery",
        importance=4,
    )
    return True


def run_progression_phase(world, living):

    for dragon in living:

        tick_dragon_progression(world, dragon, living)

        handle_possible_death(world, dragon)

        if (
            dragon.status == "Alive"
            and dragon.legend_flags.get("pending_survival_check") == 1
        ):
            dragon.hardship_survived += 1
            dragon.legend_flags["pending_survival_check"] = 0

    # Hunting fatigue is deliberately stored in world_flags so old saves load
    # without a Dragon dataclass migration. Every living dragon recovers one
    # fatigue point when a new moon begins.
    if not hasattr(world, "world_flags") or world.world_flags is None:
        world.world_flags = {}
    fatigue_moon = getattr(world, "moon", 0)
    if world.world_flags.get("last_fatigue_recovery_moon") != fatigue_moon:
        fatigue = world.world_flags.get("dragon_fatigue", {})
        if not isinstance(fatigue, dict):
            fatigue = {}
        recovered = {}
        for dragon_id, amount in fatigue.items():
            remaining = max(0, int(amount) - 1)
            if remaining > 0:
                recovered[str(dragon_id)] = remaining
        world.world_flags["dragon_fatigue"] = recovered
        world.world_flags["last_fatigue_recovery_moon"] = fatigue_moon

    # ------------------------
    # Weekly Food Consumption
    # ------------------------

    current_food_moon = getattr(world, "moon", 0)
    last_food_moon = world.world_flags.get("last_food_consumption_moon")

    if last_food_moon != current_food_moon:
        current_living = [
            dragon for dragon in getattr(world, "dragons", [])
            if getattr(dragon, "status", "") == "Alive"
        ]

        food_required = len(current_living)
        available_food = max(0, getattr(world, "food_stores", 100))
        food_consumed = min(available_food, food_required)
        food_shortage = food_required - food_consumed

        world.food_stores = available_food - food_consumed

        if food_shortage > 0:
            world.tension += min(0.25, food_shortage * 0.01)

            food_message = (
                f"The tribe consumed {food_consumed} food but needed "
                f"{food_required}. A shortage of {food_shortage} "
                f"increased tension."
            )
            food_importance = 4
        else:
            food_message = (
                f"The tribe consumed {food_consumed} food. "
                f"{world.food_stores} remains in storage."
            )
            food_importance = 1

        log_event(
            world,
            food_message,
            involved_ids=[],
            event_type="resource",
            importance=food_importance,
        )

        world.world_flags["last_food_consumption_moon"] = current_food_moon

    # ------------------------
    # Egg Progression
    # ------------------------

    if not hasattr(world, "eggs"):
        world.eggs = []

    hatched_eggs = []
    current_moon = getattr(world, "moon", 0)

    for egg in world.eggs:
        ensure_egg_hatchery_state(world, egg)
        egg["age"] += 1

        caretaker = next(
            (
                dragon
                for dragon in world.dragons
                if dragon.name == egg.get("caretaker")
                and dragon.status == "Alive"
            ),
            None,
        )
        suitability = get_caretaker_suitability(world, caretaker, egg)
        egg["caretaker_suitability"] = suitability

        care_change = int(round((suitability - 50) / 15))
        if caretaker is None:
            care_change -= 2
        if egg.get("reinforced_until_moon", -1) >= current_moon:
            care_change += 2
        care_change += random.randint(-4, 4)

        egg["condition_score"] = int(
            clamp(egg.get("condition_score", 70) + care_change, 0, 100)
        )
        egg["condition"] = egg_condition_label(egg["condition_score"])

        try:
            progress = egg["age"] / max(1, egg["hatch_time"])
        except (TypeError, ValueError, ZeroDivisionError):
            progress = 0

        if egg["condition_score"] < 40:
            egg["movement"] = "is unnervingly still"
        elif progress >= 0.8:
            egg["movement"] = "moves strongly within the shell"
        elif progress >= 0.45:
            egg["movement"] = "shifts from time to time"
        else:
            egg.setdefault("movement", "rests quietly")

        if egg["age"] >= egg["hatch_time"]:
            if egg["condition_score"] < 55:
                if egg.get("incident_cooldown_until", -1) <= current_moon:
                    create_hatchery_incident(world, egg, "difficult_hatching")
                continue
            hatched_eggs.append(egg)
        elif (
            egg["condition_score"] < 60
            and not egg.get("pending_incident")
            and egg.get("incident_cooldown_until", -1) <= current_moon
        ):
            incident_chance = 0.42 if egg["condition_score"] < 40 else 0.22
            if random.random() < incident_chance:
                create_hatchery_incident(world, egg, "fragile_egg")

    for egg in hatched_eggs:
        world.eggs.remove(egg)

        existing_ids = [d.id for d in world.dragons]
        new_id = max(existing_ids) + 1 if existing_ids else 1

        parents = [
            d for d in world.dragons
            if d.name in {egg.get("mother"), egg.get("father")}
        ]

        caretaker = next(
            (
                d for d in world.dragons
                if d.name == egg.get("caretaker")
                and d.status == "Alive"
            ),
            None
        )

        if parents:
            tribe = random.choice(parents).tribe
        else:
            tribe = random.choice(world.dragons).tribe

        dragonet = generate_dragonet(new_id, tribe, parents)
        dragonet.parents = [p.id for p in parents]
        dragonet.location = "hatchery"

        if caretaker:
            suitability = get_caretaker_suitability(world, caretaker, egg)
            trust_bonus = 1.5 + suitability / 50.0
            dragonet.trust[caretaker.id] = trust_bonus
            caretaker.trust[dragonet.id] = 0.8 + suitability / 100.0

            dragonet.caretaker_id = caretaker.id
            dragonet.caretaker_role = caretaker.role

            add_memory(
                dragonet,
                Memory(
                    type="raised_by_caretaker",
                    moon=current_moon,
                    other_id=caretaker.id,
                    importance=4,
                    tags=["hatchery", "family", "caretaker"],
                ),
            )
            add_memory(
                caretaker,
                Memory(
                    type="guarded_egg_until_hatching",
                    moon=current_moon,
                    other_id=dragonet.id,
                    importance=4,
                    tags=["hatchery", "caretaker", "dragonet"],
                ),
            )

            if caretaker.role == "Healer":
                dragonet.health = "Healthy"
                dragonet.reputation["reliable"] += 0.2

            elif caretaker.role == "Elder":
                dragonet.reputation["reliable"] += 0.3

            elif caretaker.role == "Warrior":
                dragonet.combat_skill += 1

            elif caretaker.role == "Scout":
                dragonet.watchful_actions += 1

            elif caretaker.role == "Hunter":
                dragonet.hardship_survived += 1

        if egg.get("condition_score", 70) < 45:
            dragonet.health = "Weak"
            dragonet.injury_duration = max(1, getattr(dragonet, "injury_duration", 0))

        world.dragons.append(dragonet)

        dragonet.age = 0
        dragonet.life_stage = "Dragonet"

        for parent in parents:
            parent.dragonets.append(dragonet.id)

        parent_names = " and ".join([p.name for p in parents]) if parents else "unknown parents"

        caretaker_text = (
            f" {caretaker.name}'s care left an early mark on them."
            if caretaker
            else ""
        )

        reveal = {
            "name": dragonet.name,
            "tribe": getattr(dragonet, "tribe", tribe),
            "parents": [parent.name for parent in parents],
            "caretaker": caretaker.name if caretaker else None,
            "health": getattr(dragonet, "health", "Healthy"),
            "condition": egg.get("condition", "Stable"),
            "moon": current_moon,
        }
        reveals = world.world_flags.setdefault("hatching_reveals", [])
        reveals.append(reveal)
        world.world_flags["hatching_reveals"] = reveals[-5:]

        log_event(
            world,
            f"The egg of {parent_names} hatched. The dragonet {dragonet.name} was born.{caretaker_text}",
            involved_ids=[dragonet.id] + [p.id for p in parents] + ([caretaker.id] if caretaker else []),
            event_type="hatchery",
            importance=5,
        )

    if random.random() < 0.15:
        resolve_memory_reflection(world, living)

def resolve_memory_reflection(world, living):
    import random
    
    if not living:
        return

    candidates = [
        dragon for dragon in living
        if getattr(dragon, "status", "Alive") == "Alive"
        and getattr(dragon, "memories", [])
    ]

    if not candidates:
        return

    dragon = random.choice(candidates)
    memories = getattr(dragon, "memories", [])

    if not memories:
        return

    memory = choose_memory_to_reflect(
        dragon,
        moon=getattr(world, "moon", 0)
    )

    if memory is None:
        return

    event_count_before = len(getattr(world, "event_log", []))

    memory_type = getattr(memory, "type", None)
    other_id = getattr(memory, "other_id", None)

    if memory_type == "mentored_by":
        mentor_id = other_id
        mentor = next((d for d in living if d.id == mentor_id), None)

        if mentor:
            dragon.trust[mentor.id] = dragon.trust.get(mentor.id, 0) + 0.2

            log_event(
                world,
                f"{dragon.name} sought advice from {mentor.name}, remembering their time as a student.",
                involved_ids=[dragon.id, mentor.id],
                event_type="social",
                importance=2,
            )

            strengthen_relationship(
                dragon,
                mentor.id,
                0.1,
                world,
                "student",
                memory
            )

            strengthen_relationship(
                mentor,
                dragon.id,
                0.05,
                world,
                "mentor",
                memory
            )

            memory.reflection_weight *= 0.95

    elif memory_type == "mentored":
        student_id = other_id
        student = next(
            (d for d in living if d.id == student_id),
            None
        )

        if student:
            dragon.reputation["kind"] = (
                dragon.reputation.get("kind", 0) + 0.05
            )

            student.trust[dragon.id] = (
                student.trust.get(dragon.id, 0) + 0.1
            )

            strengthen_relationship(
                dragon,
                student.id,
                0.08,
                world,
                "mentor",
                memory
            )

            strengthen_relationship(
                student,
                dragon.id,
                0.04,
                world,
                "student",
                memory
            )

            log_event(
                world,
                (
                    f"{dragon.name} checked in on {student.name}, "
                    "remembering the responsibility they once took "
                    "on as a mentor."
                ),
                involved_ids=[dragon.id, student.id],
                event_type="social",
                importance=2,
            )

            memory.reflection_weight *= 0.95

    elif memory_type == "trained_well_with":
        partner_id = other_id
        partner = next(
            (d for d in living if d.id == partner_id),
            None
        )

        if partner:
            dragon.trust[partner.id] = (
                dragon.trust.get(partner.id, 0) + 0.1
            )

            partner.trust[dragon.id] = (
                partner.trust.get(dragon.id, 0) + 0.05
            )

            strengthen_relationship(
                dragon,
                partner.id,
                0.07,
                world,
                "bond",
                memory
            )

            strengthen_relationship(
                partner,
                dragon.id,
                0.04,
                world,
                "bond",
                memory
            )

            log_event(
                world,
                (
                    f"{dragon.name} sought out {partner.name} for "
                    "another training session, remembering how well "
                    "they worked together."
                ),
                involved_ids=[dragon.id, partner.id],
                event_type="social",
                importance=2,
            )

            memory.reflection_weight *= 0.96

    elif memory_type == "was_embarrassed_by":
        rival_id = other_id
        rival = next((d for d in living if d.id == rival_id), None)

        if rival:
            dragon.resentment[rival.id] = dragon.resentment.get(rival.id, 0) + 0.2

            log_event(
                world,
                f"{dragon.name} still remembers being humiliated by {rival.name} during training.",
                involved_ids=[dragon.id, rival.id],
                event_type="social",
                importance=3,
            )

            strengthen_relationship(dragon, rival.id, 0.1, world, "rivalry", memory)
            weaken_relationship(dragon, rival.id, 0.05, world, "bond", memory)
            memory.reflection_weight *= 0.97

    elif memory_type == "won_team_drill":
        dragon.reputation["reliable"] = dragon.reputation.get("reliable", 0) + 0.1

        events = [
            f"The tribe still remembers {dragon.name}'s strong performance in past team drills.",
            f"{dragon.name}'s confidence has grown since their success in team drills.",
            f"Younger dragons watched {dragon.name} with renewed respect after hearing about their training victory.",
        ]

        log_event(
            world,
            random.choice(events),
            involved_ids=[dragon.id],
            event_type="social",
            importance=2,
        )
    
    elif memory_type == "lost_team_drill":
        dragon.reputation["reliable"] = dragon.reputation.get("reliable", 0) - 0.05

        events = [
            f"{dragon.name} still thinks about a poor showing during past team drills.",
            f"{dragon.name} trained quietly, determined not to repeat an old failure.",
            f"The memory of losing a team drill pushed {dragon.name} to work harder.",
        ]

        log_event(
            world,
            random.choice(events),
            involved_ids=[dragon.id],
            event_type="social",
            importance=2,
        )

    elif memory_type == "hunted_with":
        partner_id = other_id
        partner = next((d for d in living if d.id == partner_id), None)

        if partner:
            dragon.trust[partner.id] = dragon.trust.get(partner.id, 0) + 0.10

            strengthen_relationship(
                dragon,
                partner.id,
                0.08,
                world,
                "bond",
                memory
            )

            log_event(
                world,
                f"{dragon.name} remembered a successful hunt with {partner.name}, and the old sense of teamwork returned.",
                involved_ids=[dragon.id, partner.id],
                event_type="social",
                importance=2,
            )

            memory.reflection_weight *= 0.96

    elif memory_type == "survived_dangerous_hunt_with":
        partner_id = other_id
        partner = next((d for d in living if d.id == partner_id), None)

        if partner:
            dragon.trust[partner.id] = dragon.trust.get(partner.id, 0) + 0.25

            strengthen_relationship(
                dragon,
                partner.id,
                0.20,
                world,
                "bond",
                memory
            )

            log_event(
                world,
                f"{dragon.name} remembered surviving a dangerous hunt beside {partner.name}. The shared danger still binds them.",
                involved_ids=[dragon.id, partner.id],
                event_type="social",
                importance=3,
            )

            memory.reflection_weight *= 0.93

    elif memory_type == "witnessed_hunting_failure":
        hunter_id = other_id
        hunter = next((d for d in living if d.id == hunter_id), None)

        if hunter:
            dragon.trust[hunter.id] = dragon.trust.get(hunter.id, 0) - 0.05

            log_event(
                world,
                f"{dragon.name} remembered watching {hunter.name} struggle badly during a hunt.",
                involved_ids=[dragon.id, hunter.id],
                event_type="social",
                importance=2,
            )

            memory.reflection_weight *= 0.97

    elif memory_type == "challenged":
        rival_id = other_id
        rival = next((d for d in living if d.id == rival_id), None)

        if rival:
            dragon.resentment[rival.id] = dragon.resentment.get(rival.id, 0) + 0.1

            events = [
                f"{dragon.name} remembered challenging {rival.name} during training and felt the old tension return.",
                f"{dragon.name} watched {rival.name} carefully, still measuring themselves against them.",
                f"The rivalry between {dragon.name} and {rival.name} sharpened after memories of old training clashes resurfaced.",
            ]

            log_event(
                world,
                random.choice(events),
                involved_ids=[dragon.id, rival.id],
                event_type="social",
                importance=3,
            )

    elif memory_type == "was_challenged_by":
        rival_id = other_id
        rival = next((d for d in living if d.id == rival_id), None)

        if rival:
            dragon.resentment[rival.id] = dragon.resentment.get(rival.id, 0) + 0.1

            log_event(
                world,
                f"{dragon.name} has not forgotten being challenged by {rival.name} during training.",
                involved_ids=[dragon.id, rival.id],
                event_type="social",
                importance=3,
            )

    elif memory_type and memory_type.startswith("border_"):
        border_reflections = {
            "border_scout_success": [
                f"{dragon.name} remembered a successful border scouting mission and remained alert for hidden routes.",
                f"{dragon.name} drew confidence from an earlier scouting success.",
            ],
            "border_scout_failure": [
                f"{dragon.name} reflected on a failed border scouting mission, determined to be more careful next time.",
                f"{dragon.name} remained uneasy about mistakes made during an earlier scouting mission.",
            ],
            "border_patrol_success": [
                f"{dragon.name} remembered keeping the border secure during a successful patrol.",
                f"{dragon.name}'s confidence grew while recalling a patrol that ended well.",
            ],
            "border_patrol_failure": [
                f"{dragon.name} still worried about a border patrol that went badly.",
                f"{dragon.name} trained harder after remembering an unsuccessful patrol.",
            ],
            "border_expedition_success": [
                f"{dragon.name} recalled returning safely from a dangerous border expedition.",
                f"The memory of a successful expedition strengthened {dragon.name}'s resolve.",
            ],
            "border_expedition_failure": [
                f"{dragon.name} remained troubled by a border expedition that ended in failure.",
                f"{dragon.name} remembered the dangers of a failed expedition and became more cautious.",
            ],
        }

        events = border_reflections.get(memory_type, [])

        if events:
            log_event(
                world,
                random.choice(events),
                involved_ids=[dragon.id],
                event_type="border",
                importance=2,
            )

            memory.reflection_weight *= 0.95

    if len(getattr(world, "event_log", [])) > event_count_before:
        memory.last_reflected_moon = getattr(world, "moon", 0)
