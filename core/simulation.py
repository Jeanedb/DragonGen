import random
from core.world import World
from core.generator import generate_dragonet
from core.sim.logging import log_event
from core.sim.relationships import add_friendship, add_rivalry
from core.sim.choices import resolve_choice
from core.sim.progression import tick_dragon_progression
from core.sim.events import run_event_phase
from core.sim.titles import evaluate_world_titles
from core.sim.politics import (
    run_politics_phase,
    drift_relations,
    clamp_relations,
    get_most_hostile_relation,
    get_random_foreign_tribe,
)
from core.sim.leadership import (
    maintain_hierarchy,
    apply_leader_influence,
    get_leader_by_id,
)

def are_family(a, b):
    if a.id in b.parents or b.id in a.parents:
        return True
    if set(a.parents) & set(b.parents):
        return True
    return False

def get_living_dragons(world: World):
    return [d for d in world.dragons if d.status == "Alive"]

def get_eligible_non_dragonets(world: World):
    return [
        d for d in world.dragons
        if d.status == "Alive" and d.role != "Dragonet"
    ]

def get_world_mood(world):
    tension = getattr(world, "tension", 0.0)

    if tension < 0.75:
        return "Calm"
    elif tension < 1.5:
        return "Uneasy"
    elif tension < 2.5:
        return "Strained"
    elif tension < 3.5:
        return "Volatile"
    else:
        return "Crisis"

def get_tribe_climate(world):
    """
    Short-term tribe atmosphere for this moon.

    Mood = current emotional weather
    Leader = long-term cultural pressure

    Returns a dict of soft biases that other systems can use to
    weight events, tone, and choices.
    """
    mood = get_world_mood(world)
    leader = get_leader_by_id(world)

    climate = {
        "bonding_bias": 0.0,
        "conflict_bias": 0.0,
        "mercy_bias": 0.0,
        "risk_bias": 0.0,
        "suspicion_bias": 0.0,
        "recovery_bias": 0.0,
        "tone_tags": []
    }

    # ---- Mood effects: short-term emotional weather ----
    if mood == "Calm":
        climate["bonding_bias"] += 0.20
        climate["recovery_bias"] += 0.15
        climate["tone_tags"].append("settled")

    elif mood == "Uneasy":
        climate["suspicion_bias"] += 0.10
        climate["tone_tags"].append("watchful")

    elif mood == "Strained":
        climate["conflict_bias"] += 0.15
        climate["suspicion_bias"] += 0.15
        climate["tone_tags"].append("strained")

    elif mood == "Volatile":
        climate["conflict_bias"] += 0.30
        climate["risk_bias"] += 0.20
        climate["tone_tags"].append("volatile")

    elif mood == "Crisis":
        climate["conflict_bias"] += 0.45
        climate["risk_bias"] += 0.30
        climate["mercy_bias"] -= 0.15
        climate["tone_tags"].append("crisis")

    direction = getattr(world, "direction", None)

    if direction == "stabilizing":
        climate["bonding_bias"] += 0.20
        climate["recovery_bias"] += 0.25

    elif direction == "pressuring":
        climate["conflict_bias"] += 0.25
        climate["risk_bias"] += 0.20

    elif direction == "watchful":
        climate["suspicion_bias"] += 0.30

    # ---- Leader effects: long-term cultural pressure ----
    if leader:
        traits = getattr(leader, "personality_traits", []) or []

        if "Kind" in traits:
            climate["bonding_bias"] += 0.20
            climate["mercy_bias"] += 0.25
            climate["recovery_bias"] += 0.20
            climate["tone_tags"].append("gentle_leadership")

        if "Loyal" in traits:
            climate["bonding_bias"] += 0.15
            climate["recovery_bias"] += 0.10
            climate["tone_tags"].append("steady_leadership")

        if "Clever" in traits:
            climate["risk_bias"] -= 0.10
            climate["tone_tags"].append("measured_leadership")

        if "Ambitious" in traits:
            climate["conflict_bias"] += 0.20
            climate["risk_bias"] += 0.15
            climate["tone_tags"].append("pressured_leadership")

        if "Moody" in traits:
            climate["conflict_bias"] += 0.15
            climate["recovery_bias"] -= 0.15
            climate["tone_tags"].append("unstable_leadership")

        if "Suspicious" in traits:
            climate["suspicion_bias"] += 0.30
            climate["bonding_bias"] -= 0.10
            climate["tone_tags"].append("paranoid_leadership")

    return climate

