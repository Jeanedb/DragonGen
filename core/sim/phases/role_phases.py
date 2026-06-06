import random
from core.sim.logging import log_event


def living_adults(world, role=None):
    dragons = [
        d for d in world.dragons
        if d.status == "Alive"
        and d.role != "Dragonet"
        and d.health == "Healthy"
    ]

    if role:
        dragons = [d for d in dragons if d.role == role]

    return dragons


def run_role_phase(world):
    try_hunter_role(world)
    try_scout_role(world)
    try_warrior_role(world)
    try_elder_role(world)


def try_hunter_role(world):
    hunters = living_adults(world, "Hunter")

    if not hunters or random.random() > 0.35:
        return False

    hunter = random.choice(hunters)

    world.tension = max(0, world.tension - 0.03)
    hunter.hardship_survived += 1
    hunter.reputation["reliable"] += 0.1

    log_event(
        world,
        f"{hunter.name} returned from the hunting grounds with enough food to ease pressure on the tribe.",
        involved_ids=[hunter.id],
        event_type="hunter_success",
        importance=2,
        cause="Hunter role duty",
    )

    return True


def try_scout_role(world):
    scouts = living_adults(world, "Scout")

    if not scouts or random.random() > 0.30:
        return False

    scout = random.choice(scouts)

    scout.watchful_actions += 1

    if world.tension > 1:
        world.tension = max(0, world.tension - 0.04)

    log_event(
        world,
        f"{scout.name} patrolled the border routes and spotted trouble before it reached the village.",
        involved_ids=[scout.id],
        event_type="scout_patrol",
        importance=2,
        cause="Scout role duty",
    )

    return True


def try_warrior_role(world):
    warriors = living_adults(world, "Warrior")

    if not warriors or random.random() > 0.30:
        return False

    warrior = random.choice(warriors)

    old_skill = warrior.combat_skill
    warrior.combat_skill += 1

    log_event(
        world,
        f"{warrior.name} trained hard at the training grounds, improving their combat skill from {old_skill} to {warrior.combat_skill}.",
        involved_ids=[warrior.id],
        event_type="warrior_training",
        importance=2,
        cause="Warrior role duty",
    )

    return True


def try_elder_role(world):
    elders = living_adults(world, "Elder")

    if not elders or random.random() > 0.25:
        return False

    elder = random.choice(elders)

    world.tension = max(0, world.tension - 0.05)
    elder.reputation["reliable"] += 0.1

    log_event(
        world,
        f"{elder.name} shared old wisdom at the scroll library, helping steady the tribe.",
        involved_ids=[elder.id],
        event_type="elder_guidance",
        importance=2,
        cause="Elder role duty",
    )

    return True