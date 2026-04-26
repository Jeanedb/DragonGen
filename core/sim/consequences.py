import random
from core.sim.logging import log_event
from core.sim.politics import get_random_foreign_tribe


def schedule_consequence(world, delay, data):
    if not hasattr(world, "scheduled_events"):
        world.scheduled_events = []

    world.scheduled_events.append({
        "trigger_moon": world.moon + delay,
        "data": data
    })

def cancel_scheduled_event(world, event_type, dragon_id):
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
        if world.moon >= event["trigger_moon"]:
            resolve_scheduled_event(world, event["data"])
        else:
            remaining.append(event)

    world.scheduled_events = remaining


def resolve_scheduled_event(world, data):
    if data["type"] == "abandoned_return":
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

        if resentment < 3:
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

        if resentment >= 5 and random.random() < 0.6:
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

        if resentment >= 5:
            chance += 0.15

        if dragon.health == "Injured":
            chance += 0.10

        if random.random() > chance:
            return

        old_tribe = dragon.tribe
        new_tribe = get_random_foreign_tribe(world)

        if not new_tribe:
            return

        dragon.tribe = new_tribe
        dragon.role = "Defector"
        dragon.rank = "Outsider"

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

        schedule_consequence(world, delay=5, data={
            "type": "defector_returns",
            "dragon_id": dragon.id,
            "target_id": caused_by.id
        })
        
    elif data["type"] == "defector_returns":
        dragon = next((d for d in world.dragons if d.id == data["dragon_id"]), None)
        target = next((d for d in world.dragons if d.id == data["target_id"]), None)

        if not dragon or not target:
            return

        if dragon.status != "Alive" or target.status != "Alive":
            return

        if dragon.role != "Defector":
            return

        if target.id not in dragon.rivals:
            dragon.rivals.append(target.id)
        if dragon.id not in target.rivals:
            target.rivals.append(dragon.id)

        dragon.resentment[target.id] = dragon.resentment.get(target.id, 0) + 2

        log_event(
            world,
            f"{dragon.name}, now of the {dragon.tribe}s, was sighted again near the territory. Their hostility toward {target.name} has only grown.",
            involved_ids=[dragon.id, target.id],
            event_type="defector_return",
            importance=5,
            cause="A past defection has come back to haunt the tribe"
        )

        # 🔥 confrontation escalation
        if random.random() < 0.4:
            log_event(
                world,
                f"{dragon.name} actively confronted {target.name} during the sighting.",
                involved_ids=[dragon.id, target.id],
                event_type="defector_confrontation",
                importance=5
            )

            dragon.resentment[target.id] = dragon.resentment.get(target.id, 0) + 2
            target.resentment[dragon.id] = target.resentment.get(dragon.id, 0) + 2

        # 🔥 injury escalation
        if random.random() < 0.15:
            victim = random.choice([dragon, target])

            victim.health = "Injured"

            log_event(
                world,
                f"{victim.name} was injured during the encounter with {dragon.name}.",
                involved_ids=[dragon.id, target.id, victim.id],
                event_type="defector_injury",
                importance=6
            )