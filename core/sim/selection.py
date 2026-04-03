import random


def choose_friendship_pair(living):
    pairs = []

    for i in range(len(living)):
        for j in range(i + 1, len(living)):
            a = living[i]
            b = living[j]
            pairs.append((a, b))

    if not pairs:
        return None, None

    weights = [friendship_weight(a, b) for a, b in pairs]
    return random.choices(pairs, weights=weights, k=1)[0]


def choose_rivalry_pair(living):
    pairs = []

    for i in range(len(living)):
        for j in range(i + 1, len(living)):
            a = living[i]
            b = living[j]
            pairs.append((a, b))

    if not pairs:
        return None, None

    weights = [rivalry_weight(a, b) for a, b in pairs]
    return random.choices(pairs, weights=weights, k=1)[0]


def choose_injury_dragon(living):
    if not living:
        return None

    weights = [injury_weight(d) for d in living]
    return random.choices(living, weights=weights, k=1)[0]


# -------- weights --------

def friendship_weight(a, b):
    weight = 1.0

    friendly_traits = {"Kind", "Loyal", "Playful"}
    difficult_traits = {"Suspicious", "Moody", "Ambitious"}

    if a.personality in friendly_traits:
        weight += 0.4
    if b.personality in friendly_traits:
        weight += 0.4

    if a.personality in difficult_traits:
        weight -= 0.25
    if b.personality in difficult_traits:
        weight -= 0.25

    if set(a.parents) & set(b.parents):
        weight += 0.6

    return max(0.2, weight)


def rivalry_weight(a, b):
    weight = 1.0

    rivalry_traits = {"Ambitious", "Moody", "Suspicious"}

    if a.personality in rivalry_traits:
        weight += 0.4
    if b.personality in rivalry_traits:
        weight += 0.4

    if a.role == "Warrior":
        weight += 0.2
    if b.role == "Warrior":
        weight += 0.2

    if a.role == "Dragonet":
        weight -= 0.6
    if b.role == "Dragonet":
        weight -= 0.6

    if set(a.parents) & set(b.parents):
        weight -= 0.5

    return max(0.1, weight)


def injury_weight(dragon):
    weight = 1.0

    if dragon.personality == "Brave":
        weight += 0.5
    elif dragon.personality == "Clever":
        weight -= 0.2

    if dragon.role == "Hunter":
        weight += 0.35
    elif dragon.role == "Scout":
        weight += 0.25
    elif dragon.role == "Healer":
        weight -= 0.25
    elif dragon.role == "Dragonet":
        weight -= 0.40

    return max(0.2, weight)