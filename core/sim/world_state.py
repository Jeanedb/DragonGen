from core.world import World
from core.sim.leadership import get_leader_by_id


def get_living_dragons(world: World):
    return [d for d in world.dragons if d.status == "Alive"]


def get_eligible_non_dragonets(world: World):
    return [
        d for d in world.dragons
        if d.status == "Alive" and d.role != "Dragonet"
    ]


def get_world_mood(world):
    tension = getattr(world, "tension", 0.0)

    if tension < 0.75:
        return "Calm"
    elif tension < 1.5:
        return "Uneasy"
    elif tension < 2.5:
        return "Strained"
    elif tension < 3.5:
        return "Volatile"
    else:
        return "Crisis"


def get_tribe_climate(world):
    mood = get_world_mood(world)
    leader = get_leader_by_id(world)

    climate = {
        "bonding_bias": 0.0,
        "conflict_bias": 0.0,
        "mercy_bias": 0.0,
        "risk_bias": 0.0,
        "suspicion_bias": 0.0,
        "recovery_bias": 0.0,
        "tone_tags": []
    }

    if mood == "Calm":
        climate["bonding_bias"] += 0.20
        climate["recovery_bias"] += 0.15
    elif mood == "Uneasy":
        climate["suspicion_bias"] += 0.10
    elif mood == "Strained":
        climate["conflict_bias"] += 0.15
        climate["suspicion_bias"] += 0.15
    elif mood == "Volatile":
        climate["conflict_bias"] += 0.30
        climate["risk_bias"] += 0.20
    elif mood == "Crisis":
        climate["conflict_bias"] += 0.45
        climate["risk_bias"] += 0.30
        climate["mercy_bias"] -= 0.15

    direction = getattr(world, "direction", None)

    if direction == "stabilizing":
        climate["bonding_bias"] += 0.20
        climate["recovery_bias"] += 0.25
    elif direction == "pressuring":
        climate["conflict_bias"] += 0.25
        climate["risk_bias"] += 0.20
    elif direction == "watchful":
        climate["suspicion_bias"] += 0.30

    return climate

    
    # ---- Leader effects: long-term cultural pressure ----
    if leader:
        traits = getattr(leader, "personality_traits", []) or []

        if "Kind" in traits:
            climate["bonding_bias"] += 0.20
            climate["mercy_bias"] += 0.25
            climate["recovery_bias"] += 0.20
            climate["tone_tags"].append("gentle_leadership")

        if "Loyal" in traits:
            climate["bonding_bias"] += 0.15
            climate["recovery_bias"] += 0.10
            climate["tone_tags"].append("steady_leadership")

        if "Clever" in traits:
            climate["risk_bias"] -= 0.10
            climate["tone_tags"].append("measured_leadership")

        if "Ambitious" in traits:
            climate["conflict_bias"] += 0.20
            climate["risk_bias"] += 0.15
            climate["tone_tags"].append("pressured_leadership")

        if "Moody" in traits:
            climate["conflict_bias"] += 0.15
            climate["recovery_bias"] -= 0.15
            climate["tone_tags"].append("unstable_leadership")

        if "Suspicious" in traits:
            climate["suspicion_bias"] += 0.30
            climate["bonding_bias"] -= 0.10
            climate["tone_tags"].append("paranoid_leadership")

    return climate
