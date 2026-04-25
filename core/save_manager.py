import json
from dataclasses import asdict
from core.world import World
from core.dragon import Dragon

SAVE_VERSION = 3


def save_world(world: World, filename: str):
    data = {
        "save_version": SAVE_VERSION,

        "tribe_name": world.tribe_name,
        "moon": world.moon,
        "dragons": [asdict(dragon) for dragon in world.dragons],
        "event_log": world.event_log,
        "pending_choice": world.pending_choice,
        "tension": world.tension,

        "leader_id": world.leader_id,
        "deputy_id": world.deputy_id,

        "direction": world.direction,
        "direction_timer": world.direction_timer,

        "tribal_relations": world.tribal_relations,
        "tribal_incidents": world.tribal_incidents,
        "tribal_leaders": world.tribal_leaders,
        "diplomacy_cooldowns": world.diplomacy_cooldowns,
        "tribal_traits": world.tribal_traits,

        "tribe_titles": world.tribe_titles,
        "world_flags": world.world_flags,

        "territory_control": world.territory_control,
        "region_landmarks": world.region_landmarks,
        "region_activity": world.region_activity,
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def load_world(filename: str) -> World:
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    version = data.get("save_version", 0)

    world = World(
        tribe_name=data.get("tribe_name", "Unknown Tribe"),
        moon=data.get("moon", 0),
        dragons=[],
        event_log=data.get("event_log", []),
        pending_choice=data.get("pending_choice"),
        tension=data.get("tension", 0.0),

        leader_id=data.get("leader_id"),
        deputy_id=data.get("deputy_id"),

        direction=data.get("direction"),
        direction_timer=data.get("direction_timer", 0),

        tribal_relations=data.get("tribal_relations", {}),
        tribal_incidents=data.get("tribal_incidents", {}),
        tribal_leaders=data.get("tribal_leaders", {}),
        diplomacy_cooldowns=data.get("diplomacy_cooldowns", {}),
        tribal_traits=data.get("tribal_traits", {}),

        tribe_titles=data.get("tribe_titles", []),
        world_flags=data.get("world_flags", {}),

        territory_control=data.get("territory_control", {}),
        region_landmarks=data.get("region_landmarks", {}),
        region_activity=data.get("region_activity", {}),
    )

    for d in data.get("dragons", []):
        dragon = Dragon(**d)
        world.dragons.append(dragon)

    return world