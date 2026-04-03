from core.sim.logging import log_event


def add_friendship(world, d1, d2):
    if d2.id not in d1.friends:
        d1.friends.append(d2.id)
    if d1.id not in d2.friends:
        d2.friends.append(d1.id)

    if d2.id in d1.rivals:
        d1.rivals.remove(d2.id)
    if d1.id in d2.rivals:
        d2.rivals.remove(d1.id)

    d1.trust[d2.id] = d1.trust.get(d2.id, 0) + 1
    d2.trust[d1.id] = d2.trust.get(d1.id, 0) + 1

    log_event(
        world,
        f"{d1.name} and {d2.name} have become friends.",
        [d1.id, d2.id],
        event_type="friendship",
        importance=2,
)


def add_rivalry(world, d1, d2):
    if d2.id not in d1.rivals:
        d1.rivals.append(d2.id)
    if d1.id not in d2.rivals:
        d2.rivals.append(d1.id)

    if d2.id in d1.friends:
        d1.friends.remove(d2.id)
    if d1.id in d2.friends:
        d2.friends.remove(d1.id)

    d1.resentment[d2.id] = d1.resentment.get(d2.id, 0) + 1
    d2.resentment[d1.id] = d2.resentment.get(d1.id, 0) + 1

    log_event(
        world,
        f"Tension grows between {d1.name} and {d2.name}; they are now rivals.",
        [d1.id, d2.id],
        event_type="rivalry",
        importance=2,
    )