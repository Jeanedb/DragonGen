import random


EYE_COLORS = [
    "amber", "green", "blue", "violet", "gold", "brown", "gray"
]

HOBBIES = [
    "flying",
    "hunting",
    "storytelling",
    "exploring",
    "training",
    "sunbathing",
    "collecting odd treasures",
    "watching others quietly",
    "stargazing",
    "swimming",
    "climbing",
    "mapping the territory",
]

SKILLS = [
    "tracking",
    "combat",
    "stealth",
    "navigation",
    "strategy",
    "healing",
    "observation",
    "patience",
    "endurance",
    "quick decision-making",
]

RANDOM_FACTS = [
    "prefers silence over small talk",
    "remembers faces better than names",
    "dislikes loud arguments",
    "watches others before speaking",
    "has a habit of pacing when restless",
    "is hard to read at first glance",
    "laughs more easily around trusted dragons",
    "has a surprisingly good memory for details",
    "rarely forgets a slight",
    "takes comfort in familiar routines",
]

SCAR_OPTIONS = [
    "a scar across one shoulder",
    "a jagged mark along their side",
    "a torn edge in one wing",
    "a faded burn mark",
    "a thin scar near one eye",
    "an old bite mark along the neck",
]


def ensure_dragon_flavor(dragon):
    """
    Add persistent flavor traits if they do not already exist.
    Safe to call repeatedly.
    """
    if not hasattr(dragon, "height"):
        dragon.height = round(random.uniform(4.0, 7.5), 1)

    if not hasattr(dragon, "eye_color"):
        dragon.eye_color = random.choice(EYE_COLORS)

    if not hasattr(dragon, "hobbies"):
        dragon.hobbies = random.sample(HOBBIES, k=2)

    if not hasattr(dragon, "skills"):
        dragon.skills = random.sample(SKILLS, k=2)

    if not hasattr(dragon, "scars"):
        dragon.scars = []

    if not hasattr(dragon, "random_fact"):
        dragon.random_fact = random.choice(RANDOM_FACTS)


def maybe_gain_scar(dragon, chance=0.35):
    """
    Injured dragons may gain a scar. Safe to call after an injury.
    """
    ensure_dragon_flavor(dragon)

    if random.random() < chance:
        scar = random.choice(SCAR_OPTIONS)
        if scar not in dragon.scars:
            dragon.scars.append(scar)
            return scar
    return None


def _name_list(ids, world, limit=3):
    names = []
    for dragon_id in ids[:limit]:
        other = next((d for d in world.dragons if d.id == dragon_id), None)
        if other:
            names.append(other.name)
    return names


def _join_naturally(items):
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def generate_dragon_bio(dragon, world):
    """
    Build a readable biography paragraph from stable traits + current world state.
    """
    ensure_dragon_flavor(dragon)

    parts = []

    intro = f"{dragon.name} is a {dragon.personality.lower()} {dragon.tribe.lower()}."
    parts.append(intro)

    parent_names = _name_list(getattr(dragon, "parents", []), world, limit=2)
    if parent_names:
        parts.append(
            f"As the child of {_join_naturally(parent_names)}, {dragon.name} grew up within the {world.tribe_name}."
        )

    if dragon.role != "Dragonet":
        parts.append(
            f"They serve as a {dragon.role.lower()} and currently hold the rank of {dragon.rank.lower()}."
            if dragon.rank != "None"
            else f"They serve as a {dragon.role.lower()} in the {world.tribe_name}."
        )
    else:
        parts.append("They are still a dragonet, with the rest of their life still taking shape.")

    parts.append(
        f"Standing {dragon.height:.1f} meters tall with {dragon.eye_color} eyes, they are a noticeable presence in the tribe."
    )

    if dragon.skills:
        parts.append(
            f"Their strengths lie in {_join_naturally(dragon.skills[:2])}."
        )

    if dragon.hobbies:
        parts.append(
            f"When left to themselves, they are often drawn to {_join_naturally(dragon.hobbies[:2])}."
        )

    if dragon.mate_id is not None:
        mate = next((d for d in world.dragons if d.id == dragon.mate_id), None)
        if mate:
            parts.append(f"They are closely bonded to {mate.name}.")

    friend_names = _name_list(getattr(dragon, "friends", []), world)
    if friend_names:
        parts.append(
            f"They have formed meaningful bonds with {_join_naturally(friend_names)}."
        )

    rival_names = _name_list(getattr(dragon, "rivals", []), world)
    if rival_names:
        parts.append(
            f"Not all of their relationships are easy, and tension lingers around {_join_naturally(rival_names)}."
        )

    if dragon.scars:
        parts.append(
            f"They carry {dragon.scars[0]}, a visible reminder of what they have endured."
        )

    if dragon.random_fact:
        parts.append(f"Others have noted that {dragon.name.lower()} {dragon.random_fact}.")

    if dragon.status == "Dead":
        parts.append(f"They are now dead, but their place in the tribe's memory remains.")

    return " ".join(parts)