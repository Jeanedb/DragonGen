from core.world import World
import random
from core.sim.logging import log_event

def try_recovery_visit_event(world: World, injured):
    if injured.status != "Alive":
        return False

    if injured.health != "Injured":
        return False

    visitors = []

    # Mate gets priority
    if injured.mate_id is not None:
        mate = next(
            (
                d for d in world.dragons
                if d.id == injured.mate_id
                and d.status == "Alive"
                and d.health == "Healthy"
            ),
            None
        )
        if mate:
            visitors.append(mate)

    # Close friends can visit too
    for friend_id in injured.friends:
        friend = next(
            (
                d for d in world.dragons
                if d.id == friend_id
                and d.status == "Alive"
                and d.health == "Healthy"
            ),
            None
        )
        if friend and friend not in visitors:
            visitors.append(friend)

    if not visitors:
        return False

    # Not every injured dragon gets a visit every moon
    if random.random() > 0.35:
        return False

    visitor = random.choice(visitors)

    injured.trust[visitor.id] = injured.trust.get(visitor.id, 0) + 0.3
    visitor.trust[injured.id] = visitor.trust.get(injured.id, 0) + 0.2

    texts = [
        f"{visitor.name} visited {injured.name} in the Healer's Den.",
        f"{visitor.name} spent part of the moon beside {injured.name} while they recovered.",
        f"While {injured.name} recovered from their injuries, {visitor.name} stayed close.",
    ]

    log_event(
        world,
        random.choice(texts),
        involved_ids=[visitor.id, injured.id],
        event_type="recovery_visit",
        importance=2,
        cause="A close bond drew someone to the Healer's Den",
    )

    return True


def try_recovery_neglect_event(world: World, injured):
    if random.random() > 0.20:
        return False

    texts = [
        f"{injured.name} spent the moon recovering alone in the Healer's Den.",
        f"No one came to sit with {injured.name} while they recovered.",
        f"{injured.name} seemed quieter after another lonely moon in recovery.",
    ]

    injured.resentment[0] = injured.resentment.get(0, 0) + 0.2

    log_event(
        world,
        random.choice(texts),
        involved_ids=[injured.id],
        event_type="recovery_neglect",
        importance=2,
        cause="No close visitor came during recovery",
    )

    return True


def try_injury_strain_event(world: World):
    injured = [
        d for d in world.dragons
        if d.status == "Alive" and d.health == "Injured"
    ]

    injured_count = len(injured)

    # Ignore tiny injury counts
    if injured_count < 3:
        return False

    # Prevent spam every moon
    if random.random() > 0.25:
        return False

    texts = [
        f"With several dragons recovering in the Healer's Den, patrol coverage has begun to thin.",
        f"The growing number of injured dragons has started straining the tribe's daily duties.",
        f"Too many dragons remain injured, and the tribe is beginning to feel the pressure.",
        f"The Healer's Den has grown crowded, leaving fewer healthy dragons available for patrols and work.",
    ]

    world.tension += 0.10

    log_event(
        world,
        random.choice(texts),
        involved_ids=[d.id for d in injured],
        event_type="injury_strain",
        importance=3,
        cause="Too many dragons are unavailable due to injuries",
    )

    return True