def add_friend_event(world, a, b):
    direction = getattr(world, "direction", None)
    mood = get_world_mood(world)
    climate = get_tribe_climate(world)

    used_memory = False  # <-- ADD THIS LINE

    if ("saved_by", b.id) in a.memory_flags:
        text = f"{a.name} stayed close to {b.name}, still remembering when {b.name} helped them in a moment of danger."
        used_memory = True
    elif ("saved_by", a.id) in b.memory_flags:
        text = f"{b.name} sought out {a.name}, remembering the help they were once given."
        used_memory = True
    elif a.trust.get(b.id, 0) >= 3 or b.trust.get(a.id, 0) >= 3:
        text = f"{a.name} and {b.name} naturally fell into each other's company, their bond now an easy one."
        used_memory = True
    else:
        if mood == "Calm":
            texts = [
                f"{a.name} and {b.name} spent the moon in easy company.",
                f"In the {world.tribe_name}, {a.name} and {b.name} spent time together.",
                f"{a.name} sought out {b.name}, and the two enjoyed each other's company."
            ]

            if climate["bonding_bias"] >= 0.35:
                texts.append(
                    f"With the tribe feeling unusually steady, {a.name} and {b.name} easily fell into one another's company."
                )

        elif mood in {"Uneasy", "Strained"}:
            texts = [
                f"{a.name} and {b.name} spent time together, a welcome relief from the strain in the tribe.",
                f"With tensions simmering in the {world.tribe_name}, {a.name} and {b.name} found comfort in each other's company.",
                f"{a.name} and {b.name} stayed close this moon, steadying each other amid growing tension."
            ]

            if climate["recovery_bias"] > 0.20:
                texts.append(
                    f"Even with unease hanging over the tribe, {a.name} and {b.name} seemed determined to keep each other grounded."
                )

        else:
            texts = [
                f"{a.name} and {b.name} found a brief moment of calm despite the tension gripping the tribe.",
                f"Even with the tribe on edge, {a.name} and {b.name} stayed close and drew comfort from one another.",
                f"In a tense and uneasy moon, {a.name} and {b.name} managed to find a little peace together."
            ]

            if climate["bonding_bias"] > climate["conflict_bias"]:
                texts.append(
                    f"Though the tribe felt dangerously strained, {a.name} and {b.name} still managed to hold onto each other."
                )

        text = random.choice(texts)

    if direction == "stabilizing":
         text += " The tribe seems to be trying to hold together."
    elif direction == "pressuring":
         text += " The pace of the tribe leaves little room for rest."
    elif direction == "watchful":
        text += " Others nearby seemed alert to everything happening."

    # light personality reaction echoes (ONLY if not memory-based)
    if not used_memory:
        if direction == "pressuring":
            if a.personality == "Kind" or b.personality == "Kind":
                text += " The harsher pace seems to weigh on them."
            elif a.personality == "Ambitious" or b.personality == "Ambitious":
                text += " Neither seemed especially troubled by the tribe's demanding pace."

        elif direction == "stabilizing":
            if a.personality == "Loyal" or b.personality == "Loyal":
                text += " Both seemed to respond well to the tribe's effort to steady itself."
            elif a.personality == "Moody" or b.personality == "Moody":
                text += " Even with the tribe trying to steady itself, the calm felt fragile."

        elif direction == "watchful":
            if a.personality == "Suspicious" or b.personality == "Suspicious":
                text += " The tense, alert atmosphere seemed almost natural to them."
            elif a.personality == "Kind" or b.personality == "Kind":
                text += " The constant vigilance made the moment feel more precious."

    cause = None

    if ("saved_by", b.id) in a.memory_flags or ("saved_by", a.id) in b.memory_flags:
        cause = "A remembered act of loyalty"
    elif a.trust.get(b.id, 0) >= 3 or b.trust.get(a.id, 0) >= 3:
        cause = "A strong existing bond"
    elif mood in {"Uneasy", "Strained", "Volatile", "Crisis"}:
        cause = "Shared strain in the tribe brought them together"
    elif climate["bonding_bias"] > 0.2:
        cause = "A steadier tribe climate encouraged closeness"

    log_event(
        world,
        text,
        involved_ids=[a.id, b.id],
        event_type="friend_event",
        cause=cause,
    )
    return True


def add_rival_event(world, a, b):
    direction = getattr(world, "direction", None)
    mood = get_world_mood(world)
    climate = get_tribe_climate(world)

    used_memory = False

    if ("abandoned_by", b.id) in a.memory_flags:
        text = f"{a.name} clashed with {b.name}, still carrying the sting of being abandoned when it mattered."
        used_memory = True
    elif ("abandoned_by", a.id) in b.memory_flags:
        text = f"{b.name} met {a.name} with open hostility, old resentment still hanging between them."
        used_memory = True
    elif a.resentment.get(b.id, 0) >= 3 or b.resentment.get(a.id, 0) >= 3:
        text = f"The hostility between {a.name} and {b.name} no longer feels like a passing disagreement."
        used_memory = True
    else:
        if mood == "Calm":
            texts = [
                f"{a.name} and {b.name} argued, though the dispute passed without disturbing the tribe too deeply.",
                f"{a.name} and {b.name} clashed over a minor dispute this moon.",
                f"Old tension flickered briefly between {a.name} and {b.name}."
            ]
        elif mood in {"Uneasy", "Strained"}:
            texts = [
                f"{a.name} and {b.name} argued again, adding to the strain already running through the tribe.",
                f"{a.name} and {b.name} clashed, and the mood in the tribe did little to soften it.",
                f"In the {world.tribe_name}, tension flared again between {a.name} and {b.name}."
            ]
        else:  # Volatile / Crisis
            texts = [
                f"{a.name} and {b.name} clashed, and others nearby took notice in the already tense tribe.",
                f"{a.name} and {b.name} argued fiercely, their hostility feeding the unrest around them.",
                f"With the tribe already on edge, conflict between {a.name} and {b.name} quickly turned sharp."
            ]

        text = random.choice(texts)

    if direction == "stabilizing":
        text += " Even so, the tribe seemed reluctant to let things escalate."
    elif direction == "pressuring":
        text += " Tension like this has become more common under the current pace."
    elif direction == "watchful":
        text += " Others nearby watched closely, as if expecting trouble."

    # light personality reaction echoes
    if not used_memory:
        if direction == "pressuring":
            if a.personality == "Ambitious" or b.personality == "Ambitious":
                text += " The tribe's demanding pace only seemed to sharpen the conflict."
            elif a.personality == "Kind" or b.personality == "Kind":
                text += " At least one of them seemed ill at ease with how harsh things have become."

        elif direction == "stabilizing":
            if a.personality == "Loyal" or b.personality == "Loyal":
                text += " Even in conflict, there was a sense that the tribe wanted to keep itself from splintering."
            elif a.personality == "Moody" or b.personality == "Moody":
                text += " The tribe's attempt at calm did little to soften the mood."

        elif direction == "watchful":
            if a.personality == "Suspicious" or b.personality == "Suspicious":
                text += " The atmosphere of caution seemed to encourage mistrust."
            elif a.personality == "Clever" or b.personality == "Clever":
                text += " Both seemed careful not to misstep under so many watchful eyes."

    cause = None

    if ("abandoned_by", b.id) in a.memory_flags or ("abandoned_by", a.id) in b.memory_flags:
        cause = "An old abandonment still lingers between them"
    elif a.resentment.get(b.id, 0) >= 3 or b.resentment.get(a.id, 0) >= 3:
        cause = "Long-growing resentment"
    elif mood in {"Volatile", "Crisis"}:
        cause = "High tension in the tribe sharpened the conflict"
    elif climate["conflict_bias"] > 0.2 or climate["suspicion_bias"] > 0.2:
        cause = "A tense tribe climate made conflict more likely"

    # rivalry arc progression: advance on every rival event
    a.rivalry_levels[b.id] = a.rivalry_levels.get(b.id, 0) + 1
    b.rivalry_levels[a.id] = b.rivalry_levels.get(a.id, 0) + 1

    level = a.rivalry_levels[b.id]

    log_event(
        world,
        text,
        involved_ids=[a.id, b.id],
        event_type="rival_event",
        cause=cause,
    )

    if level == 3:
        log_event(
            world,
            f"The conflict between {a.name} and {b.name} is becoming serious.",
            involved_ids=[a.id, b.id],
            event_type="rivalry_escalation",
            importance=4,
            cause="Repeated unresolved conflict",
        )

    elif level == 5:
        log_event(
            world,
            f"{a.name} and {b.name} can no longer avoid each other. Something will have to give.",
            involved_ids=[a.id, b.id],
            event_type="rivalry_crisis",
            importance=5,
            cause="A long-standing rivalry reaching a breaking point",
        )

    elif level >= 6 and random.random() < 0.5:

        outcome = random.choice(["injury", "break"])

        if outcome == "injury":
            victim = random.choice([a, b])
            victim.health = "Injured"

            log_event(
                world,
                f"{a.name} and {b.name}'s rivalry turned physical. {victim.name} was injured.",
                involved_ids=[a.id, b.id, victim.id],
                event_type="rivalry_injury",
                importance=6,
                cause="Escalation left unresolved for too long",
            )

        elif outcome == "break":
            log_event(
                world,
                f"{a.name} and {b.name}'s rivalry has divided them completely. They will not reconcile.",
                involved_ids=[a.id, b.id],
                event_type="rivalry_break",
                importance=6,
                cause="A long-standing conflict finally fractured beyond repair",
            )

            # optional: increase permanent resentment
            a.resentment[b.id] = a.resentment.get(b.id, 0) + 3
            b.resentment[a.id] = b.resentment.get(a.id, 0) + 3

    return True

