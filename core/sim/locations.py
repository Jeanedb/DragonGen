import random


LOCATION_NAMES = {
    "village_center": "The Village Center",
    "queen_palace": "The Queen's Palace",
    "healer_den": "The Healer's Den",
    "training_grounds": "The Training Grounds",
    "hunting_grounds": "The Hunting Grounds",
    "border_routes": "The Border Routes",
    "scroll_library": "The Scroll Library",
    "hatchery": "The Hatchery",
}


ROLE_LOCATION_BIAS = {
    "Healer": ["healer_den", "village_center"],
    "Warrior": ["training_grounds", "border_routes"],
    "Scout": ["border_routes", "hunting_grounds"],
    "Hunter": ["hunting_grounds", "border_routes"],
    "Dragonet": ["hatchery", "village_center"],
    "Elder": ["scroll_library", "village_center"],
}


def try_healer_den_event(world):
    import random
    from core.sim.logging import log_event

    candidates = [
        d for d in world.dragons
        if d.status == "Alive"
        and d.role != "Healer"
    ]

    if not candidates:
        return False

    # Prefer dragons already at healer_den, but allow others to visit
    at_den = [d for d in candidates if d.location == "healer_den"]

    if at_den and random.random() < 0.75:
        dragon = random.choice(at_den)
    else:
        dragon = random.choice(candidates)
        dragon.location = "healer_den"

    if not candidates:
        return False

    if random.random() > 0.15:
        return False

    healers = [
        d for d in world.dragons
        if d.role == "Healer" and d.status == "Alive"
    ]

    if not healers:
        return False

    healer = random.choice(healers)

    # effect
    dragon.trust[healer.id] = dragon.trust.get(healer.id, 0) + 1

    log_event(
        world,
        f"{dragon.name} quietly sought guidance at the Healer's Den. {healer.name} offered support.",
        involved_ids=[dragon.id, healer.id],
        event_type="healer_den_visit",
        importance=2,
    )

    return True


def try_training_grounds_event(world):
    import random
    from core.sim.logging import log_event

    candidates = [
        d for d in world.dragons
        if d.status == "Alive"
        and d.role != "Dragonet"
    ]

    if len(candidates) < 2:
        return False

    at_training = [
        d for d in candidates
        if d.location == "training_grounds"
    ]

    if len(at_training) >= 2 and random.random() < 0.75:
        a, b = random.sample(at_training, 2)
    else:
        a, b = random.sample(candidates, 2)
        a.location = "training_grounds"
        b.location = "training_grounds"

    # More likely to be serious if warriors are involved
    intensity = 1.0
    if a.role == "Warrior":
        intensity += 0.4
    if b.role == "Warrior":
        intensity += 0.4

    if random.random() < 0.65:
        # Respectful sparring
        a.trust[b.id] = a.trust.get(b.id, 0) + 0.4
        b.trust[a.id] = b.trust.get(a.id, 0) + 0.4

        log_event(
            world,
            f"{a.name} and {b.name} sparred at the training grounds, gaining respect for each other.",
            involved_ids=[a.id, b.id],
            event_type="training_spar",
            importance=2,
        )
        return True

    else:
        # Sparring turns tense
        a.resentment[b.id] = a.resentment.get(b.id, 0) + (0.3 * intensity)
        b.resentment[a.id] = b.resentment.get(a.id, 0) + (0.3 * intensity)
        world.tension += 0.03 * intensity

        log_event(
            world,
            f"{a.name} and {b.name}'s sparring at the training grounds turned sharper than expected.",
            involved_ids=[a.id, b.id],
            event_type="training_tension",
            importance=2,
        )
        return True


