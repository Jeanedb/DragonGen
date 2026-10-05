import random


NORMAL_SHELL_COLORS = [
    "dark blue",
    "pale gold",
    "ash-gray",
    "speckled",
    "rust-red",
]


def create_egg(
    parent1,
    parent2,
    *,
    tribe=None,
    clutch_id=None,
    birth_order=1,
    egg_type="normal",
    hatch_time=None,
):
    """Create one egg with enough identity to survive saving and hatching.

    The caller decides whether an egg belongs to a MudWing clutch and whether
    it is blood-red.  Keeping those rolls outside this helper prevents other
    tribes from receiving MudWing traits merely because of a cosmetic shell
    colour.
    """
    resolved_tribe = tribe or getattr(parent1, "tribe", "Unknown")
    is_blood_red = resolved_tribe == "MudWing" and egg_type == "blood_red"
    resolved_clutch_id = str(clutch_id) if clutch_id is not None else None

    return {
        "mother": parent1.name,
        "father": parent2.name,
        "parent_ids": [parent1.id, parent2.id],
        "tribe": resolved_tribe,
        "age": 0,
        "hatch_time": hatch_time if hatch_time is not None else random.randint(3, 6),
        "size": random.choice(["small", "heavy", "large", "round"]),
        "shell_color": "blood-red" if is_blood_red else random.choice(NORMAL_SHELL_COLORS),
        "movement": random.choice(["rocks often", "barely moves", "twitches sharply", "rolls gently"]),
        "condition": random.choice(["healthy", "warm", "weak", "restless"]),
        "caretaker": None,
        "clutch_id": resolved_clutch_id,
        "sib_group_id": resolved_clutch_id if resolved_tribe == "MudWing" else None,
        "birth_order": int(birth_order),
        "egg_type": "blood_red" if is_blood_red else "normal",
        "fire_resistant": bool(is_blood_red),
    }
