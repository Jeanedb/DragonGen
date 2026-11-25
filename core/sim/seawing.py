"""SeaWing reef expeditions and storm rescues."""

import random

from core.sim.consequences import schedule_consequence
from core.sim.fatigue import change_fatigue
from core.sim.logging import log_event
from core.sim.memory import Memory, add_memory

REEF_REWARDS = {"shallow_reef": (8, 14), "deep_reef": (21, 33)}


def has_reef_routes(world):
    return world.tribe_name == "SeaWing Tribe"


def has_dark_vision(dragon):
    return dragon.tribe == "SeaWing"


def advance_reef_current(world):
    if has_reef_routes(world):
        world.world_flags["reef_current"] = "strong" if random.random() < 0.30 else "calm"


def has_strong_current(world):
    return world.world_flags.get("reef_current") == "strong"


def reef_success(world, route, divers, base_chance):
    if not divers or route != "deep_reef" or not has_strong_current(world):
        return base_chance
    penalty = 0.10 if any(dragon.role == "Scout" for dragon in divers) else 0.20
    return max(0.05, base_chance - penalty)


def fit_for_reef(dragon):
    return dragon.status == "Alive" and dragon.health == "Healthy" and dragon.role != "Dragonet"


def reef_party(party, route):
    available = [dragon for dragon in party if fit_for_reef(dragon)]
    if route == "shallow_reef":
        return available, []
    divers = [dragon for dragon in available if dragon.tribe == "SeaWing"]
    shore_party = [dragon for dragon in available if dragon.tribe != "SeaWing"]
    return divers, shore_party


def reef_food_range(route, yield_multiplier, shore_count):
    return tuple(round(amount * yield_multiplier) + 2 * shore_count for amount in REEF_REWARDS[route])


def forage_reef(world, route, party, success_chance, yield_multiplier):
    if not has_reef_routes(world) or route not in REEF_REWARDS or world.pending_choice is not None:
        return False
    divers, shore_party = reef_party(party, route)
    if not divers:
        return False

    deep = route == "deep_reef"
    place = "the deep reef" if deep else "the reef shallows"
    leader = divers[0]
    for dragon in divers:
        change_fatigue(world, dragon, 2 if deep else 1)
    for dragon in shore_party:
        change_fatigue(world, dragon, 1)

    if random.random() < success_chance:
        food = random.randint(*reef_food_range(route, yield_multiplier, len(shore_party)))
        if deep and random.random() < 0.25:
            offer_aquatic_warning(world, divers, shore_party, food)
            return True
        world.food_stores += food
        text = f"{leader.name}'s party returned from {place} with {food} food."
        if shore_party:
            text += " The shore party added food gathered in the shallows."
    else:
        text = f"{leader.name}'s party returned from {place} empty-handed."

    log_event(
        world, text, involved_ids=[dragon.id for dragon in divers + shore_party],
        event_type="hunt", importance=3 if deep else 2,
    )
    return True


def offer_aquatic_warning(world, divers, shore_party, food):
    scout = divers[0]
    interpreter = divers[1] if len(divers) > 1 else None
    # A visiting shore crew makes the warning possible in a SeaWing-only roster.
    shore_team = "the shore team" if shore_party else "a visiting shore crew"
    shore_food = 2 * len(shore_party)
    wait_food = shore_food + (food - shore_food) // 2
    options = []
    if interpreter:
        options.append({
            "id": "relay",
            "text": f"{interpreter.name} relays the warning ({food} food, +1 fatigue)",
        })
    options.extend([
        {"id": "recall", "text": f"Recall the divers ({shore_food} food)"},
        {"id": "wait", "text": f"Wait for the divers to surface ({wait_food} food, +1 fatigue per diver)"},
    ])
    world.pending_choice = {
        "type": "seawing_aquatic_warning",
        "location": "hunting",
        "diver_ids": [dragon.id for dragon in divers],
        "shore_ids": [dragon.id for dragon in shore_party],
        "interpreter_id": interpreter.id if interpreter else None,
        "food": food,
        "shore_food": shore_food,
        "wait_food": wait_food,
        "text": (
            f"At Tideglass Reef, {scout.name} flashes a warning in Aquatic. "
            f"The passage ahead is unsafe. On shore, {shore_team} sees the flashes but can't read them."
        ),
        "context": [] if interpreter else ["Bring a second SeaWing to relay signals to the shore team."],
        "options": options,
    }