def try_queen_palace_event(world):
    import random
    from core.sim.logging import log_event

    candidates = [
        d for d in world.dragons
        if d.status == "Alive"
        and d.role != "Dragonet"
    ]

    if len(candidates) < 2:
        return False

    at_palace = [
        d for d in candidates
        if d.location == "queen_palace"
    ]

    dispute_pairs = []

    for a in candidates:
        for b in candidates:
            if a.id >= b.id:
                continue

            resentment_ab = a.resentment.get(b.id, 0)
            resentment_ba = b.resentment.get(a.id, 0)

            if resentment_ab >= 2 or resentment_ba >= 2:
                dispute_pairs.append((a, b, resentment_ab + resentment_ba))

    if dispute_pairs and random.random() < 0.70:
        pair_choices = [(a, b) for a, b, _ in dispute_pairs]
        pair_weights = [w for _, _, w in dispute_pairs]

        a, b = random.choices(pair_choices, weights=pair_weights, k=1)[0]
        a.location = "queen_palace"
        b.location = "queen_palace"

    elif len(at_palace) >= 2 and random.random() < 0.75:
        a, b = random.sample(at_palace, 2)

    else:
        a, b = random.sample(candidates, 2)
        a.location = "queen_palace"
        b.location = "queen_palace"

    leader = next(
        (d for d in world.dragons if d.id == getattr(world, "leader_id", None)),
        None
    )

    if not leader or leader.status != "Alive":
        return False

    if random.random() < 0.6:
        a.resentment[b.id] = max(0, a.resentment.get(b.id, 0) - 0.5)
        b.resentment[a.id] = max(0, b.resentment.get(a.id, 0) - 0.5)

        world.tension = max(0, world.tension - 0.1)

        log_event(
            world,
            f"{leader.name} mediated a dispute between {a.name} and {b.name} at the Queen's Palace.",
            involved_ids=[leader.id, a.id, b.id],
            event_type="palace_mediation",
            importance=3,
        )
        return True

    else:
        world.tension += 0.1

        favored = random.choice([a, b])
        other = b if favored == a else a

        favored.trust[leader.id] = favored.trust.get(leader.id, 0) + 0.5
        other.resentment[leader.id] = other.resentment.get(leader.id, 0) + 0.5

        log_event(
            world,
            f"{leader.name} ruled in favor of {favored.name} during a dispute at the Queen's Palace, leaving {other.name} dissatisfied.",
            involved_ids=[leader.id, a.id, b.id],
            event_type="palace_judgment",
            importance=3,
        )
        return True


def get_location_name(location_id):
    return LOCATION_NAMES.get(location_id, location_id.replace("_", " "))


def choose_location_for_dragon(world, dragon):
    locations = getattr(world, "locations", [])

    if not locations:
        return "village_center"

    # Leaders/deputies should spend more time at the Queen's Palace
    if getattr(world, "leader_id", None) == dragon.id:
        if "queen_palace" in locations and random.random() < 0.65:
            return "queen_palace"

    if getattr(dragon, "rank", None) in {"Leader", "Deputy", "Queen", "King"}:
        if "queen_palace" in locations and random.random() < 0.60:
            return "queen_palace"

    biased = ROLE_LOCATION_BIAS.get(dragon.role)

    if biased and random.random() < 0.70:
        valid = [loc for loc in biased if loc in locations]
        if valid:
            return random.choice(valid)

    return random.choice(locations)


def initialize_dragon_locations(world):
    for dragon in world.dragons:
        if not getattr(dragon, "location", None):
            dragon.location = choose_location_for_dragon(world, dragon)


def move_dragons_between_locations(world):
    for dragon in world.dragons:
        if dragon.status != "Alive":
            continue

        if random.random() < 0.40:
            dragon.location = choose_location_for_dragon(world, dragon)


def shared_location(a, b):
    return getattr(a, "location", None) == getattr(b, "location", None)


def get_event_location_text(*dragons):
    locations = [
        getattr(d, "location", None)
        for d in dragons
        if getattr(d, "location", None)
    ]

    if not locations:
        return ""

    first = locations[0]

    if all(loc == first for loc in locations):
        return f" at {get_location_name(first)}"

    return ""