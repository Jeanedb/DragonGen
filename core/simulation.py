import random
from core.world import World
from core.generator import generate_dragonet
from core.sim.logging import log_event
from core.sim.relationships import add_friendship, add_rivalry
from core.sim.choices import resolve_choice
from core.sim.progression import tick_dragon_progression
from core.sim.events import run_event_phase
from core.sim.leadership import maintain_hierarchy, apply_leader_influence

def are_family(a, b):
    if a.id in b.parents or b.id in a.parents:
        return True
    if set(a.parents) & set(b.parents):
        return True
    return False

def get_living_dragons(world: World):
    return [d for d in world.dragons if d.status == "Alive"]

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
    leader = getattr(world, "leader", None)

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
    climate = get_tribe_climate(world)
    mood = get_world_mood(world)

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

        text = random.choice(texts)

    if direction == "stabilizing":
         text += " The tribe seems to be trying to hold together."
    elif direction == "pressuring":
         text += " The pace of the tribe leaves little room for rest."
    elif direction == "watchful":
        text += " Others nearby seemed alert to everything happening."

    # light personality reaction echoes
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

    log_event(world, text, involved_ids=[a.id, b.id], event_type="friend_event")
    return True


def add_rival_event(world, a, b):
    direction = getattr(world, "direction", None)
    mood = get_world_mood(world)

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
                text += f" The tribe's demanding pace only seemed to sharpen the conflict."
            elif a.personality == "Kind" or b.personality == "Kind":
                text += f" At least one of them seemed ill at ease with how harsh things have become."

        elif direction == "stabilizing":
            if a.personality == "Loyal" or b.personality == "Loyal":
                text += f" Even in conflict, there was a sense that the tribe wanted to keep itself from splintering."
            elif a.personality == "Moody" or b.personality == "Moody":
                text += f" The tribe's attempt at calm did little to soften the mood."

        elif direction == "watchful":
            if a.personality == "Suspicious" or b.personality == "Suspicious":
                text += f" The atmosphere of caution seemed to encourage mistrust."
            elif a.personality == "Clever" or b.personality == "Clever":
                text += f" Both seemed careful not to misstep under so many watchful eyes."

    log_event(world, text, involved_ids=[a.id, b.id], event_type="rival_event")
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

    if dragon.health == "Injured":
        death_chance += 0.05

    if random.random() < death_chance:
        dragon.status = "Dead"
        dragon.health = "Dead"

        if dragon.health == "Injured":
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
                flag = ("lost_mate", dragon.id)
                if flag not in surviving_mate.memory_flags:
                    surviving_mate.memory_flags.append(flag)

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

                # Climate support for conflict / suspicion
                weight *= max(0.2, 1.0 + climate["conflict_bias"] + (climate["suspicion_bias"] * 0.5))

                weighted_candidates.append(("rival", dragon, rival, weight))

    if not weighted_candidates:
        return False

    # ---- Grief event weighting ----
    grief_candidates = [
        d for d in living
        if any(flag == "lost_mate" for flag, _ in d.memory_flags)
    ]

    grief_pool = []
    for d in grief_candidates:
        weight = 1.0

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
        texts = [
            f"{a.name} kept to themselves this moon, still grieving their loss.",
            f"{a.name} seemed distant and withdrawn, the loss of their mate still weighing heavily.",
            f"{a.name} avoided others this moon, grief still close beneath the surface."
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



# ---------- PLAYER CHOICES ----------

def create_injured_patrol_choice(world):
    climate = get_tribe_climate(world)

    candidates = [
        d for d in world.dragons
        if d.status == "Alive" and d.role != "Dragonet"
    ]

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

            # If b once saved a, make it more likely they end up in this kind of moment again
            if ("saved_by", b.id) in a.memory_flags:
                weight += 1.5

            # If b once abandoned a, also make it more likely they cross paths again
            if ("abandoned_by", b.id) in a.memory_flags:
                weight += 1.2

            if a.mate_id == b.id or b.mate_id == a.id:
                weight += 1.8

            # existing strong feelings also increase likelihood of meaningful encounters
            weight += a.trust.get(b.id, 0) * 0.15
            weight += a.resentment.get(b.id, 0) * 0.20

            # climate effect:
            # dangerous, unstable tribes surface more injury/rescue dilemmas
            weight *= max(
                0.25,
                1.0
                + climate["risk_bias"]
                + (climate["conflict_bias"] * 0.35)
                - (climate["recovery_bias"] * 0.20)
            )

            possible_pairs.append((a, b, weight))

    if not possible_pairs:
        return False

    pairs = [(a, b) for a, b, _ in possible_pairs]
    weights = [w for _, _, w in possible_pairs]
    a, b = random.choices(pairs, weights=weights, k=1)[0]

    if a.health != "Injured":
        a.health = "Injured"
        log_event(
            world,
            f"{a.name} was injured while out on patrol with {b.name}.",
            involved_ids=[a.id, b.id],
            event_type="injury",
            importance=3
        )

    mood = get_world_mood(world)

    if a.mate_id == b.id or b.mate_id == a.id:
        prompt_text = (
            f"{a.name} and {b.name} are on patrol together. When {a.name} is injured and rival dragons can be heard approaching, "
            f"{b.name} must decide whether to stay with their mate or run for help."
        )
    elif ("saved_by", b.id) in a.memory_flags:
        prompt_text = (
            f"{a.name} and {b.name} are on patrol. {a.name} is injured again, and rival dragons can be heard approaching. "
            f"{a.name} still remembers that {b.name} once stayed when it mattered. What should {b.name} do now?"
        )
    elif ("abandoned_by", b.id) in a.memory_flags:
        prompt_text = (
            f"{a.name} and {b.name} are on patrol. {a.name} is injured, and rival dragons can be heard approaching. "
            f"{a.name} has never forgotten the last time {b.name} left. What should {b.name} do now?"
        )
    else:
        if mood in {"Volatile", "Crisis"}:
            prompt_text = (
                f"{a.name} and {b.name} are on patrol in a tribe already on edge. {a.name} is injured, and "
                f"rival dragons can be heard approaching through the darkness. What should {b.name} do?"
            )
        elif climate["recovery_bias"] > 0.20:
            prompt_text = (
                f"{a.name} and {b.name} are on patrol. {a.name} is injured, and rival dragons can be heard approaching. "
                f"In a tribe that still seems to hold together, what should {b.name} do?"
            )
        else:
            prompt_text = (
                f"{a.name} and {b.name} are on patrol. {a.name} is injured, and "
                f"rival dragons can be heard approaching. What should {b.name} do?"
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
    living = get_living_dragons(world)

    rival_pairs = []
    weights = []

    for dragon in living:
        for rival_id in dragon.rivals:
            rival = next((d for d in living if d.id == rival_id), None)
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
    leader = getattr(world, "leader", None)

    if not leader or leader.status != "Alive":
        return False

    climate = get_tribe_climate(world)

    # low chance — this should feel occasional, not spammy
    if random.random() > 0.15:
        return False

    texts = []

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

    # fallback if no traits exist
    if not texts:
        texts.append(f"{name} oversaw the tribe this moon.")

    text = random.choice(texts)

    log_event(
        world,
        text,
        involved_ids=[leader.id],
        event_type="leader_event",
        importance=2
    )

    return True

def create_leader_decision(world):
    leader = getattr(world, "leader", None)

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


def advance_moon(world: World):
    if world.pending_choice is not None:
        return False

    if getattr(world, "direction_timer", 0) > 0:
        world.direction_timer -= 1
        if world.direction_timer <= 0:
            world.direction = None

    world.moon += 1
    living = get_living_dragons(world)

    for dragon in living:
        tick_dragon_progression(world, dragon, living)
        handle_possible_death(world, dragon)

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
        


    run_event_phase(world)
    try_leader_event(world)

    for dragon in world.dragons:
        for k in list(dragon.trust.keys()):
            dragon.trust[k] *= 0.95
            if dragon.trust[k] < 0.1:
                del dragon.trust[k]

        for k in list(dragon.resentment.keys()):
            dragon.resentment[k] *= 0.95
            if dragon.resentment[k] < 0.1:
                del dragon.resentment[k]

    world.tension = max(0.0, min(5.0, world.tension))

    world.event_log = world.event_log[-100:]
    return True