def resolve_aquatic_warning(world, option_id):
    choice = world.pending_choice
    available = {dragon.id: dragon for dragon in world.dragons if fit_for_reef(dragon)}
    divers = [available[dragon_id] for dragon_id in choice["diver_ids"] if dragon_id in available]
    shore_party = [available[dragon_id] for dragon_id in choice["shore_ids"] if dragon_id in available]
    interpreter = available.get(choice["interpreter_id"])

    if option_id == "relay" and interpreter is not None and interpreter.tribe == "SeaWing":
        change_fatigue(world, interpreter, 1)
        for helper in shore_party:
            helper.trust[interpreter.id] = helper.trust.get(interpreter.id, 0) + 0.5
        food = choice["food"]
        text = f"{interpreter.name} relayed the Aquatic warning. The party took a sheltered route."
    elif option_id == "wait" and divers:
        for diver in divers:
            change_fatigue(world, diver, 1)
        food = choice["wait_food"]
        text = "The shore team waited for the divers to surface. Part of the catch drifted away."
    elif option_id in {"recall", "wait", "relay"}:
        food = choice["shore_food"]
        text = "The party abandoned the deep reef."
        if food:
            text += " The shore team brought home what they had gathered."
    else:
        return "That response to the Aquatic warning is unavailable."

    world.food_stores += food
    result = f"{text} The tribe gained {food} food."
    log_event(
        world, result, involved_ids=[dragon.id for dragon in divers + shore_party],
        event_type="hunt", importance=3,
    )
    return result


def try_trench_discovery(world):
    if (
        not has_reef_routes(world)
        or world.pending_choice is not None
        or world.moon < world.world_flags.get("last_trench_discovery_moon", -6) + 6
    ):
        return False

    divers = [dragon for dragon in world.dragons if fit_for_reef(dragon) and has_dark_vision(dragon)]
    if not divers or random.random() >= 0.08:
        return False

    guide = next((dragon for dragon in divers if dragon.role == "Scout"), divers[0])
    world.pending_choice = {
        "type": "seawing_trench_discovery",
        "location": "hunting",
        "guide_id": guide.id,
        "text": (
            f"In the dark passages of Deepfin Trench, {guide.name} spots a supply sled "
            "wedged beneath a ledge. They can see a path to it that the shore crew missed."
        ),
        "options": [
            {"id": "retrieve", "text": f"Send {guide.name} in now (10 food, +2 fatigue)"},
            {"id": "mark", "text": "Mark the route and return next moon (5 food, no extra fatigue)"},
        ],
    }
    world.world_flags["last_trench_discovery_moon"] = world.moon
    return True


def resolve_trench_discovery(world, option_id):
    guide = next(
        (dragon for dragon in world.dragons if dragon.id == world.pending_choice["guide_id"]),
        None,
    )
    if option_id == "retrieve" and guide and fit_for_reef(guide) and has_dark_vision(guide):
        change_fatigue(world, guide, 2)
        world.food_stores += 10
        text = f"{guide.name} used their dark vision to free the supply sled. The tribe gained 10 food."
    elif option_id == "mark":
        schedule_consequence(world, 0, {"type": "seawing_trench_supplies"})
        text = "The route to the sled is marked. A shore crew will recover 5 food next moon."
    else:
        return "That response to the trench discovery is unavailable."

    log_event(world, text, involved_ids=[guide.id] if guide else [], event_type="hunt", importance=3)
    return text


