import random
from core.dragon import Dragon
from core.world import World
from data.names import NAMES_BY_TRIBE
from data.personalities import PERSONALITIES
from data.tribes import TRIBES, TRIBE_PERSONALITY_BIAS
from core.sim.politics import initialize_tribal_relations
from core.sim.logging import log_event
from data.regions import REGION_DATA



def pick_role(age_moons: int) -> str:
    if age_moons < 12:
        return "Dragonet"
    if age_moons > 140:
        return random.choice(["Elder", "Hunter", "Scout"])
    return random.choice(["Hunter", "Scout", "Warrior", "Healer"])


def generate_dragon(dragon_id: int, forced_tribe: str | None = None) -> Dragon:
    tribe = forced_tribe if forced_tribe else random.choice(TRIBES)
    age = random.randint(12, 160)
    role = pick_role(age)

    if tribe in TRIBE_PERSONALITY_BIAS and random.random() < 0.6:
        personality = random.choice(TRIBE_PERSONALITY_BIAS[tribe])
    else:
        personality = random.choice(PERSONALITIES)

    name = random.choice(NAMES_BY_TRIBE[tribe])

    return Dragon(
        id=dragon_id,
        name=name,
        tribe=tribe,
        age_moons=age,
        role=role,
        personality=personality,
        rank="None"
    )


def generate_dragonet(dragon_id: int, tribe: str, parents=None) -> Dragon:
    if parents and random.random() < 0.6:
        personality = random.choice([p.personality for p in parents])
    elif tribe in TRIBE_PERSONALITY_BIAS and random.random() < 0.5:
        personality = random.choice(TRIBE_PERSONALITY_BIAS[tribe])
    else:
        personality = random.choice(PERSONALITIES)

    name = random.choice(NAMES_BY_TRIBE[tribe])

    return Dragon(
        id=dragon_id,
        name=name,
        tribe=tribe,
        age_moons=0,
        role="Dragonet",
        personality=personality,
        rank="None"
    )


def initialize_regions(world):
    for tribe, regions in REGION_DATA.items():
        for region in regions:
            region_name = region["name"]

            world.territory_control[region_name] = tribe
            world.region_landmarks[region_name] = region["landmarks"]



def generate_starting_world(selected_tribe=None) -> World:
    if selected_tribe is None or selected_tribe == "Mixed":
        world = World(tribe_name="Sunset Tribe")
        forced_tribe = None
        initialize_tribal_relations(world)
    else:
        world = World(tribe_name=f"{selected_tribe} Tribe")
        forced_tribe = selected_tribe
        initialize_tribal_relations(world, selected_tribe)

    initialize_regions(world)


    for tribe in world.tribal_relations.keys():
        name = random.choice(NAMES_BY_TRIBE.get(tribe, ["Unnamed"]))
        world.tribal_leaders[tribe] = f"Queen {name}"

    TRAITS = ["cautious", "aggressive", "opportunistic"]

    for tribe in world.tribal_relations.keys():
        world.tribal_traits[tribe] = random.choice(TRAITS)

    for i in range(12):
        world.dragons.append(generate_dragon(i + 1, forced_tribe))

    adults = [d for d in world.dragons if d.role != "Dragonet"]

    if adults:
        leader = random.choice(adults)
        leader.rank = "Leader"

        deputy_candidates = [d for d in adults if d.id != leader.id]
        if deputy_candidates:
            deputy = random.choice(deputy_candidates)
            deputy.rank = "Deputy"

    log_event(
        world,
        "The tribe was founded.",
        involved_ids=[],
        event_type="founding",
        importance=5,
    )


    return world