def add_new_dragonet(world: World):
    if not world.dragons:
        return False

    existing_ids = [d.id for d in world.dragons]
    new_id = max(existing_ids) + 1 if existing_ids else 1

    chosen_tribe = random.choice(world.dragons).tribe

    candidates = [
        d for d in world.dragons
        if d.status == "Alive" and d.role != "Dragonet"
    ]

    parents = []

    # Prefer living mate pairs
    mate_pairs = []
    seen_pairs = set()

    for d in candidates:
        if d.mate_id is None:
            continue

        mate = next((x for x in candidates if x.id == d.mate_id), None)
        if not mate:
            continue

        pair_key = tuple(sorted((d.id, mate.id)))
        if pair_key in seen_pairs:
            continue

        seen_pairs.add(pair_key)

        # optional light weighting by trust
        trust_bonus = d.trust.get(mate.id, 0) + mate.trust.get(d.id, 0)
        weight = 1.0 + (trust_bonus * 0.1)

        mate_pairs.append((d, mate, weight))

    if mate_pairs and random.random() < 0.8:
        pair_choices = [(a, b) for a, b, _ in mate_pairs]
        pair_weights = [w for _, _, w in mate_pairs]
        p1, p2 = random.choices(pair_choices, weights=pair_weights, k=1)[0]
        parents = [p1, p2]

    elif len(candidates) >= 2:
        parents = random.sample(candidates, 2)
    elif len(candidates) == 1:
        parents = [candidates[0]]

    dragonet = generate_dragonet(new_id, chosen_tribe, parents)
    dragonet.parents = [p.id for p in parents]

    world.dragons.append(dragonet)

    for p in parents:
        p.dragonets.append(dragonet.id)

    if parents:
        parent_names = " and ".join([p.name for p in parents])
        text = f"{parent_names} welcomed a new dragonet named {dragonet.name}."
        ids = [dragonet.id] + [p.id for p in parents]
    else:
        text = f"A new dragonet named {dragonet.name} appeared in the tribe."
        ids = [dragonet.id]

    log_event(world, text, involved_ids=ids, event_type="birth", importance=4)
    return True


def handle_possible_death(world: World, dragon):
    if dragon.status != "Alive":
        return False

    death_chance = 0.0

    if dragon.age_moons >= 180:
        death_chance += 0.02
    if dragon.age_moons >= 220:
        death_chance += 0.05
    if dragon.age_moons >= 260:
        death_chance += 0.10

    if dragon.role == "Elder":
        death_chance += 0.03

    was_injured = (dragon.health == "Injured")
    if was_injured:
        death_chance += 0.05

    if random.random() < death_chance:
        dragon.status = "Dead"
        dragon.health = "Dead"

        if was_injured:
            dragon.cause_of_death = "injury"
        elif dragon.age_moons >= 180 or dragon.role == "Elder":
            dragon.cause_of_death = "natural"
        else:
            dragon.cause_of_death = "natural"

        surviving_mate = None

        if dragon.mate_id is not None:
            surviving_mate = next(
                (d for d in world.dragons if d.id == dragon.mate_id and d.status == "Alive"),
                None
            )

            if surviving_mate:
                flag = ("lost_mate", dragon.id, world.moon)

                already_recorded = any(
                    len(memory) >= 2 and memory[0] == "lost_mate" and memory[1] == dragon.id
                    for memory in surviving_mate.memory_flags
                )

                if not already_recorded:
                    surviving_mate.memory_flags.append(flag)

                surviving_mate.grief_level = 12
                surviving_mate.mate_id = None

                if hasattr(world, "tension"):
                    world.tension += 0.18

        if surviving_mate:
            texts = [
                f"{dragon.name} passed away under the stars, leaving {surviving_mate.name} behind in grief.",
                f"The tribe mourns the loss of {dragon.name}, and {surviving_mate.name} seems deeply shaken.",
                f"In the {world.tribe_name}, {dragon.name} died, leaving their mate {surviving_mate.name} to carry the loss.",
            ]
        else:
            texts = [
                f"{dragon.name} passed away under the stars.",
                f"The tribe mourns the loss of {dragon.name}.",
                f"In the {world.tribe_name}, {dragon.name} ascended to the sky after death.",
                f"{dragon.name} has died, leaving behind memories in the tribe."
            ]

        text = random.choice(texts)
        log_event(world, text, involved_ids=[dragon.id], event_type="death", importance=5)

        dragon.mate_id = None
        return True

    return False


