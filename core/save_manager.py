import json
from dataclasses import asdict
from core.world import World
from core.dragon import Dragon
from core.sim.memory import Memory
from core.sim.relationships import Relationship

SAVE_VERSION = 9


def _keys_to_int(value):
    """Convert JSON object keys that represent dragon IDs back into integers."""
    if not isinstance(value, dict):
        return {}

    converted = {}
    for key, item in value.items():
        try:
            converted[int(key)] = item
        except (TypeError, ValueError):
            converted[key] = item
    return converted


def _normalize_dragon_after_load(dragon: Dragon):
    """Repair fields that JSON cannot preserve exactly, especially int-keyed dicts."""
    dragon.trust = _keys_to_int(getattr(dragon, "trust", {}))
    dragon.resentment = _keys_to_int(getattr(dragon, "resentment", {}))
    dragon.perceived_reputation = _keys_to_int(getattr(dragon, "perceived_reputation", {}))
    dragon.rivalry_levels = _keys_to_int(getattr(dragon, "rivalry_levels", {}))

    # JSON stores tuples as lists. The rest of the code only indexes these,
    # but converting back keeps the field consistent with the dataclass intent.
    dragon.memory_flags = [tuple(flag) for flag in getattr(dragon, "memory_flags", [])]

    dragon.memories = [
        memory
        if isinstance(memory, Memory)
        else Memory(**memory)
        for memory in getattr(dragon, "memories", [])
        if isinstance(memory, (Memory, dict))
    ]

    restored_relationships = []

    for relationship in getattr(dragon, "relationships", []):
        if isinstance(relationship, Relationship):
            restored_relationships.append(relationship)
            continue

        if not isinstance(relationship, dict):
            continue

        relationship_data = dict(relationship)

        relationship_data["history"] = [
            memory
            if isinstance(memory, Memory)
            else Memory(**memory)
            for memory in relationship_data.get("history", [])
            if isinstance(memory, (Memory, dict))
        ]

        restored_relationships.append(
            Relationship(**relationship_data)
        )

    dragon.relationships = restored_relationships

    # Explicit defaults also protect saves made by experimental builds where
    # Dragon may have been serialized without the current dataclass fields.
    dragon.sib_group_id = getattr(dragon, "sib_group_id", None)
    dragon.is_bigwings = bool(getattr(dragon, "is_bigwings", False))
    dragon.birth_order = getattr(dragon, "birth_order", None)
    dragon.egg_type = getattr(dragon, "egg_type", "normal") or "normal"
    dragon.fire_resistant = bool(getattr(dragon, "fire_resistant", False))
    dragon.last_clutch_moon = int(getattr(dragon, "last_clutch_moon", -999))

    return dragon


def _normalize_eggs_after_load(world: World):
    """Migrate eggs made before clutches and real blood-red traits existed."""
    dragons_by_id = {dragon.id: dragon for dragon in world.dragons}
    dragons_by_name = {dragon.name: dragon for dragon in world.dragons}

    for egg in getattr(world, "eggs", []):
        if not isinstance(egg, dict):
            continue

        parent_ids = egg.get("parent_ids", [])
        parents = [
            dragons_by_id[parent_id]
            for parent_id in parent_ids
            if parent_id in dragons_by_id
        ]

        if not parents:
            parents = [
                dragons_by_name[name]
                for name in (egg.get("mother"), egg.get("father"))
                if name in dragons_by_name
            ]
            egg["parent_ids"] = [parent.id for parent in parents]

        tribe = egg.get("tribe")
        if not tribe and parents:
            parent_tribes = {parent.tribe for parent in parents}
            tribe = parents[0].tribe if len(parent_tribes) == 1 else parents[0].tribe
        egg["tribe"] = tribe or "Unknown"

        legacy_blood_red = str(egg.get("shell_color", "")).lower() == "blood-red"
        is_blood_red = (
            egg["tribe"] == "MudWing"
            and (egg.get("egg_type") == "blood_red" or legacy_blood_red)
        )

        egg["egg_type"] = "blood_red" if is_blood_red else "normal"
        egg["fire_resistant"] = bool(is_blood_red)
        egg.setdefault("clutch_id", None)
        egg.setdefault("sib_group_id", egg.get("clutch_id") if egg["tribe"] == "MudWing" else None)
        egg.setdefault("birth_order", 1)

        # Older builds could randomly give any tribe a cosmetic blood-red
        # shell.  Keep red-brown colouring without falsely granting the trait.
        if legacy_blood_red and egg["tribe"] != "MudWing":
            egg["shell_color"] = "rust-red"


def save_world(world: World, filename: str):
    data = {
        "save_version": SAVE_VERSION,

        "tribe_name": world.tribe_name,
        "moon": world.moon,
        "eggs": world.eggs,
        "dragons": [asdict(dragon) for dragon in world.dragons],
        "event_log": world.event_log,
        "pending_choice": world.pending_choice,
        "location_notices": getattr(world, "location_notices", {}),
        "tension": world.tension,
        "food_stores": world.food_stores,

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
        eggs=data.get("eggs", []),
        dragons=[],
        event_log=data.get("event_log", []),
        pending_choice=data.get("pending_choice"),
        location_notices=data.get("location_notices", {}),
        tension=data.get("tension", 0.0),
        food_stores=data.get("food_stores", 100),

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
        dragon = _normalize_dragon_after_load(Dragon(**d))
        world.dragons.append(dragon)

    _normalize_eggs_after_load(world)

    return world
