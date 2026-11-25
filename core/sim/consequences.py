import random
from core.sim.logging import log_event
from core.sim.membership import mark_departed
from core.sim.memory import Memory, add_memory


def schedule_consequence(world, delay, data):
    if not hasattr(world, "scheduled_events"):
        world.scheduled_events = []

    world.scheduled_events.append({
        "trigger_moon": world.moon + delay,
        "data": data
    })

def cancel_scheduled_event(world, event_type, dragon_id):
    if not hasattr(world, "scheduled_events"):
        world.scheduled_events = []
        return

    world.scheduled_events = [
        e for e in world.scheduled_events
        if not (
            e["data"].get("type") == event_type
            and e["data"].get("dragon_id") == dragon_id
        )
    ]


def process_scheduled_events(world):
    if not hasattr(world, "scheduled_events"):
        return

    remaining = []

    for event in world.scheduled_events:
        waits_for_choice = event["data"].get("type") == "defector_returns" and world.pending_choice is not None
        if world.moon >= event["trigger_moon"] and not waits_for_choice:
            resolve_scheduled_event(world, event["data"])
        else:
            remaining.append(event)

    world.scheduled_events = remaining


def resolve_scheduled_event(world, data):
    if data["type"] == "seawing_trench_supplies":
        world.food_stores += 5
        log_event(
            world,
            "The shore crew followed the marked route to the trench sled and recovered 5 food.",
            event_type="hunt",
            importance=3,
        )

    elif data["type"] == "abandoned_return":
        abandoned = next((d for d in world.dragons if d.id == data["abandoned"]), None)
        abandoner = next((d for d in world.dragons if d.id == data["abandoner"]), None)

        if not abandoned or not abandoner:
            return

        if abandoned.status != "Alive":
            return

        # escalate relationship
        if abandoner.id not in abandoned.rivals:
            abandoned.rivals.append(abandoner.id)

        abandoned.resentment[abandoner.id] = abandoned.resentment.get(abandoner.id, 0) + 2

        log_event(
            world,
            f"{abandoned.name} has not forgotten being left behind by {abandoner.name}. The tension between them resurfaces.",
            involved_ids=[abandoned.id, abandoner.id],
            event_type="delayed_consequence",
            importance=4
        )

    elif data["type"] == "possible_defection":
        dragon = next((d for d in world.dragons if d.id == data["dragon_id"]), None)
        caused_by = next((d for d in world.dragons if d.id == data["caused_by"]), None)

        if not dragon or not caused_by:
            return

        if dragon.status != "Alive":
            return

        if dragon.rank in {"Leader", "Deputy"}:
            return

        resentment = dragon.resentment.get(caused_by.id, 0)

        rep_score = (
            caused_by.reputation.get("kind", 0)
            + caused_by.reputation.get("reliable", 0)
            - caused_by.reputation.get("harsh", 0)
            - caused_by.reputation.get("unpredictable", 0)
        )

        adjusted_resentment = resentment - (rep_score * 0.5)

        if adjusted_resentment < 3:
            return

        # 🔥 WARNING STAGE (now correctly placed)
        if random.random() < 0.5:
            log_event(
                world,
                f"{dragon.name} has been distant lately. Something seems off.",
                involved_ids=[dragon.id],
                event_type="warning",
                importance=2,
                cause="Lingering resentment"
            )

        if adjusted_resentment >= 5 and random.random() < 0.6:
            log_event(
                world,
                f"{dragon.name} has been seen speaking with outsiders. Their loyalty may be wavering.",
                involved_ids=[dragon.id],
                event_type="serious_warning",
                importance=3,
                cause="Growing resentment and instability"
            )

        # Rare, but serious
        chance = 0.30

        if adjusted_resentment >= 5:
            chance += 0.15

        # world tension amplifies existing resentment
        world_tension = getattr(world, "tension", 0)

        if adjusted_resentment >= 3:
            chance += world_tension * 0.05

        if dragon.health == "Injured":
            chance += 0.10

        chance = max(0.05, min(0.85, chance))

        if random.random() > chance:
            return

        old_tribe = dragon.tribe
        home_tribe = world.tribe_name.removesuffix(" Tribe")
        destinations = [tribe for tribe in world.tribal_relations if tribe not in {old_tribe, home_tribe}]
        if not destinations:
            return

        new_tribe = random.choice(destinations)
        dragon.foreign_tribe = new_tribe
        dragon.role = "Defector"
        dragon.rank = "Outsider"
        mark_departed(world, dragon)
        add_memory(dragon, Memory("defected_after_betrayal", world.moon, caused_by.id, importance=6))
        add_memory(caused_by, Memory("tribemate_defected", world.moon, dragon.id, importance=6))

        old = old_tribe
        new = new_tribe

        # initialize if needed
        if new not in world.tribal_relations:
            world.tribal_relations[new] = 0

        if old not in world.tribal_relations:
            world.tribal_relations[old] = 0

        # defection creates distrust
        world.tribal_relations[new] -= 0.5
        world.tribal_relations[old] -= 0.2

        # increase global tension
        world.tension += 0.3

        dragon.resentment[caused_by.id] = dragon.resentment.get(caused_by.id, 0) + 3

        log_event(
            world,
            f"{dragon.name} left the {old_tribe}s and defected to the {new_tribe}s. The act has strained relations between the tribes.",
            involved_ids=[dragon.id, caused_by.id],
            event_type="defection",
            importance=6,
            cause="A personal betrayal escalated into political tension"
        )
        
        from core.sim.rumors import spread_rumor

        spread_rumor(world, dragon.id, caused_by.id, effect=-0.5)

        schedule_consequence(world, delay=6, data={
            "type": "defector_returns",
            "dragon_id": dragon.id,
            "target_id": caused_by.id
        })
        
    elif data["type"] == "defector_returns":
        dragon, target = returning_dragons(world, data)
        if not dragon or not target:
            return

        world.pending_choice = {
            "type": "defector_return_choice",
            "location": "border",
            "dragon_id": dragon.id,
            "target_id": target.id,
            "text": (
                f"{dragon.name} has returned to the boundary as a member of the {dragon.foreign_tribe}s. "
                f"They are still angry with {target.name} for leaving them on patrol and demand to speak."
            ),
            "options": [
                {"id": "hear_out", "text": "Let them talk at the border"},
                {"id": "turn_away", "text": "Turn the former tribemate away"},
            ],
        }