def try_existing_relationship_event(world: World, living):
    climate = get_tribe_climate(world)

    weighted_candidates = []

    for dragon in living:
        for friend_id in dragon.friends:
            friend = next((d for d in living if d.id == friend_id), None)
            if friend and dragon.id < friend.id:
                weight = 1.0

                # Stronger trust = more likely this bond surfaces
                weight += dragon.trust.get(friend.id, 0) * 0.20
                weight += friend.trust.get(dragon.id, 0) * 0.20

                # Saved-by memories make friend echoes more likely
                if ("saved_by", friend.id) in dragon.memory_flags:
                    weight += 1.0
                if ("saved_by", dragon.id) in friend.memory_flags:
                    weight += 1.0

                if ("trusted_decision", friend.id) in dragon.memory_flags:
                    weight += 0.8
                if ("trusted_decision", dragon.id) in friend.memory_flags:
                    weight += 0.8

                # Climate support for bonding / recovery
                weight *= max(0.2, 1.0 + climate["bonding_bias"] + (climate["recovery_bias"] * 0.5))

                weighted_candidates.append(("friend", dragon, friend, weight))

        for rival_id in dragon.rivals:
            rival = next((d for d in living if d.id == rival_id), None)
            if rival and dragon.id < rival.id:
                weight = 1.0

                # Stronger resentment = more likely this conflict resurfaces
                weight += dragon.resentment.get(rival.id, 0) * 0.20
                weight += rival.resentment.get(dragon.id, 0) * 0.20

                # Abandonment memories make rival echoes more likely
                if ("abandoned_by", rival.id) in dragon.memory_flags:
                    weight += 1.0
                if ("abandoned_by", dragon.id) in rival.memory_flags:
                    weight += 1.0

                if ("seen_as_unreliable", rival.id) in dragon.memory_flags:
                    weight += 0.8
                if ("seen_as_unreliable", dragon.id) in rival.memory_flags:
                    weight += 0.8

                # Climate support for conflict / suspicion
                weight *= max(0.2, 1.0 + climate["conflict_bias"] + (climate["suspicion_bias"] * 0.5))

                weighted_candidates.append(("rival", dragon, rival, weight))

    if not weighted_candidates:
        return False

    # ---- Grief event weighting ----
    grief_candidates = [
        d for d in living
        if getattr(d, "grief_level", 0) > 0
    ]

    grief_pool = []
    for d in grief_candidates:
        weight = 1.0 + (d.grief_level * 0.08)

        # In calmer or more merciful climates, grief can surface as visible withdrawal
        weight += max(0.0, climate["recovery_bias"] * 0.5)
        weight += max(0.0, climate["mercy_bias"] * 0.5)

        # In suspicious / conflict-heavy climates, grief may be suppressed a bit
        weight -= max(0.0, climate["conflict_bias"] * 0.25)
        weight -= max(0.0, climate["suspicion_bias"] * 0.25)

        weight = max(0.25, weight)
        grief_pool.append(("grief", d, None, weight))

    # Combine all possible relationship-surface events
    combined = weighted_candidates + grief_pool

    selections = [(etype, a, b) for etype, a, b, _ in combined]
    weights = [w for _, _, _, w in combined]

    event_type, a, b = random.choices(selections, weights=weights, k=1)[0]

    if event_type == "grief":
        if a.grief_level >= 8:
            texts = [
                f"{a.name} kept to themselves this moon, their grief still raw.",
                f"{a.name} seemed distant and shaken, the loss still weighing heavily.",
                f"{a.name} avoided others this moon, grief still close to the surface."
            ]
        elif a.grief_level >= 4:
            texts = [
                f"{a.name} was quieter than usual this moon, still carrying their loss.",
                f"{a.name} seemed withdrawn at times, grief not yet fully faded.",
                f"The loss still lingered around {a.name}, even if less sharply than before."
            ]
        else:
            texts = [
                f"{a.name} seemed reflective this moon, their old grief still not fully gone.",
                f"{a.name} carried a quiet sadness this moon, though time has softened it.",
                f"Though the worst had passed, the loss still lingered in {a.name}."
            ]

        # climate-aware grief tone
        if climate["mercy_bias"] > 0.2:
            texts.append(
                f"In a tribe that seemed gentler than usual, {a.name}'s grief was quietly noticed by others."
            )
        if climate["suspicion_bias"] > 0.2:
            texts.append(
                f"With the tribe feeling watchful and tense, {a.name} withdrew further into their grief."
            )

        log_event(
            world,
            random.choice(texts),
            involved_ids=[a.id],
            event_type="grief_event",
            importance=3
        )
        return True

    if event_type == "friend":
        return add_friend_event(world, a, b)
    elif event_type == "rival":
        return add_rival_event(world, a, b)

    return False


def create_border_sighting_event(world):
    tribe = get_random_foreign_tribe(world)
    if not tribe:
        return False

    region = get_random_region(world, tribe)
    landmark = get_random_landmark(world, region)

    record_region_activity(world, region)

    prompt_text = (
        f"A patrol from the {tribe}s has been spotted near {landmark} in {region}. "
        f"They appear to be watching your territory."
    )

    options = [
        {"id": "observe", "text": "Observe them from a distance"},
        {"id": "approach", "text": "Approach and question them"},
        {"id": "drive_off", "text": "Drive them away immediately"},
    ]

    world.pending_choice = {
        "type": "border_sighting",
        "tribe": tribe,
        "region": region,
        "landmark": landmark,
        "text": prompt_text,
        "options": options,
    }
    return True

def create_border_violation_event(world):
    tribe = get_random_foreign_tribe(world)
    if not tribe:
        return False

    region = get_random_region(world, tribe)
    landmark = get_random_landmark(world, region)

    record_region_activity(world, region)

    prompt_text = (
        f"Tracks from the {tribe}s have been discovered near {landmark} in {region}. "
        f"They may have crossed into your territory."
    )

    options = [
        {"id": "ignore_tracks", "text": "Ignore it for now"},
        {"id": "investigate_tracks", "text": "Investigate further"},
        {"id": "respond_forcefully", "text": "Prepare a response"},
    ]

    world.pending_choice = {
        "type": "border_violation",
        "tribe": tribe,
        "region": region,
        "landmark": landmark,
        "text": prompt_text,
        "options": options,
    }

    return True

def create_aid_delivery_event(world):
    tribe = get_random_foreign_tribe(world)
    if not tribe:
        return False

    region = get_random_region(world, tribe)
    landmark = get_random_landmark(world, region)

    record_region_activity(world, region)

    prompt_text = (
        f"A small group of {tribe}s is delivering supplies near {landmark} in {region}. "
        f"They request safe passage through your lands."
    )

    options = [
        {"id": "allow_aid", "text": "Allow the aid to pass"},
        {"id": "inspect_aid", "text": "Inspect the supplies"},
        {"id": "deny_aid", "text": "Deny passage"},
    ]

    world.pending_choice = {
        "type": "aid_delivery",
        "tribe": tribe,
        "region": region,
        "landmark": landmark,
        "text": prompt_text,
        "options": options,
    }

    return True

# ---------- PLAYER CHOICES ----------

