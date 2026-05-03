import random
from core.sim.logging import log_event


def can_become_mates(a, b):
    if a.id == b.id:
        return False

    if a.status != "Alive" or b.status != "Alive":
        return False

    if a.role == "Dragonet" or b.role == "Dragonet":
        return False

    if a.mate_id is not None or b.mate_id is not None:
        return False

    # direct parent/child
    if a.id in b.parents or b.id in a.parents:
        return False

    # shared parents / siblings
    if set(a.parents) & set(b.parents):
        return False

    return True


def mate_weight(a, b):
    if not can_become_mates(a, b):
        return 0.0

    weight = 0.03

    # existing friendship helps
    if b.id in a.friends or a.id in b.friends:
        weight += 0.6

    # trust matters a lot
    weight += a.trust.get(b.id, 0) * 0.25
    weight += b.trust.get(a.id, 0) * 0.25

    # resentment suppresses bonding
    weight -= a.resentment.get(b.id, 0) * 0.35
    weight -= b.resentment.get(a.id, 0) * 0.35

    # some personalities are a bit better at pair bonding
    bonding_traits = {"Kind", "Loyal", "Playful"}
    difficult_traits = {"Suspicious", "Moody"}

    if a.personality in bonding_traits:
        weight += 0.15
    if b.personality in bonding_traits:
        weight += 0.15

    if a.personality in difficult_traits:
        weight -= 0.10
    if b.personality in difficult_traits:
        weight -= 0.10

    return max(0.0, weight)


def choose_mate_pair(living):
    pairs = []

    for i in range(len(living)):
        for j in range(i + 1, len(living)):
            a = living[i]
            b = living[j]
            w = mate_weight(a, b)
            if w > 0:
                pairs.append((a, b, w))

    if not pairs:
        return None, None

    weighted_pairs = [(a, b) for a, b, _ in pairs]
    weights = [w for _, _, w in pairs]
    return random.choices(weighted_pairs, weights=weights, k=1)[0]


def add_mate_bond(world, a, b):
    if not can_become_mates(a, b):
        return False

    a.mate_id = b.id
    b.mate_id = a.id

    # strong trust bump
    a.trust[b.id] = a.trust.get(b.id, 0) + 3
    b.trust[a.id] = b.trust.get(a.id, 0) + 3

    # mates should not stay rivals
    if b.id in a.rivals:
        a.rivals.remove(b.id)
    if a.id in b.rivals:
        b.rivals.remove(a.id)

    # if not already friends, make them friends
    if b.id not in a.friends:
        a.friends.append(b.id)
    if a.id not in b.friends:
        b.friends.append(a.id)

    # calm the tribe a little
    if hasattr(world, "tension"):
        world.tension = max(0.0, world.tension - 0.09)

    log_event(
        world,
        f"{a.name} and {b.name} have formed a mate bond.",
        involved_ids=[a.id, b.id],
        event_type="mate_bond",
        importance=4,
    )

    return True


def try_mate_event(world, living):
    # low-frequency event
    a, b = choose_mate_pair(living)
    if not a or not b:
        return False

    return add_mate_bond(world, a, b)

def add_mate_event(world, a, b):
    texts = [
        f"{a.name} and {b.name} spent quiet time together, strengthening their bond.",
        f"{a.name} stayed close to {b.name}, and the two seemed steadier for it.",
        f"In the {world.tribe_name}, {a.name} and {b.name} shared a rare peaceful moment together.",
        f"{a.name} and {b.name} found comfort in each other's company this moon."
    ]
    text = random.choice(texts)

    # small trust reinforcement
    a.trust[b.id] = a.trust.get(b.id, 0) + 0.5
    b.trust[a.id] = b.trust.get(a.id, 0) + 0.5

    # small calming effect
    if hasattr(world, "tension"):
        world.tension = max(0.0, world.tension - 0.04)

    log_event(
        world,
        text,
        involved_ids=[a.id, b.id],
        event_type="mate_event",
        importance=2,
    )
    return True


def try_mate_bond_event(world, living):
    mate_pairs = []
    seen_pairs = set()

    for d in living:
        if d.mate_id is None:
            continue

        mate = next((x for x in living if x.id == d.mate_id), None)
        if not mate:
            continue

        pair_key = tuple(sorted((d.id, mate.id)))
        if pair_key in seen_pairs:
            continue

        seen_pairs.add(pair_key)

        weight = 1.0
        weight += d.trust.get(mate.id, 0) * 0.08
        weight += mate.trust.get(d.id, 0) * 0.08

        mate_pairs.append((d, mate, weight))

    if not mate_pairs:
        return False

    pair_choices = [(a, b) for a, b, _ in mate_pairs]
    pair_weights = [w for _, _, w in mate_pairs]
    a, b = random.choices(pair_choices, weights=pair_weights, k=1)[0]

    return add_mate_event(world, a, b)