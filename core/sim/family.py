import random
from core.sim.logging import log_event


def add_family_bond_event(world, a, b):
    texts = [
        f"{a.name} and {b.name} spent time together as kin and grew closer.",
        f"{a.name} and {b.name}, bound by family, supported each other this moon.",
    ]
    text = random.choice(texts)
    log_event(world, text, involved_ids=[a.id, b.id], event_type="family_bond")
    return True


def add_parent_child_event(world, parent, child):
    texts = [
        f"{parent.name} guided {child.name} through the challenges of the moon.",
        f"{parent.name} kept a close watch over {child.name}.",
    ]
    text = random.choice(texts)
    log_event(world, text, involved_ids=[parent.id, child.id], event_type="parent_child")
    return True


def add_family_conflict_event(world, a, b):
    texts = [
        f"{a.name} and {b.name} argued despite their shared blood.",
        f"Tension rose between {a.name} and {b.name}, even as family.",
    ]
    text = random.choice(texts)
    log_event(world, text, involved_ids=[a.id, b.id], event_type="family_conflict")
    return True


def try_family_event(world, living):
    from core.simulation import are_family  # temporary dependency

    family_pairs = []

    for i in range(len(living)):
        for j in range(i + 1, len(living)):
            a = living[i]
            b = living[j]

            if are_family(a, b):
                family_pairs.append((a, b))

    if not family_pairs:
        return False

    a, b = random.choice(family_pairs)
    roll = random.random()

    if a.id in b.parents:
        parent, child = a, b
    elif b.id in a.parents:
        parent, child = b, a
    else:
        parent, child = None, None

    if parent and child:
        return add_parent_child_event(world, parent, child)
    elif roll < 0.7:
        return add_family_bond_event(world, a, b)
    else:
        return add_family_conflict_event(world, a, b)