def create_injured_patrol_choice(world):
    climate = get_tribe_climate(world)
    hostile_tribe, hostile_score = get_most_hostile_relation(world)

    region = None
    landmark = None

    if hostile_tribe and hostile_score <= -20:
        region = get_random_region(world, hostile_tribe)
        landmark = get_random_landmark(world, region)
        record_region_activity(world, region)

    candidates = get_eligible_non_dragonets(world)

    if len(candidates) < 2:
        return False

    possible_pairs = []

    for i in range(len(candidates)):
        for j in range(len(candidates)):
            if i == j:
                continue

            a = candidates[i]  # injured dragon
            b = candidates[j]  # helper dragon

            weight = 1.0

            if ("saved_by", b.id) in a.memory_flags:
                weight += 1.5

            if ("abandoned_by", b.id) in a.memory_flags:
                weight += 1.2

            if a.mate_id == b.id or b.mate_id == a.id:
                weight += 1.8

            weight += a.trust.get(b.id, 0) * 0.15
            weight += a.resentment.get(b.id, 0) * 0.20

            weight *= max(
                0.25,
                1.0
                + climate["risk_bias"]
                + (climate["conflict_bias"] * 0.35)
                - (climate["recovery_bias"] * 0.20)
            )

            if hostile_score <= -40:
                weight *= 1.35
            elif hostile_score <= -20:
                weight *= 1.15

            possible_pairs.append((a, b, weight))

    if not possible_pairs:
        return False

    pairs = [(a, b) for a, b, _ in possible_pairs]
    weights = [w for _, _, w in possible_pairs]
    a, b = random.choices(pairs, weights=weights, k=1)[0]

    if a.health != "Injured":
        a.health = "Injured"

        if hostile_tribe and hostile_score <= -20:
            location_text = f" near {landmark} in {region}" if region and landmark else ""
            injury_text = (
                f"{a.name} was injured while out on patrol with {b.name}{location_text}, "
                f"not far from territory where tension with the {hostile_tribe}s has been rising."
            )
        else:
            injury_text = f"{a.name} was injured while out on patrol with {b.name}."

        log_event(
            world,
            injury_text,
            involved_ids=[a.id, b.id],
            event_type="injury",
            importance=3
        )

    mood = get_world_mood(world)

    approaching_tribe_text = "rival dragons"
    if hostile_tribe and hostile_score <= -20:
        approaching_tribe_text = f"{hostile_tribe} dragons"

    if a.mate_id == b.id or b.mate_id == a.id:
        prompt_text = (
            f"{a.name} and {b.name} are on patrol together. When {a.name} is injured and "
            f"{approaching_tribe_text} can be heard approaching, "
            f"{b.name} must decide whether to stay with their mate or run for help."
        )
    elif ("saved_by", b.id) in a.memory_flags:
        prompt_text = (
            f"{a.name} and {b.name} are on patrol. {a.name} is injured again, and "
            f"{approaching_tribe_text} can be heard approaching. "
            f"{a.name} still remembers that {b.name} once stayed when it mattered. "
            f"What should {b.name} do now?"
        )
    elif ("abandoned_by", b.id) in a.memory_flags:
        prompt_text = (
            f"{a.name} and {b.name} are on patrol. {a.name} is injured, and "
            f"{approaching_tribe_text} can be heard approaching. "
            f"{a.name} has never forgotten the last time {b.name} left. "
            f"What should {b.name} do now?"
        )
    else:
        if mood in {"Volatile", "Crisis"}:
            prompt_text = (
                f"{a.name} and {b.name} are on patrol in a tribe already on edge. "
                f"{a.name} is injured, and {approaching_tribe_text} can be heard approaching through the darkness. "
                f"What should {b.name} do?"
            )
        elif climate["recovery_bias"] > 0.20:
            prompt_text = (
                f"{a.name} and {b.name} are on patrol. {a.name} is injured, and "
                f"{approaching_tribe_text} can be heard approaching. "
                f"In a tribe that still seems to hold together, what should {b.name} do?"
            )
        else:
            prompt_text = (
                f"{a.name} and {b.name} are on patrol. {a.name} is injured, and "
                f"{approaching_tribe_text} can be heard approaching. "
                f"What should {b.name} do?"
            )

    world.pending_choice = {
        "type": "injured_patrol_choice",
        "text": prompt_text,
        "involved_ids": [a.id, b.id],
        "options": [
            {"id": "stay_and_help", "text": f"Stay and help {a.name}"},
            {"id": "run_for_help", "text": "Return to camp for help"}
        ]
    }
    return True


def create_rival_confrontation_choice(world):
    climate = get_tribe_climate(world)
    mood = get_world_mood(world)
    eligible = get_eligible_non_dragonets(world)

    rival_pairs = []
    weights = []

    for dragon in eligible:
        for rival_id in dragon.rivals:
            rival = next((d for d in eligible if d.id == rival_id), None)
            if rival and dragon.id < rival.id:
                weight = 1.0

                # abandonment history makes confrontation more likely
                if ("abandoned_by", rival.id) in dragon.memory_flags:
                    weight += 1.2
                if ("abandoned_by", dragon.id) in rival.memory_flags:
                    weight += 1.2

                # stronger resentment makes this pair more likely to surface
                weight += dragon.resentment.get(rival.id, 0) * 0.20
                weight += rival.resentment.get(dragon.id, 0) * 0.20



                # climate effect:
                # tense, suspicious, conflict-heavy tribes surface more confrontation dilemmas
                weight *= max(
                    0.25,
                    1.0
                    + climate["conflict_bias"]
                    + (climate["suspicion_bias"] * 0.40)
                    - (climate["recovery_bias"] * 0.20)
                    - (climate["mercy_bias"] * 0.15)
                )

                rival_pairs.append((dragon, rival))
                weights.append(weight)

    if not rival_pairs:
        return False



    a, b = random.choices(rival_pairs, weights=weights, k=1)[0]

    if ("abandoned_by", b.id) in a.memory_flags:
        prompt_text = (
            f"{a.name} and {b.name}, long-standing rivals, cross paths on patrol. "
            f"{a.name} still carries the memory of being abandoned by {b.name}. What should {a.name} do?"
        )
    elif ("abandoned_by", a.id) in b.memory_flags:
        prompt_text = (
            f"{a.name} and {b.name}, long-standing rivals, cross paths on patrol. "
            f"Old resentment still hangs between them. What should {a.name} do?"
        )
    elif a.resentment.get(b.id, 0) >= 3 or b.resentment.get(a.id, 0) >= 3:
        prompt_text = (
            f"{a.name} and {b.name}, long-standing rivals, cross paths on patrol. "
            f"The hostility between them no longer feels like a passing disagreement. What should {a.name} do?"
        )
    else:
        if mood in {"Volatile", "Crisis"}:
            prompt_text = (
                f"{a.name} and {b.name}, long-standing rivals, cross paths during a patrol while the tribe is already on edge. "
                f"What should {a.name} do?"
            )
        elif climate["mercy_bias"] > 0.20:
            prompt_text = (
                f"{a.name} and {b.name}, long-standing rivals, cross paths on patrol. "
                f"The tribe seems steadier than usual, but the tension between them remains. What should {a.name} do?"
            )
        elif climate["suspicion_bias"] > 0.20:
            prompt_text = (
                f"{a.name} and {b.name}, long-standing rivals, cross paths on patrol in a tribe grown watchful and uneasy. "
                f"What should {a.name} do?"
            )
        else:
            prompt_text = (
                f"{a.name} and {b.name}, long-standing rivals, cross paths on patrol. "
                f"What should {a.name} do?"
            )

    world.pending_choice = {
        "type": "rival_confrontation_choice",
        "text": prompt_text,
        "involved_ids": [a.id, b.id],
        "options": [
            {"id": "back_down", "text": f"Have {a.name} back down and avoid a fight"},
            {"id": "confront", "text": f"Have {a.name} confront {b.name} directly"}
        ]
    }
    return True

