from core.sim.logging import log_event


def grant_dragon_title(world, dragon, title, reason_text=None):
    if title in dragon.earned_titles:
        return False

    dragon.earned_titles.append(title)

    text = reason_text or f"{dragon.name} has earned the title '{title}'."
    log_event(
        world,
        text,
        involved_ids=[dragon.id],
        event_type="title_gain",
        importance=4
    )
    return True


def grant_tribe_title(world, title, reason_text=None):
    if title in world.tribe_titles:
        return False

    world.tribe_titles.append(title)

    text = reason_text or f"The tribe has become known as '{title}'."
    log_event(
        world,
        text,
        involved_ids=[],
        event_type="tribe_title_gain",
        importance=5
    )
    return True


def evaluate_dragon_titles(world, dragon):
    if dragon.combat_wins >= 5:
        grant_dragon_title(
            world,
            dragon,
            "The Harbinger",
            f"After repeated victories, {dragon.name} is beginning to be known as 'The Harbinger'."
        )

    if dragon.hardship_survived >= 2 and dragon.combat_wins >= 1:
        grant_dragon_title(
            world,
            dragon,
            "The Survivor",
            f"{dragon.name} has endured hardship and returned stronger, earning the name 'The Survivor'."
        )

    abandoned_flags = [flag for flag, other_id in dragon.memory_flags if flag == "abandoned_by"]
    if abandoned_flags and dragon.hardship_survived >= 1:
        grant_dragon_title(
            world,
            dragon,
            "The Betrayed",
            f"Others now speak of {dragon.name} as 'The Betrayed', a dragon shaped by an old abandonment."
        )

    if dragon.peace_actions >= 3:
        grant_dragon_title(
            world,
            dragon,
            "The Peacemaker",
            f"Through repeated restraint and steadiness, {dragon.name} has earned the title 'The Peacemaker'."
        )

    if dragon.watchful_actions >= 3:
        grant_dragon_title(
            world,
            dragon,
            "The Watchful",
            f"Years of caution and vigilance have caused others to know {dragon.name} as 'The Watchful'."
        )


def update_world_title_flags(world):
    direction = getattr(world, "direction", None)
    tension = getattr(world, "tension", 0.0)

    friendly_relations = 0
    hostile_relations = 0

    for score in getattr(world, "tribal_relations", {}).values():
        if score >= 10:
            friendly_relations += 1
        elif score <= -10:
            hostile_relations += 1

    if tension < 1.5 and hostile_relations == 0 and friendly_relations >= 2:
        world.world_flags["peace_streak"] = world.world_flags.get("peace_streak", 0) + 1
    else:
        world.world_flags["peace_streak"] = 0

    if direction == "watchful":
        world.world_flags["watchful_streak"] = world.world_flags.get("watchful_streak", 0) + 1
    else:
        world.world_flags["watchful_streak"] = 0

    if tension >= 2.5 or hostile_relations >= 2:
        world.world_flags["warlike_streak"] = world.world_flags.get("warlike_streak", 0) + 1
    else:
        world.world_flags["warlike_streak"] = 0


def evaluate_tribe_titles(world):
    peace_streak = world.world_flags.get("peace_streak", 0)
    watchful_streak = world.world_flags.get("watchful_streak", 0)
    warlike_streak = world.world_flags.get("warlike_streak", 0)

    if peace_streak >= 6:
        grant_tribe_title(
            world,
            "Peacekeepers",
            "After many moons of restraint and stability, the tribe has begun to be known as the Peacekeepers."
        )

    if watchful_streak >= 6:
        grant_tribe_title(
            world,
            "Watchful Tribe",
            "Long seasons of suspicion and vigilance have made the tribe known as the Watchful Tribe."
        )

    if warlike_streak >= 6:
        grant_tribe_title(
            world,
            "Blooded Tribe",
            "After moons shaped by conflict, the tribe has come to be known as the Blooded Tribe."
        )


def evaluate_world_titles(world):
    update_world_title_flags(world)

    for dragon in world.dragons:
        if dragon.status != "Alive":
            continue
        evaluate_dragon_titles(world, dragon)

    evaluate_tribe_titles(world)