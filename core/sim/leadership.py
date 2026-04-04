import random
from core.sim.logging import log_event


def get_current_leader(world):
    for d in world.dragons:
        if d.status == "Alive" and d.rank == "Leader":
            return d
    return None


def get_current_deputy(world):
    for d in world.dragons:
        if d.status == "Alive" and d.rank == "Deputy":
            return d
    return None


def choose_leadership_candidate(world, exclude_ids=None):
    if exclude_ids is None:
        exclude_ids = []

    candidates = [
        d for d in world.dragons
        if d.status == "Alive"
        and d.role != "Dragonet"
        and d.id not in exclude_ids
    ]

    if not candidates:
        return None

    def candidate_weight(dragon):
        weight = 1.0

        if dragon.role in ["Warrior", "Scout", "Hunter"]:
            weight += 0.5
        if dragon.role == "Healer":
            weight -= 0.2
        if dragon.role == "Elder":
            weight -= 0.3

        if dragon.personality in ["Loyal", "Brave", "Clever", "Ambitious"]:
            weight += 0.4
        if dragon.personality == "Moody":
            weight -= 0.2

        return max(0.2, weight)

    weights = [candidate_weight(d) for d in candidates]
    return random.choices(candidates, weights=weights, k=1)[0]


def maintain_hierarchy(world):
    # Find current alive leader/deputy by rank
    leader = get_current_leader(world)
    deputy = get_current_deputy(world)

    # Fill leader vacancy
    if leader is None:
        if deputy is not None:
            deputy.rank = "Leader"
            log_event(
                world,
                f"{deputy.name} has become the new Leader of the tribe.",
                involved_ids=[deputy.id],
                event_type="leadership_change",
                importance=5
            )
            leader = deputy
            deputy = None
        else:
            new_leader = choose_leadership_candidate(world)
            if new_leader:
                new_leader.rank = "Leader"
                log_event(
                    world,
                    f"{new_leader.name} has been chosen as Leader of the tribe.",
                    involved_ids=[new_leader.id],
                    event_type="leadership_change",
                    importance=5
                )
                leader = new_leader

    # Re-scan deputy after any leader promotion
    deputy = get_current_deputy(world)

    # Fill deputy vacancy
    if deputy is None:
        exclude_ids = [leader.id] if leader else []
        new_deputy = choose_leadership_candidate(world, exclude_ids=exclude_ids)

        if new_deputy and new_deputy.rank != "Leader":
            new_deputy.rank = "Deputy"
            log_event(
                world,
                f"{new_deputy.name} has been appointed Deputy.",
                involved_ids=[new_deputy.id],
                event_type="leadership_change",
                importance=5
            )
            deputy = new_deputy

    # Final authoritative re-scan
    leader = get_current_leader(world)
    deputy = get_current_deputy(world)

    # Remove stale/duplicate leadership ranks from everyone else
    for dragon in world.dragons:
        if dragon.status != "Alive":
            continue

        if dragon == leader:
            dragon.rank = "Leader"
        elif dragon == deputy:
            dragon.rank = "Deputy"
        elif dragon.rank in ("Leader", "Deputy"):
            dragon.rank = "None"

    # Sync world pointers
    world.leader = leader
    world.deputy = deputy

def add_leader_event(world, leader):
    if leader.personality == "Loyal":
        texts = [
            f"{leader.name} reassured the tribe and kept everyone steady through the moon.",
            f"{leader.name} led with quiet consistency, helping the tribe hold together.",
        ]
    elif leader.personality == "Kind":
        texts = [
            f"{leader.name} took care to ease tensions and keep the tribe united.",
            f"{leader.name} guided the tribe with warmth, calming nerves through the moon.",
        ]
    elif leader.personality == "Clever":
        texts = [
            f"{leader.name} made a careful decision that helped the tribe avoid greater trouble.",
            f"{leader.name}'s planning kept the tribe steady through a difficult moon.",
        ]
    elif leader.personality == "Ambitious":
        texts = [
            f"{leader.name} pushed the tribe hard this moon, and not everyone welcomed it.",
            f"{leader.name}'s forceful direction drove the tribe forward, though tensions followed.",
        ]
    elif leader.personality == "Moody":
        texts = [
            f"{leader.name}'s shifting temper left the tribe uneasy this moon.",
            f"{leader.name} led through the moon, but their mood made the tribe hard to settle.",
        ]
    elif leader.personality == "Suspicious":
        texts = [
            f"{leader.name} watched the tribe closely, and their distrust put others on edge.",
            f"{leader.name}'s wary leadership made the tribe feel tense and guarded.",
        ]
    else:
        texts = [
            f"{leader.name}, leader of the tribe, made a decision that shaped the moon.",
            f"{leader.name} addressed the tribe, guiding them through the moon's challenges.",
            f"{leader.name} took charge during a tense moment in the tribe.",
        ]

    text = random.choice(texts)
    log_event(world, text, involved_ids=[leader.id], event_type="leader_event")
    return True


def add_deputy_event(world, deputy):
    texts = [
        f"{deputy.name}, the deputy, ensured order within the tribe.",
        f"{deputy.name} stepped in to support the leader during the moon.",
        f"{deputy.name} took responsibility and kept the tribe steady.",
    ]
    text = random.choice(texts)
    log_event(world, text, involved_ids=[deputy.id], event_type="deputy_event")
    return True


def try_leadership_event(world):
    leader = get_current_leader(world)
    deputy = get_current_deputy(world)

    roll = random.random()

    if leader and roll < 0.7:
        return add_leader_event(world, leader)
    elif deputy:
        return add_deputy_event(world, deputy)

    return False

def apply_leader_influence(world):
    leader = get_current_leader(world)
    if not leader or not hasattr(world, "tension"):
        return

    if leader.personality == "Loyal":
        world.tension = max(0.0, world.tension - 0.06)
    elif leader.personality == "Kind":
        world.tension = max(0.0, world.tension - 0.07)
    elif leader.personality == "Clever":
        world.tension = max(0.0, world.tension - 0.04)
    elif leader.personality == "Ambitious":
        world.tension = min(5.0, world.tension + 0.06)
    elif leader.personality == "Moody":
        world.tension = min(5.0, world.tension + 0.07)
    elif leader.personality == "Suspicious":
        world.tension = min(5.0, world.tension + 0.05)