def try_leader_event(world):
    leader = get_leader_by_id(world)

    if not leader or leader.status != "Alive":
        return False

    climate = get_tribe_climate(world)

    # low chance — this should feel occasional, not spammy
    if random.random() > 0.15:
        return False

    texts = []

    pressure = getattr(leader, "leadership_pressure", 0)
    traits = getattr(leader, "personality_traits", []) or []
    name = leader.name

    if "Kind" in traits:
        texts.append(f"{name} took time to settle a dispute, easing tensions in the tribe.")
        texts.append(f"{name} checked in on several dragons this moon, making the tribe feel more connected.")

    if "Loyal" in traits:
        texts.append(f"{name} publicly recognized the efforts of others, strengthening bonds within the tribe.")

    if "Clever" in traits:
        texts.append(f"{name} adjusted patrol strategies, avoiding unnecessary risk.")

    if "Ambitious" in traits:
        texts.append(f"{name} pushed the tribe harder this moon, urging them toward greater strength.")
        texts.append(f"{name}'s drive pushed the tribe forward, though not everyone welcomed it.")

    if "Moody" in traits:
        texts.append(f"{name}'s shifting mood unsettled others this moon.")
        texts.append(f"{name} reacted sharply to a minor issue, leaving others uneasy.")

    if "Suspicious" in traits:
        texts.append(f"{name} questioned the loyalty of others, casting a shadow over the tribe.")
        texts.append(f"{name} kept a close watch on others this moon, trust feeling thin.")

    if pressure >= 8:
        texts.append(f"{name} seemed strained this moon, their decisions sharper and less patient.")
        texts.append(f"{name} struggled to maintain control as pressure mounted.")
    elif pressure >= 4:
        texts.append(f"{name} seemed burdened, carrying the weight of the tribe's troubles.")

    if not texts:
        texts.append(f"{name} oversaw the tribe this moon.")

    text = random.choice(texts)

    cause = None
    if pressure >= 8:
        cause = "Leadership pressure is starting to affect the leader"
    elif "Kind" in traits:
        cause = "The leader's gentle nature shaped the tribe's mood"
    elif "Loyal" in traits:
        cause = "The leader's loyalty strengthened the tribe"
    elif "Clever" in traits:
        cause = "The leader's careful judgment influenced events"
    elif "Ambitious" in traits:
        cause = "The leader's ambition pushed the tribe harder"
    elif "Moody" in traits:
        cause = "The leader's instability affected the tribe"
    elif "Suspicious" in traits:
        cause = "The leader's distrust cast a shadow over the tribe"

    log_event(
        world,
        text,
        involved_ids=[leader.id],
        event_type="leader_event",
        importance=2,
        cause=cause,
    )

    if pressure >= 10 and random.random() < 0.3:
        log_event(
            world,
            f"{leader.name}'s leadership faltered under pressure, worsening tensions in the tribe.",
            involved_ids=[leader.id],
            event_type="leadership_failure",
            importance=5,
            cause="Accumulated pressure from unresolved problems",
        )

        if hasattr(world, "tension"):
            world.tension += 0.5

    return True

def create_leader_decision(world):
    leader = get_leader_by_id(world)

    if not leader or leader.status != "Alive":
        return False

    world.pending_choice = {
        "type": "leader_decision",
        "text": f"As leader, {leader.name} must decide how to guide the tribe this moon.",
        "involved_ids": [leader.id],
        "options": [
            {"id": "stabilize", "text": "Focus on unity and stability"},
            {"id": "push_strength", "text": "Push the tribe to become stronger"},
            {"id": "watch_closely", "text": "Encourage vigilance and caution"},
        ]
    }

    return True


