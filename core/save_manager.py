import json
from dataclasses import asdict
from core.world import World
from core.dragon import Dragon

SAVE_VERSION = 2


def save_world(world: World, filename: str):
    data = {
        "save_version": SAVE_VERSION,
        "tribe_name": world.tribe_name,
        "moon": world.moon,
        "event_log": world.event_log,
        "dragons": [asdict(dragon) for dragon in world.dragons],

        "tension": world.tension,
        "pending_choice": world.pending_choice,
        "leader_id": world.leader_id,
        "deputy_id": world.deputy_id,
        "direction": world.direction,
        "direction_timer": world.direction_timer,
        "tribal_relations": world.tribal_relations,
        "tribe_titles": world.tribe_titles,
        "world_flags": world.world_flags,
        "tribal_incidents": world.tribal_incidents,
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def load_world(filename: str) -> World:
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    version = data.get("save_version", 0)

    if version == 0:
        world = World(
            tribe_name=data["tribe_name"],
            moon=data["moon"],
            event_log=data.get("event_log", []),
            dragons=[],
            tension=0.0,
            pending_choice=None,
            leader_id=None,
            deputy_id=None,
            direction=None,
            direction_timer=0,
            tribal_relations={},
            tribal_incidents=data.get("tribal_incidents", {}),
        )

    elif version == 1:
        world = World(
            tribe_name=data["tribe_name"],
            moon=data["moon"],
            event_log=data.get("event_log", []),
            dragons=[],
            tension=data.get("tension", 0.0),
            pending_choice=data.get("pending_choice"),
            leader_id=data.get("leader_id"),
            deputy_id=data.get("deputy_id"),
            direction=data.get("direction"),
            direction_timer=data.get("direction_timer", 0),
            tribal_relations=data.get("tribal_relations", {}),
        )
    elif version == 2:
        world = World(
            tribe_name=data["tribe_name"],
            moon=data["moon"],
            event_log=data.get("event_log", []),
            dragons=[],
            tension=data.get("tension", 0.0),
            pending_choice=data.get("pending_choice"),
            leader_id=data.get("leader_id"),
            deputy_id=data.get("deputy_id"),
            direction=data.get("direction"),
            direction_timer=data.get("direction_timer", 0),
            tribal_relations=data.get("tribal_relations", {}),
            tribe_titles=data.get("tribe_titles", []),
            world_flags=data.get("world_flags", {}),
        )
    else:
        raise ValueError(f"Unsupported save version: {version}")

    for d in data.get("dragons", []):
        dragon = Dragon(**d)
        world.dragons.append(dragon)

    return world