import json
from dataclasses import asdict
from core.world import World
from core.dragon import Dragon


def save_world(world: World, filename: str):
    data = {
        "tribe_name": world.tribe_name,
        "moon": world.moon,
        "event_log": world.event_log,
        "dragons": [asdict(dragon) for dragon in world.dragons]
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def load_world(filename: str) -> World:
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    world = World(
        tribe_name=data["tribe_name"],
        moon=data["moon"],
        event_log=data["event_log"],
        dragons=[]
    )

    for d in data["dragons"]:
        dragon = Dragon(**d)
        world.dragons.append(dragon)

    return world