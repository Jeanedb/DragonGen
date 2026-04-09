import random
from data.tribes import TRIBES


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
    """
    Small natural drift toward center so relations do not stay extreme forever
    unless events keep pushing them.
    """
    for tribe, score in world.tribal_relations.items():
        if score > 0:
            world.tribal_relations[tribe] -= 1
        elif score < 0:
            world.tribal_relations[tribe] += 1