def create_diplomatic_choice(world):
    tribe = get_random_foreign_tribe(world)
    if not tribe:
        return False

    score = world.tribal_relations.get(tribe, 0)

    recent_incidents = world.tribal_incidents.get(tribe, [])
    incident_text = " ".join(recent_incidents[-2:]).lower()

    # ---- Influence scenario based on recent diplomacy ----

    if "pressure" in incident_text or "patrol" in incident_text:
        scenario = random.choices(
            ["border_misunderstanding", "safe_passage", "wounded_outsider"],
            weights=[0.5, 0.2, 0.3]
        )[0]

    elif "peace" in incident_text or "aid" in incident_text:
        scenario = random.choices(
            ["safe_passage", "wounded_outsider", "border_misunderstanding"],
            weights=[0.5, 0.3, 0.2]
        )[0]

    else:
        # fallback to your original logic
        if score <= -40:
            scenario = random.choices(
                ["border_misunderstanding", "wounded_outsider", "safe_passage"],
                weights=[0.5, 0.3, 0.2]
            )[0]
 
        elif score <= -10:
            scenario = random.choices(
                ["border_misunderstanding", "wounded_outsider", "safe_passage"],
                weights=[0.4, 0.3, 0.3]
            )[0]

        elif score < 10:
            scenario = random.choice([
                "safe_passage",
                "wounded_outsider",
                "border_misunderstanding"
            ])

        else:
            scenario = random.choices(
                ["safe_passage", "wounded_outsider", "border_misunderstanding"],
                weights=[0.5, 0.3, 0.2]
            )[0]

    region = get_random_region(world, tribe)
    landmark = get_random_landmark(world, region)
    record_region_activity(world, region)

    if scenario == "safe_passage":

        if score <= -40:
            prompt_text = (
                f"A small group of {tribe}s appears near the edge of your territory under a flag of truce. "
                f"Relations are already hostile. They ask for safe passage. How should the tribe respond?"
            )
        elif score <= -10:
            prompt_text = (
                f"A small group of {tribe}s approaches the edge of your territory seeking safe passage. "
                f"Relations are uneasy. How should the tribe respond?"
            )
        elif score < 10:
            prompt_text = (
                f"A small group of {tribe}s approaches the edge of your territory seeking safe passage. "
                f"Relations are neutral. How should the tribe respond?"
            )
        else:
            prompt_text = (
                f"A small group of {tribe}s approaches in peace, asking to pass safely through nearby territory. "
                f"Relations are reasonably positive. How should the tribe respond?"
            )

        options = [
            {"id": "allow_passage", "text": "Allow them safe passage"},
            {"id": "refuse_passage", "text": "Refuse and turn them away"},
            {"id": "escort_passage", "text": "Escort them through your territory"},
        ]

    elif scenario == "wounded_outsider":

        prompt_text = (
            f"A wounded {tribe} is found near the edge of your territory at {landmark} in {region}, separated from their own kind. "
            f"How should the tribe respond?"
        )

        options = [
            {"id": "help_wounded", "text": "Help them recover"},
            {"id": "ignore_wounded", "text": "Leave them and move on"},
            {"id": "detain_wounded", "text": "Detain and question them"},
        ]

    else:

        prompt_text = (
            f"A patrol from the {tribe}s is spotted near your border. They claim they crossed by mistake. "
            f"How should the tribe respond?"
        )

        options = [
            {"id": "accept_explanation", "text": "Accept the explanation and let them leave"},
            {"id": "issue_warning", "text": "Warn them harshly and send them away"},
            {"id": "escalate_border", "text": "Escalate and challenge their presence"},
        ]

    

    world.pending_choice = {
        "type": "diplomatic_choice",
        "scenario": scenario,
        "tribe": tribe,
        "region": region,
        "landmark": landmark,
        "text": prompt_text,
        "options": options,
    }

    return True


def create_tribal_policy_choice(world):
    tribes = list(getattr(world, "tribal_relations", {}).keys())

    if not tribes:
        return False

    tribe = random.choice(tribes)
    score = world.tribal_relations.get(tribe, 0)

    if score <= -30:
        prompt_text = (
            f"The tribe has an opportunity to shape its stance toward the {tribe}s this moon. "
            f"Relations are already hostile. What approach should it take?"
        )
    elif score <= -10:
        prompt_text = (
            f"The tribe has an opportunity to shape its stance toward the {tribe}s this moon. "
            f"Relations are uneasy. What approach should it take?"
        )
    elif score < 10:
        prompt_text = (
            f"The tribe has an opportunity to shape its stance toward the {tribe}s this moon. "
            f"Relations are neutral. What approach should it take?"
        )
    else:
        prompt_text = (
            f"The tribe has an opportunity to shape its stance toward the {tribe}s this moon. "
            f"Relations are already fairly positive. What approach should it take?"
        )

    world.pending_choice = {
        "type": "tribal_policy_choice",
        "tribe": tribe,
        "text": prompt_text,
        "options": [
            {"id": "peace_gesture", "text": "Send a peace gesture"},
            {"id": "border_patrol", "text": "Increase border patrols"},
            {"id": "border_pressure", "text": "Apply border pressure"},
            {"id": "offer_aid", "text": "Offer practical aid"},
        ]
    }

    return True

def create_incoming_diplomacy_choice(world):
    tribes = [
        t for t in world.tribal_relations.keys()
        if world.diplomacy_cooldowns.get(t, 0) <= 0
    ]

    if not tribes:
        return False

    weights = []

    for t in tribes:
        score = world.tribal_relations.get(t, 0)
        weight = 1.0

        if score >= 10:
            weight += 1.0
        elif score <= -30:
            weight += 0.8
        elif score <= -10:
            weight += 0.4

        weights.append(weight)

    tribe = random.choices(tribes, weights=weights, k=1)[0]
    score = world.tribal_relations.get(tribe, 0)
    queen = world.tribal_leaders.get(tribe, f"Queen of the {tribe}s")
    trait = world.tribal_traits.get(tribe, "neutral")
    region = get_random_region(world, tribe)
    landmark = get_random_landmark(world, region)
    record_region_activity(world, region)

    if score <= -30:
        scenario = random.choices(
            ["warning", "truce_offer", "aid_request"],
            weights=[0.55, 0.25, 0.20]
        )[0]
    elif score <= -10:
        scenario = random.choices(
            ["warning", "truce_offer", "aid_request"],
            weights=[0.35, 0.35, 0.30]
        )[0]
    elif score < 10:
        scenario = random.choices(
            ["aid_request", "truce_offer", "warning"],
            weights=[0.35, 0.35, 0.30]
        )[0]
    else:
        scenario = random.choices(
            ["aid_request", "truce_offer", "warning"],
            weights=[0.45, 0.40, 0.15]
        )[0]

    if trait == "aggressive":
        warning_bias = 1.3
        truce_bias = 0.8
        aid_bias = 0.8
    elif trait == "cautious":
        warning_bias = 0.9
        truce_bias = 1.2
        aid_bias = 1.1
    elif trait == "opportunistic":
        warning_bias = 1.0
        truce_bias = 1.0
        aid_bias = 1.3
    else:
        warning_bias = truce_bias = aid_bias = 1.0

    if scenario == "aid_request":
        text = (
            f"{queen} of the {tribe}s has sent word requesting practical aid after hardship near {landmark} in {region}. "
            f"How should the tribe respond?"
        )
        options = [
            {"id": "grant_aid", "text": "Send aid"},
            {"id": "refuse_aid", "text": "Refuse"},
            {"id": "limited_aid", "text": "Send limited aid"},
        ]

    elif scenario == "warning":
        text = (
            f"{queen} of the {tribe}s has sent a stern warning about recent tensions near {landmark} in {region}. "
            f"How should the tribe respond?"
        )
        options = [
            {"id": "deescalate_warning", "text": "De-escalate diplomatically"},
            {"id": "ignore_warning", "text": "Ignore the warning"},
            {"id": "answer_firmly", "text": "Respond with a firm warning of your own"},
        ]

    else:  # truce_offer
        text = (
            f"{queen} of the {tribe}s has proposed a temporary truce to ease tensions. "
            f"How should the tribe respond?"
        )
        options = [
            {"id": "accept_truce", "text": "Accept the truce"},
            {"id": "reject_truce", "text": "Reject it"},
            {"id": "conditional_truce", "text": "Accept with conditions"},
        ]

    world.pending_choice = {
        "type": "incoming_diplomacy_choice",
        "tribe": tribe,
        "scenario": scenario,
        "region": region,
        "landmark": landmark,
        "text": text,
        "options": options,
    }

    world.diplomacy_cooldowns[tribe] = 3
    return True

