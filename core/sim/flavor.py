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

def get_life_stage(dragon):
    age = dragon.age_moons

    if age < 24:
        return "Dragonet"
    elif age < 60:
        return "Young"
    elif age < 120:
        return "Adult"
    elif age < 200:
        return "Mature"
    else:
        return "Elder"

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

def generate_legacy_text(dragon, world):
    parts = []

    if dragon.status != "Dead":
        return ""

    cause = getattr(dragon, "cause_of_death", None)

    if cause == "conflict":
        parts.append("They died in a moment of conflict, a reminder of how quickly tension can turn deadly.")
    elif cause == "injury":
        parts.append("Their injuries ultimately claimed them, despite surviving the first blow.")
    elif cause == "natural":
        parts.append("They passed at the end of their life, their time in the tribe complete.")

    friend_count = len(getattr(dragon, "friends", []))
    rival_count = len(getattr(dragon, "rivals", []))
    scar_count = len(getattr(dragon, "scars", [])) if hasattr(dragon, "scars") else 0
    dragonet_count = len(getattr(dragon, "dragonets", []))
    mate = None

    surviving_mates = []
    for other in world.dragons:
        for flag, other_id in getattr(other, "memory_flags", []):
            if flag == "lost_mate" and other_id == dragon.id:
                surviving_mates.append(other.name)

    if surviving_mates:
        if len(surviving_mates) == 1:
            parts.append(f"They left behind their mate, {surviving_mates[0]}.")
        else:
            parts.append(f"They left behind mates who still remember them: {', '.join(surviving_mates)}.")

    if getattr(dragon, "mate_id", None) is not None:
        mate = next((d for d in world.dragons if d.id == dragon.mate_id), None)

    if dragon.role == "Leader":
        parts.append(f"They are remembered as one of the tribe's leaders.")
    elif dragon.role == "Healer":
        parts.append(f"They are remembered for the care they offered the tribe.")
    elif dragon.role in {"Warrior", "Hunter", "Scout"}:
        parts.append(f"They are remembered as a dragon who served the tribe directly.")

    if friend_count >= 3:
        parts.append("They left behind many bonds within the tribe.")
    elif friend_count >= 1:
        parts.append("They are still remembered by those who were close to them.")

    if rival_count >= 3:
        parts.append("Not all memories of them are gentle, and old tensions have not entirely faded.")

    if dragonet_count > 0:
        parts.append("Part of their legacy lives on through the dragonets they left behind.")

    if scar_count >= 2:
        parts.append("Their body bore clear signs of a difficult life.")

    if not parts:
        parts.append("Their memory lingers quietly in the tribe.")

    return " ".join(parts)

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

    stage = get_life_stage(dragon)

    parts.append(
        f"{dragon.name} is a {dragon.personality.lower()} {stage.lower()} {dragon.tribe.lower()}."
    )

    if stage == "Dragonet":
        parts.append("They are still early in life, with much of their future yet to unfold.")

    elif stage == "Young":
        parts.append("They are still finding their place within the tribe.")

    elif stage == "Adult":
        parts.append("They are firmly part of the tribe’s daily life.")

    elif stage == "Mature":
        parts.append("They have seen enough of the tribe to understand its deeper currents.")

    elif stage == "Elder":
        parts.append("They carry a long memory of the tribe and what it has endured.")

    if dragon.scars and stage in ["Mature", "Elder"]:
        parts.append(
            f"They carry {dragon.scars[0]}, one of many signs of a life that has not been easy."
        )

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

    lost_mate_ids = [
        other_id for flag, other_id in getattr(dragon, "memory_flags", [])
        if flag == "lost_mate"
    ]

    if lost_mate_ids:
        lost_mate = next((d for d in world.dragons if d.id == lost_mate_ids[-1]), None)
        if lost_mate:
            parts.append(
                f"They still carry the loss of {lost_mate.name}, and that absence remains part of who they are."
            )

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

    if not hasattr(dragon, "cause_of_death"):
        dragon.cause_of_death = None

    return " ".join(parts)