import random

from core.sim.logging import log_event
from core.sim.leadership import get_leader_by_id


def try_leader_event(world):
    leader = get_leader_by_id(world)

    if not leader or leader.status != "Alive":
        return False

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
