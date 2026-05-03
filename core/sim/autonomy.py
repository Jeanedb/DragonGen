import random
from core.sim.logging import log_event

MIN_AUTONOMY_POOL = 2


def _living_non_self(dragon, living):
    return [d for d in living if d.id != dragon.id and d.status == "Alive"]


def _relationship_pressure(actor, target):
    perceived = actor.perceived_reputation.get(target.id, 0)
    trust = actor.trust.get(target.id, 0)
    resentment = actor.resentment.get(target.id, 0)

    return {
        "friendly_pull": max(0.0, perceived) + trust,
        "hostile_pull": max(0.0, -perceived) + resentment,
    }


def _personality_bias(actor):
    personality = getattr(actor, "personality", "Neutral")

    return {
        "Kind": {"seek": 1.25, "avoid": 0.85, "confront": 0.75},
        "Loyal": {"seek": 1.15, "avoid": 0.90, "confront": 0.90},
        "Suspicious": {"seek": 0.85, "avoid": 1.35, "confront": 1.10},
        "Ambitious": {"seek": 0.95, "avoid": 0.90, "confront": 1.25},
        "Moody": {"seek": 0.90, "avoid": 1.10, "confront": 1.25},
        "Clever": {"seek": 1.00, "avoid": 1.15, "confront": 0.90},
    }.get(personality, {"seek": 1.0, "avoid": 1.0, "confront": 1.0})


def _score_actions(actor, target):
    pressure = _relationship_pressure(actor, target)
    bias = _personality_bias(actor)

    actions = []

    seek = pressure["friendly_pull"] * bias["seek"]
    avoid = pressure["hostile_pull"] * bias["avoid"]
    confront = pressure["hostile_pull"] * bias["confront"]

    if seek >= 1.2:
        actions.append(("seek", actor, target, seek))

    if avoid >= 1.4:
        actions.append(("avoid", actor, target, avoid))

    if confront >= 2.0:
        actions.append(("confront", actor, target, confront))

    return actions


def _build_pool(living):
    pool = []

    for actor in living:
        if actor.role == "Dragonet":
            continue

        for target in _living_non_self(actor, living):
            if target.role == "Dragonet":
                continue

            pool.extend(_score_actions(actor, target))

    return pool


def try_autonomous_social_behavior(world, living):
    if len(living) < MIN_AUTONOMY_POOL:
        return False

    pool = _build_pool(living)

    if not pool:
        return False

    actions = [(a, b, c) for a, b, c, _ in pool]
    weights = [w for _, _, _, w in pool]

    action, actor, target = random.choices(actions, weights=weights, k=1)[0]

    if action == "seek":
        return _seek(world, actor, target)

    if action == "avoid":
        return _avoid(world, actor, target)

    if action == "confront":
        return _confront(world, actor, target)

    return False


def _seek(world, a, b):
    a.trust[b.id] = a.trust.get(b.id, 0) + 0.4
    world.tension = max(0.0, world.tension - 0.03)

    log_event(
        world,
        f"{a.name} chose to spend time near {b.name}, drawn by growing trust.",
        [a.id, b.id],
        event_type="autonomous_seek",
        importance=2,
    )
    return True


def _avoid(world, a, b):
    a.resentment[b.id] = a.resentment.get(b.id, 0) + 0.25
    world.tension += 0.02

    log_event(
        world,
        f"{a.name} avoided {b.name}, keeping their distance.",
        [a.id, b.id],
        event_type="autonomous_avoid",
        importance=2,
    )
    return True


def _confront(world, a, b):
    a.resentment[b.id] = a.resentment.get(b.id, 0) + 0.5
    b.resentment[a.id] = b.resentment.get(a.id, 0) + 0.25
    world.tension += 0.06

    if b.id not in a.rivals and a.resentment.get(b.id, 0) >= 3:
        a.rivals.append(b.id)

    log_event(
        world,
        f"{a.name} confronted {b.name}, unable to ignore their distrust any longer.",
        [a.id, b.id],
        event_type="autonomous_confront",
        importance=3,
    )
    return True