"""MudWing sib leadership and events using the shared simulation state."""

import random

from core.sim.family import birth_sib_group
from core.sim.fatigue import change_fatigue
from core.sim.injury import add_injury
from core.sim.logging import log_event
from core.sim.memory import Memory, add_memory


def has_mud_wallow(world):
    return world.tribe_name == "MudWing Tribe"


def sib_groups(world):
    groups = {}
    for dragon in world.dragons:
        if dragon.tribe == "MudWing" and dragon.sib_group_id:
            groups.setdefault(dragon.sib_group_id, []).append(dragon)
    return {
        group_id: sorted(
            members, key=lambda dragon: (dragon.birth_order or float("inf"), dragon.id)
        )
        for group_id, members in groups.items()
    }


def sib_group_label(group_id):
    if group_id.startswith("founding-mudwing-sibs-"):
        return f"Founding sib group {group_id.rsplit('-', 1)[1]}"
    if group_id.startswith("mudwing-clutch-"):
        return f"Clutch {group_id.rsplit('-', 1)[1]}"
    return f"Sib group {group_id}"


def maintain_bigwings(world):
    for members in sib_groups(world).values():
        living = [dragon for dragon in members if dragon.status == "Alive"]
        if not living or any(dragon.is_bigwings for dragon in living):
            continue

        former = max(
            (dragon for dragon in reversed(members) if dragon.is_bigwings),
            key=lambda dragon: max(
                (memory.moon for memory in dragon.memories if memory.type == "took_up_bigwings_duties"),
                default=-1,
            ),
            default=None,
        )
        if former is None:
            continue

        successor = next(
            (dragon for dragon in living if dragon.sib_adoption_moon is None),
            living[0],
        )
        successor.is_bigwings = True
        add_memory(successor, Memory(
            type="took_up_bigwings_duties",
            moon=world.moon,
            other_id=former.id,
            importance=5,
            tags=["mudwing", "sib", "family"],
        ))
        loss = "departure" if former.status == "Departed" else "death"
        log_event(
            world,
            f"{successor.name} took up BigWings duties for their sibs after {former.name}'s {loss}.",
            involved_ids=[successor.id, former.id],
            event_type="bigwings_succession",
            importance=5,
        )


def can_be_adopted(world, dragon, groups):
    if dragon.tribe != "MudWing" or dragon.status != "Alive" or dragon.role != "Dragonet":
        return False
    group = dragon.sib_group_id
    if not group:
        return True
    return (
        not any(sib.id != dragon.id and sib.status == "Alive" for sib in groups.get(group, []))
        and not any(egg.get("sib_group_id") == group for egg in world.eggs)
    )


def try_sib_adoption(world):
    if world.pending_choice is not None:
        return False
    groups = sib_groups(world)
    if not groups:
        return False
    retries = world.world_flags.get("sib_adoption_retry", {})
    for dragon in world.dragons:
        if world.moon < retries.get(str(dragon.id), 0) or not can_be_adopted(world, dragon, groups):
            continue
        offers = []
        for group_id, members in groups.items():
            if group_id == dragon.sib_group_id:
                continue
            living = [sib for sib in members if sib.status == "Alive"]
            if not living:
                continue
            average_age = sum(sib.age_moons for sib in living) / len(living)
            age_gap = abs(average_age - dragon.age_moons)
            if age_gap <= 12:
                representative = next((sib for sib in living if sib.is_bigwings), living[0])
                offers.append((age_gap, group_id, representative))

        if not offers:
            continue
        _, group_id, representative = min(offers, key=lambda offer: (offer[0], offer[1]))
        world.pending_choice = {
            "type": "mudwing_sib_adoption",
            "location": "hatchery",
            "dragonet_id": dragon.id,
            "sib_group_id": group_id,
            "text": (
                f"{dragon.name} is growing up without sibs. "
                f"{representative.name}'s sib group has offered to take them in."
            ),
            "options": [
                {"id": "accept", "text": "Let the group adopt the dragonet as a sib"},
                {"id": "wait", "text": "Wait and give the dragonet more time"},
            ],
        }
        return True
    return False