def normalize_region_tribe_name(tribe):
    if not tribe:
        return tribe

    mapping = {
        "MudWing": "MudWings",
        "SandWing": "SandWings",
        "SkyWing": "SkyWings",
        "SeaWing": "SeaWings",
        "RainWing": "RainWings",
        "IceWing": "IceWings",
        "NightWing": "NightWings",
    }

    return mapping.get(tribe, tribe)


def get_regions_for_tribe(world, tribe):
    tribe = normalize_region_tribe_name(tribe)
    return [
        r for r, owner in world.territory_control.items()
        if owner == tribe
    ]


def get_random_region(world, tribe):
    tribe = normalize_region_tribe_name(tribe)
    regions = get_regions_for_tribe(world, tribe)

    if not regions:
        return "unknown region"

    weights = []
    for region in regions:
        activity = world.region_activity.get(region, 0)
        weight = 1.0 + (activity * 0.25)
        weights.append(weight)

    return random.choices(regions, weights=weights, k=1)[0]

def get_random_landmark(world, region):
    landmarks = world.region_landmarks.get(region, [])
    return random.choice(landmarks) if landmarks else "unknown landmark"

def record_region_activity(world, region, amount=1):
    if not region or region == "unknown region":
        return

    if region not in world.region_activity:
        world.region_activity[region] = 0

    world.region_activity[region] += amount


def get_region_intensity(world, region):
    if not region:
        return 0.0

    activity = world.region_activity.get(region, 0)

    # soft scaling
    if activity >= 6:
        return 0.25   # high tension area
    elif activity >= 3:
        return 0.15   # medium activity
    elif activity >= 1:
        return 0.05   # low activity
    else:
        return 0.0


def get_top_active_regions(world, limit=3):
    items = sorted(
        world.region_activity.items(),
        key=lambda x: x[1],
        reverse=True
    )
    return items[:limit]

def apply_world_drift(world: World):
    for tribe in list(world.diplomacy_cooldowns.keys()):
        world.diplomacy_cooldowns[tribe] -= 1
        if world.diplomacy_cooldowns[tribe] <= 0:
            del world.diplomacy_cooldowns[tribe]

    for dragon in world.dragons:
        if dragon.status == "Alive" and dragon.grief_level > 0:
            dragon.grief_level -= 1

        if dragon.status == "Alive" and getattr(dragon, "leadership_pressure", 0) > 0:
            dragon.leadership_pressure -= 1

        for k in list(dragon.trust.keys()):
            dragon.trust[k] *= 0.95
            if dragon.trust[k] < 0.1:
                del dragon.trust[k]

        for k in list(dragon.resentment.keys()):
            dragon.resentment[k] *= 0.95
            if dragon.resentment[k] < 0.1:
                del dragon.resentment[k]


def advance_moon(world: World):

    living = get_living_dragons(world)

    if world.pending_choice is not None:
        return False
    
    apply_world_drift(world)

    if getattr(world, "direction_timer", 0) > 0:
        world.direction_timer -= 1
        if world.direction_timer <= 0:
            world.direction = None

    world.moon += 1



    for dragon in living:
        tick_dragon_progression(world, dragon, living)
        handle_possible_death(world, dragon)



        if dragon.status == "Alive" and dragon.legend_flags.get("pending_survival_check") == 1:
            dragon.hardship_survived += 1
            dragon.legend_flags["pending_survival_check"] = 0

    maintain_hierarchy(world)
    apply_leader_influence(world)

    if random.random() < 0.20:
        add_new_dragonet(world)


    # occasional player choice
    if world.pending_choice is None:
        choice_roll = random.random()

        if choice_roll < 0.08:
            created = create_leader_decision(world)
            if created:
                world.event_log = world.event_log[-100:]
                return True

        elif choice_roll < 0.14:
            created = create_injured_patrol_choice(world)
            if created:
                world.event_log = world.event_log[-100:]
                return True

        elif choice_roll < 0.20:
            created = create_rival_confrontation_choice(world)
            if created:
                world.event_log = world.event_log[-100:]
                return True

        elif choice_roll < 0.25:
            created = create_diplomatic_choice(world)
            if created:
                world.event_log = world.event_log[-100:]
                return True

        elif choice_roll < 0.31:
            created = create_tribal_policy_choice(world)
            if created:
                world.event_log = world.event_log[-100:]
                return True

        elif choice_roll < 0.36:
            created = create_incoming_diplomacy_choice(world)
            if created:
                world.event_log = world.event_log[-100:]
                return True

        elif choice_roll < 0.41:
            created = create_border_sighting_event(world)
            if created:
                world.event_log = world.event_log[-100:]
                return True

        elif choice_roll < 0.46:
            created = create_border_violation_event(world)
            if created:
                world.event_log = world.event_log[-100:]
                return True

        elif choice_roll < 0.51:
            created = create_aid_delivery_event(world)
            if created:
                world.event_log = world.event_log[-100:]
                return True


    run_event_phase(world)

    leader = get_leader_by_id(world)

    if leader and leader.status == "Alive":
        pressure = 0

        # tension contributes
        pressure += int(getattr(world, "tension", 0))

        # injured dragons increase pressure
        injured = sum(1 for d in world.dragons if d.health == "Injured")
        pressure += injured * 0.5

        # recent deaths increase pressure
        recent_deaths = [
            e for e in world.event_log[-5:]
            if isinstance(e, dict) and e.get("type") == "death"
        ]
        pressure += len(recent_deaths) * 1.5

        leader.leadership_pressure += int(pressure)

    try_leader_event(world)



    run_politics_phase(world)
    drift_relations(world)
    clamp_relations(world)

    world.tension = max(0.0, min(5.0, world.tension))
    world.previous_tribal_relations = world.tribal_relations.copy()

    evaluate_world_titles(world)

    world.event_log = world.event_log[-100:]
    return True