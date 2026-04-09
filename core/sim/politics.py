import random
from data.tribes import TRIBES
from core.sim.logging import log_event


def run_politics_phase(world):

    if not world.tribal_relations:
        return False

    if random.random() > 0.35:
        return False

    tribe = random.choice(list(world.tribal_relations.keys()))
    roll = random.random()

    if roll < 0.35:
        shift_relation(world, tribe, -4)
        log_event(
            world,
            f"Tension rose with the {tribe}s after a minor border dispute.",
            event_type="politics",
            importance=2
        )

        incident_text = "Border dispute"

        if tribe not in world.tribal_incidents:
            world.tribal_incidents[tribe] = []

        world.tribal_incidents[tribe].append(incident_text)
        world.tribal_incidents[tribe] = world.tribal_incidents[tribe][-5:]


    elif roll < 0.70:
        shift_relation(world, tribe, +3)
        log_event(
            world,
            f"Relations with the {tribe}s improved after a peaceful exchange.",
            event_type="politics",
            importance=2
        )

        incident_text = "Peaceful exchange"

        if tribe not in world.tribal_incidents:
            world.tribal_incidents[tribe] = []

        world.tribal_incidents[tribe].append(incident_text)
        world.tribal_incidents[tribe] = world.tribal_incidents[tribe][-5:]


    else:
        shift_relation(world, tribe, -2)
        log_event(
            world,
            f"Trust with the {tribe}s weakened slightly after a suspicious encounter.",
            event_type="politics",
            importance=1,
        )

        incident_text = "Suspicious encounter"

        if tribe not in world.tribal_incidents:
            world.tribal_incidents[tribe] = []

        world.tribal_incidents[tribe].append(incident_text)
        world.tribal_incidents[tribe] = world.tribal_incidents[tribe][-5:]



    return True


def initialize_tribal_relations(world, player_tribe: str | None = None):
    """
    Creates starting relation values between the player's tribe
    and all other tribes.

    Relation scale:
    -100 = total war
    -60  = hostile
    -20  = uneasy
      0  = neutral
     20  = friendly
     60  = allied
    100  = extremely close / rare
    """
    relations = {}

    for tribe in TRIBES:
        if player_tribe and tribe == player_tribe:
            continue
        relations[tribe] = random.randint(-20, 20)

    world.tribal_relations = relations


def get_relation_status(score: int) -> str:
    if score <= -75:
        return "War"
    elif score <= -40:
        return "Hostile"
    elif score <= -10:
        return "Uneasy"
    elif score < 10:
        return "Neutral"
    elif score < 40:
        return "Friendly"
    else:
        return "Allied"


def clamp_relations(world):
    for tribe, score in world.tribal_relations.items():
        world.tribal_relations[tribe] = max(-100, min(100, score))


def shift_relation(world, tribe: str, amount: int):
    if tribe not in world.tribal_relations:
        world.tribal_relations[tribe] = 0

    world.tribal_relations[tribe] += amount
    world.tribal_relations[tribe] = max(-100, min(100, world.tribal_relations[tribe]))


def drift_relations(world):
    for tribe, score in world.tribal_relations.items():
        if random.random() < 0.25:
            if score > 0:
                world.tribal_relations[tribe] -= 1
            elif score < 0:
                world.tribal_relations[tribe] += 1