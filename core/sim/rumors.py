import random


def spread_rumor(world, source_id, target_id, effect):
    for dragon in world.dragons:
        if dragon.id == source_id:
            continue

        if dragon.status != "Alive":
            continue

        if not hasattr(dragon, "perceived_reputation"):
            dragon.perceived_reputation = {}

        if random.random() < 0.4:
            current = dragon.perceived_reputation.get(target_id, 0)
            personality = getattr(dragon, "personality", "Neutral")

            modifier = 1.0

            if personality == "Suspicious":
                modifier = 1.5
            elif personality == "Loyal":
                modifier = 0.7
            elif personality == "Clever":
                modifier = 0.8
            elif personality == "Moody":
                modifier = 1.2

            distortion = random.uniform(0.8, 1.2)

            new_value = current + (effect * modifier * distortion)
            dragon.perceived_reputation[target_id] = new_value