def returning_dragons(world, data):
    dragon = next(
        (d for d in world.dragons if d.id == data["dragon_id"] and d.status == "Departed"),
        None,
    )
    target = next(
        (d for d in world.dragons if d.id == data["target_id"] and d.status == "Alive"),
        None,
    )
    return dragon, target


def resolve_defector_return(world, option_id):
    dragon, target = returning_dragons(world, world.pending_choice)
    if not dragon or not target:
        return "The border meeting can no longer take place."

    if option_id == "hear_out":
        prior_resentment = dragon.resentment.get(target.id, 0)
        dragon.resentment[target.id] = max(0, prior_resentment - 2)
        target.trust[dragon.id] = target.trust.get(dragon.id, 0) + 0.5
        text = (
            f"{dragon.name} told {target.name} how it felt to be left behind. "
            f"{target.name} listened, and {dragon.name} returned to the {dragon.foreign_tribe}s with less resentment."
        )
        memories = ("heard_at_border", "heard_former_tribemate")
    elif option_id == "turn_away":
        dragon.resentment[target.id] = dragon.resentment.get(target.id, 0) + 2
        target.resentment[dragon.id] = target.resentment.get(dragon.id, 0) + 1
        if target.id not in dragon.rivals:
            dragon.rivals.append(target.id)
        if dragon.id not in target.rivals:
            target.rivals.append(dragon.id)
        relation = world.tribal_relations.get(dragon.foreign_tribe, 0)
        world.tribal_relations[dragon.foreign_tribe] = max(-100, relation - 2)
        text = (
            f"{target.name} refused to meet with {dragon.name}. "
            f"{dragon.name} left angry, and relations with the {dragon.foreign_tribe}s worsened."
        )
        memories = ("turned_away_at_border", "turned_away_former_tribemate")
    else:
        return "That response is unavailable."

    for member, other, kind in zip((dragon, target), (target, dragon), memories):
        add_memory(member, Memory(kind, world.moon, other.id, importance=6))
    log_event(
        world, text, involved_ids=[dragon.id, target.id], event_type="defector_return",
        importance=6,
    )
    if option_id == "hear_out":
        if prior_resentment <= 0:
            return f"{target.name} trusts {dragon.name} a little more. Both will remember the meeting."
        return f"{dragon.name}'s resentment toward {target.name} eased. Both will remember the meeting."
    return f"The rivalry deepened, and relations with the {dragon.foreign_tribe}s worsened. Both will remember the meeting."