def try_reef_storm(world):
    if (
        not has_reef_routes(world)
        or world.pending_choice is not None
        or world.moon < world.world_flags.get("last_reef_storm_moon", -6) + 6
    ):
        return False

    swimmers = [dragon for dragon in world.dragons if fit_for_reef(dragon) and dragon.tribe == "SeaWing"]
    if len(swimmers) < 2 or random.random() >= 0.10:
        return False

    scout = next((dragon for dragon in swimmers if dragon.role == "Scout"), swimmers[0])
    stranded = random.choice([dragon for dragon in swimmers if dragon.id != scout.id])
    divers = [dragon for dragon in swimmers if dragon.id != stranded.id][:2]
    shore_lead = next(
        (dragon for dragon in world.dragons if fit_for_reef(dragon) and dragon.tribe != "SeaWing"),
        scout,
    )

    world.pending_choice = {
        "type": "seawing_reef_storm",
        "location": "hunting",
        "stranded_id": stranded.id,
        "diver_ids": [dragon.id for dragon in divers],
        "shore_id": shore_lead.id,
        "text": (
            f"After a storm at Tideglass Reef, {scout.name} spotted {stranded.name} "
            "stranded on a reef shelf beside a damaged food cache."
        ),
        "context": [
            f"Swimmers: {', '.join(dragon.name for dragon in divers)}",
            f"Shoreline guide: {shore_lead.name}",
        ],
        "options": [
            {"id": "dive", "text": "Send SeaWing swimmers and recover 8 food (+2 fatigue each)"},
            {"id": "shore", "text": "Guide them ashore and leave the cache (+1 fatigue to the guide)"},
            {"id": "wait", "text": "Wait for the current to ease"},
        ],
    }
    world.world_flags["last_reef_storm_moon"] = world.moon
    return True


def resolve_reef_storm(world, option_id):
    choice = world.pending_choice
    by_id = {dragon.id: dragon for dragon in world.dragons if dragon.status == "Alive"}
    stranded = by_id.get(choice["stranded_id"])
    if stranded is None:
        return "The reef rescue is no longer needed."

    if option_id == "dive":
        helpers = [
            by_id[dragon_id] for dragon_id in choice["diver_ids"]
            if dragon_id in by_id and fit_for_reef(by_id[dragon_id])
            and by_id[dragon_id].tribe == "SeaWing"
        ]
        if not helpers:
            return "The planned swimmers were unavailable. No food was recovered."
        world.food_stores += 8
        fatigue, trust = 2, 1.0
        text = f"The SeaWing swimmers brought {stranded.name} home and recovered 8 food from the cache."
    elif option_id == "shore":
        guide = by_id.get(choice["shore_id"])
        if guide is None or not fit_for_reef(guide):
            return "The shoreline guide was unavailable. No food was recovered."
        helpers = [guide]
        fatigue, trust = 1, 0.5
        text = f"{guide.name} guided {stranded.name} ashore. The damaged cache was swept away."
    elif option_id == "wait":
        helpers = []
        fatigue, trust = 0, 0
        change_fatigue(world, stranded, 2)
        world.tension = min(5, world.tension + 0.15)
        text = f"{stranded.name} made it ashore once the current eased, exhausted and without the cache."
    else:
        return "That response to the reef storm is unavailable."

    for helper in helpers:
        change_fatigue(world, helper, fatigue)
        stranded.trust[helper.id] = stranded.trust.get(helper.id, 0) + trust
        add_memory(stranded, Memory(
            type="helped_ashore_at_reef", moon=world.moon, other_id=helper.id,
            importance=4, tags=["seawing", "reef", "rescue"],
        ))
    log_event(
        world, text, involved_ids=[stranded.id, *(dragon.id for dragon in helpers)],
        event_type="hunt", importance=4,
    )
    return text
