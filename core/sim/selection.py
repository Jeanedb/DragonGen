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

    if ("saved_by", b.id) in a.memory_flags:
        weight += 0.6
    if ("saved_by", a.id) in b.memory_flags:
        weight += 0.6

    weight += a.trust.get(b.id, 0) * 0.25
    weight += b.trust.get(a.id, 0) * 0.25

    weight -= a.resentment.get(b.id, 0) * 0.30
    weight -= b.resentment.get(a.id, 0) * 0.30

    if a.mate_id == b.id or b.mate_id == a.id:
        weight += 1.5

    if any(flag == "lost_mate" for flag, _ in a.memory_flags):
        weight -= 0.15
    if any(flag == "lost_mate" for flag, _ in b.memory_flags):
        weight -= 0.15

    return max(0.2, weight)


def rivalry_weight(a, b):
    weight = 0.6

    rivalry_traits = {"Ambitious", "Moody", "Suspicious"}

    if a.personality in rivalry_traits:
        weight += 0.20
    if b.personality in rivalry_traits:
        weight += 0.20

    if a.role == "Warrior":
        weight += 0.10
    if b.role == "Warrior":
        weight += 0.10

    if a.role == "Dragonet":
        weight -= 0.30
    if b.role == "Dragonet":
        weight -= 0.30

    # direct family or shared parents should strongly suppress rivalry
    if a.id in b.parents or b.id in a.parents:
        weight -= 0.60
    if set(a.parents) & set(b.parents):
        weight -= 0.45

    # if already rivals, reduce repeated selection a bit
    if b.id in a.rivals or a.id in b.rivals:
        weight -= 0.15

    if ("abandoned_by", b.id) in a.memory_flags:
        weight += 0.8
    if ("abandoned_by", a.id) in b.memory_flags:
        weight += 0.8

    weight += a.resentment.get(b.id, 0) * 0.30
    weight += b.resentment.get(a.id, 0) * 0.30

    weight -= a.trust.get(b.id, 0) * 0.20
    weight -= b.trust.get(a.id, 0) * 0.20

    if a.mate_id == b.id or b.mate_id == a.id:
        weight -= 2.0

    if any(flag == "lost_mate" for flag, _ in a.memory_flags):
        weight += 0.12
    if any(flag == "lost_mate" for flag, _ in b.memory_flags):
        weight += 0.12

    return max(0.05, weight)


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