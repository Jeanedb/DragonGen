import random
from core.world import World
from core.generator import generate_dragonet
from core.sim.logging import log_event
from core.sim.progression import tick_dragon_progression
from core.sim.events import run_event_phase
from core.sim.titles import evaluate_world_titles
from core.sim.consequences import process_scheduled_events
from core.sim.world_state import (
    get_living_dragons,
    get_world_mood,
    get_tribe_climate,
)
from core.sim.choice_generation.personal import (
    create_injured_patrol_choice,
    create_rival_confrontation_choice,
)
from core.sim.choice_generation.leadership import (
    try_leader_event,
    create_leader_decision,
)
from core.sim.choice_generation.diplomacy import (
    create_diplomatic_choice,
    create_tribal_policy_choice,
    create_incoming_diplomacy_choice,
)
from core.sim.choice_generation.border import (
    create_border_sighting_event,
    create_border_violation_event,
    create_aid_delivery_event,
)
from core.sim.politics import (
    run_politics_phase,
    drift_relations,
    clamp_relations,
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


# ---------- PLAYER CHOICES ----------


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

    process_scheduled_events(world)

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