import random
from core.sim.logging import log_event


def get_living_healers(world):
    return [
        d for d in world.dragons
        if d.status == "Alive"
        and d.role == "Healer"
    ]

def try_leader_influence_event(world):
    leader = next(
        (d for d in world.dragons if d.status == "Alive" and d.id == getattr(world, "leader_id", None)),
        None
    )

    if not leader:
        return False

    # Rare passive leadership moment
    if random.random() > 0.20:
        return False

    personality = getattr(leader, "personality", "Neutral")

    if personality in {"Kind", "Loyal"}:
        world.tension = max(0, world.tension - 0.12)

        for d in world.dragons:
            if d.status == "Alive" and d.id != leader.id:
                d.perceived_reputation[leader.id] = d.perceived_reputation.get(leader.id, 0) + 0.15

        log_event(
            world,
            f"{leader.name}'s steady leadership helped calm the tribe.",
            involved_ids=[leader.id],
            event_type="leader_stabilized_tribe",
            importance=3,
            cause="Leadership influence",
        )
        return True

    elif personality in {"Ambitious", "Suspicious", "Moody"}:
        world.tension += 0.12

        for d in world.dragons:
            if d.status == "Alive" and d.id != leader.id:
                d.perceived_reputation[leader.id] = d.perceived_reputation.get(leader.id, 0) - 0.10

        log_event(
            world,
            f"{leader.name}'s leadership left the tribe more tense and watchful.",
            involved_ids=[leader.id],
            event_type="leader_unsettled_tribe",
            importance=3,
            cause="Leadership influence",
        )
        return True

    return False

def try_healer_intervention(world, injured):
    if injured.status != "Alive":
        return False

    if injured.health != "Injured":
        return False

    healers = get_living_healers(world)

    if not healers:
        return False

    healer = random.choice(healers)

    if healer.id == injured.id:
        return False

    chance = 0.20

    if healer.trust.get(injured.id, 0) >= 2:
        chance += 0.20

    if healer.resentment.get(injured.id, 0) >= 2:
        chance -= 0.20

    chance = max(0.10, min(0.80, chance))

    if random.random() > chance:
        return False

    injured.health = "Healthy"
    healer.trust[injured.id] = healer.trust.get(injured.id, 0) + 0.3
    injured.trust[healer.id] = injured.trust.get(healer.id, 0) + 1.0

    if ("healed_by", healer.id) not in [m[:2] for m in injured.memory_flags]:
        injured.memory_flags.append(("healed_by", healer.id, world.moon))

    log_event(
        world,
        f"{healer.name} treated {injured.name}'s wounds, helping them recover.",
        involved_ids=[healer.id, injured.id],
        event_type="healer_intervention",
        importance=3,
        cause="A healer stepped into their role",
    )

    return True