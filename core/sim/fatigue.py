def change_fatigue(world, dragon, amount):
    """Adjust the shared fatigue pool for hunts, patrols, and other activities."""
    fatigue = world.world_flags.get("dragon_fatigue")
    if not isinstance(fatigue, dict):
        fatigue = {}
        world.world_flags["dragon_fatigue"] = fatigue
    key = str(dragon.id)
    legacy_amount = fatigue.pop(dragon.id, 0)
    fatigue[key] = max(0, min(6, int(fatigue.get(key, legacy_amount)) + amount))