def resolve_sib_adoption(world, option_id):
    choice = world.pending_choice
    dragon = next((d for d in world.dragons if d.id == choice["dragonet_id"]), None)
    group_id = choice["sib_group_id"]
    groups = sib_groups(world)
    sibs = [sib for sib in groups.get(group_id, []) if sib.status == "Alive"]
    if (
        dragon is None
        or not sibs
        or group_id == dragon.sib_group_id
        or not can_be_adopted(world, dragon, groups)
    ):
        return "The sib adoption offer is no longer available."

    if option_id == "wait":
        world.world_flags.setdefault("sib_adoption_retry", {})[str(dragon.id)] = world.moon + 3
        return f"The caretaker decided to give {dragon.name} more time before revisiting adoption."
    if option_id != "accept":
        return "That adoption decision is unavailable."

    dragon.birth_sib_group_id = birth_sib_group(dragon)
    dragon.sib_adoption_moon = world.moon
    dragon.sib_group_id = group_id
    dragon.is_bigwings = False
    for sib in sibs:
        dragon.trust[sib.id] = dragon.trust.get(sib.id, 0) + 0.5
        sib.trust[dragon.id] = sib.trust.get(dragon.id, 0) + 0.5
        for member, other in ((dragon, sib), (sib, dragon)):
            add_memory(member, Memory(
                type="welcomed_as_sibs",
                moon=world.moon,
                other_id=other.id,
                importance=4,
                tags=["mudwing", "sib", "family"],
            ))

    result = f"{dragon.name} was welcomed as an adopted sib by {sib_group_label(group_id).lower()}."
    log_event(
        world,
        result,
        involved_ids=[dragon.id, *(sib.id for sib in sibs)],
        event_type="hatchery",
        importance=4,
    )
    return result


def resting_sibs(members):
    return [dragon for dragon in members if dragon.status == "Alive" and dragon.health == "Healthy"]


def wallow_reopens_moon(world):
    return world.world_flags.get("wallow_reopens_moon", 0)


def rest_sibs_at_wallow(world, group_id):
    if (
        not has_mud_wallow(world)
        or world.moon < wallow_reopens_moon(world)
        or world.world_flags.get("last_wallow_moon") == world.moon
    ):
        return False
    party = resting_sibs(sib_groups(world).get(group_id, []))
    if len(party) < 2:
        return False

    for dragon in party:
        change_fatigue(world, dragon, -2)
        dragon.location = "mud_wallow"
        for sib in party:
            if sib.id != dragon.id:
                dragon.trust[sib.id] = dragon.trust.get(sib.id, 0) + 0.15

    world.world_flags["last_wallow_moon"] = world.moon
    names = ", ".join(dragon.name for dragon in party)
    log_event(
        world,
        f"{names} rested together at the communal mud wallow and caught up with their sibs.",
        involved_ids=[dragon.id for dragon in party],
        event_type="mud_wallow_rest",
        importance=2,
    )
    return True


def try_mudwing_sib_decision(world):
    if (
        not has_mud_wallow(world)
        or world.pending_choice is not None
        or world.moon < world.world_flags.get("last_mudwing_sib_decision_moon", -5) + 5
    ):
        return False

    rations = []
    floods = []
    living_count = sum(dragon.status == "Alive" for dragon in world.dragons)
    for group_id, members in sib_groups(world).items():
        living = [dragon for dragon in members if dragon.status == "Alive"]
        bigwings = next((dragon for dragon in living if dragon.is_bigwings), None)
        if bigwings and len(living) >= 2 and 4 <= world.food_stores <= living_count:
            rations.append({
                "type": "mudwing_sib_rations",
                "location": "village",
                "group_id": group_id,
                "bigwings_id": bigwings.id,
                "text": (
                    f"With fewer rations to go around, {bigwings.name} asks to draw on the "
                    "tribe's last food stores so their sibs can eat together."
                ),
                "options": [
                    {"id": "share", "text": "Spend 4 food on a shared meal for the sibs"},
                    {"id": "reserve", "text": "Keep the food in the communal reserve"},
                ],
            })

        crew = [dragon for dragon in resting_sibs(living) if dragon.role != "Dragonet"]
        if len(crew) >= 2 and world.moon >= wallow_reopens_moon(world):
            first, second = crew[:2]
            floods.append({
                "type": "mudwing_wallow_flood",
                "location": "mud_wallow",
                "crew_ids": [first.id, second.id],
                "text": (
                    "Heavy rain has flooded the mud wallow. "
                    f"{first.name} and their sib {second.name} offer to clear the drainage channels."
                ),
                "options": [
                    {"id": "clear", "text": "Let the sibs clear the channels (+2 fatigue each)"},
                    {"id": "close", "text": "Close the wallow until the water drains (2 moons)"},
                ],
            })

    choices = [offers for offers in (rations, floods) if offers]
    if not choices or random.random() >= 0.10:
        return False
    # Choose the incident before choosing a group so the roster does not skew the odds.
    world.pending_choice = random.choice(random.choice(choices))
    world.world_flags["last_mudwing_sib_decision_moon"] = world.moon
    return True


