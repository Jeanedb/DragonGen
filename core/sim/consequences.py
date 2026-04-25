from core.sim.logging import log_event


def schedule_consequence(world, delay, data):
    if not hasattr(world, "scheduled_events"):
        world.scheduled_events = []

    world.scheduled_events.append({
        "trigger_moon": world.moon + delay,
        "data": data
    })


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