def resolve_sib_rations(world, option_id):
    choice = world.pending_choice
    members = sib_groups(world).get(choice["group_id"], [])
    living = [dragon for dragon in members if dragon.status == "Alive"]
    bigwings = next((dragon for dragon in living if dragon.id == choice["bigwings_id"]), None)
    if bigwings is None or not bigwings.is_bigwings or len(living) < 2:
        return "The request for a shared meal has passed."

    if option_id == "share" and world.food_stores >= 4:
        world.food_stores -= 4
        world.tension = max(0, world.tension - 0.2)
        for sib in living:
            if sib.id != bigwings.id:
                sib.trust[bigwings.id] = sib.trust.get(bigwings.id, 0) + 0.5
        result = f"{bigwings.name} spent 4 food on a meal for their sibs. The meal eased tensions."
    elif option_id == "reserve":
        result = f"{bigwings.name} agreed to keep the remaining food in the communal reserve."
    else:
        return "There is no shared meal available."

    log_event(
        world, result, involved_ids=[dragon.id for dragon in living],
        event_type="mudwing_sib_rations", importance=3,
    )
    return result


def resolve_wallow_flood(world, option_id):
    crew_ids = world.pending_choice["crew_ids"]
    crew = [
        dragon for dragon in resting_sibs(world.dragons)
        if dragon.id in crew_ids and dragon.role != "Dragonet"
    ]
    if option_id == "clear" and len(crew) == len(crew_ids):
        for dragon in crew:
            change_fatigue(world, dragon, 2)
        result = f"{crew[0].name} and {crew[1].name} cleared the channels. The wallow stays open."
    elif option_id in {"clear", "close"}:
        world.world_flags["wallow_reopens_moon"] = world.moon + 2
        for dragon in world.dragons:
            if dragon.status == "Alive" and dragon.location == "mud_wallow":
                dragon.location = "healer_den" if dragon.health == "Injured" else "village_center"
        result = f"The flooded wallow will reopen at Moon {world.moon + 2}."
    else:
        return "That response to the flood is unavailable."

    log_event(
        world, result, involved_ids=[dragon.id for dragon in crew],
        event_type="mudwing_wallow_flood", importance=3,
    )
    return result


def can_help_at_marsh_fire(dragon):
    return (
        dragon.tribe == "MudWing"
        and dragon.status == "Alive"
        and dragon.health == "Healthy"
        and dragon.role != "Dragonet"
    )


def try_marsh_fire(world):
    if (
        not has_mud_wallow(world)
        or world.pending_choice is not None
        or world.moon < world.world_flags.get("last_marsh_fire_moon", -6) + 6
    ):
        return False

    candidates = [dragon for dragon in world.dragons if can_help_at_marsh_fire(dragon)]
    if not candidates or random.random() >= 0.08:
        return False

    options = []
    for resistant in (True, False):
        volunteers = [dragon for dragon in candidates if dragon.fire_resistant == resistant]
        if volunteers:
            volunteer = random.choice(volunteers)
            risk = "lower burn risk" if resistant else "higher burn risk"
            options.append({
                "id": f"rescue_{volunteer.id}",
                "text": f"Send {volunteer.name} to clear the reed beds ({risk})",
            })
    options.append({"id": "perimeter", "text": "Evacuate from the perimeter and abandon the food caches"})

    world.pending_choice = {
        "type": "mudwing_marsh_fire",
        "location": "mud_wallow",
        "text": (
            "A dry spell has left the reed beds brittle. "
            "Fire is spreading toward the marsh paths and food caches."
        ),
        "options": options,
    }
    world.world_flags["last_marsh_fire_moon"] = world.moon
    return True


def resolve_marsh_fire(world, option_id):
    choice = world.pending_choice
    options = {option["id"] for option in choice["options"]}
    if option_id not in options:
        return "That marsh fire response is unavailable."

    volunteer = next(
        (
            dragon for dragon in world.dragons
            if f"rescue_{dragon.id}" == option_id and can_help_at_marsh_fire(dragon)
        ),
        None,
    )
    food_lost = min(world.food_stores, 6 if volunteer else 12)
    world.food_stores -= food_lost
    if volunteer:
        result = f"{volunteer.name} helped evacuate the reed beds. The tribe lost {food_lost} food."
        if random.random() < (0.10 if volunteer.fire_resistant else 0.45):
            add_injury(world, volunteer, text=f"{volunteer.name} suffered burns during the marsh fire.")
        elif volunteer.fire_resistant:
            result += f" {volunteer.name}'s fire-resistant scales helped protect them from burns."
    else:
        result = f"The tribe evacuated along the perimeter and lost {food_lost} food to the marsh fire."

    log_event(
        world,
        result,
        involved_ids=[volunteer.id] if volunteer else [],
        event_type="mudwing_marsh_fire",
        importance=4,
    )
    return result
