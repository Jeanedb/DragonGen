from core.sim.logging import log_event
from core.sim.politics import shift_relation    



def handle_border_sighting(world, option_id):
    choice = world.pending_choice
    tribe = choice.get("tribe")

    if not tribe:
        world.pending_choice = None
        return

    if tribe not in world.tribal_incidents:
        world.tribal_incidents[tribe] = []

    if option_id == "observe":
        shift_relation(world, tribe, 1)
        log_event(
            world,
            f"The tribe kept watch on the {tribe}s from a distance without escalating the encounter.",
            event_type="politics",
            importance=2
        )
        world.tribal_incidents[tribe].append("Border patrol was observed")

    elif option_id == "approach":
        shift_relation(world, tribe, -1)
        log_event(
            world,
            f"The tribe approached the {tribe} patrol and questioned their presence.",
            event_type="politics",
            importance=2
        )
        world.tribal_incidents[tribe].append("Border patrol was questioned")

    elif option_id == "drive_off":
        shift_relation(world, tribe, -3)
        world.tension += 0.2
        log_event(
            world,
            f"The tribe drove off the {tribe} patrol forcefully, worsening tensions.",
            event_type="politics",
            importance=3
        )
        world.tribal_incidents[tribe].append("Border patrol was driven off")

    world.tribal_incidents[tribe] = world.tribal_incidents[tribe][-5:]
    world.pending_choice = None
    return



def handle_border_violation(world, option_id):
    choice = world.pending_choice
    tribe = choice.get("tribe")

    if not tribe:
        world.pending_choice = None
        return

    if tribe not in world.tribal_incidents:
        world.tribal_incidents[tribe] = []

    if option_id == "ignore_tracks":
        log_event(
            world,
            f"The tribe chose not to respond immediately to signs of {tribe} movement near the border.",
            event_type="politics",
            importance=2
        )
        world.tribal_incidents[tribe].append("Border tracks were ignored")

    elif option_id == "investigate_tracks":
        shift_relation(world, tribe, -1)
        log_event(
            world,
            f"The tribe investigated suspicious tracks near the border, deepening mistrust slightly.",
            event_type="politics",
            importance=2
        )
        world.tribal_incidents[tribe].append("Border tracks were investigated")

    elif option_id == "respond_forcefully":
        shift_relation(world, tribe, -4)
        world.tension += 0.3
        log_event(
            world,
            f"The tribe prepared a forceful response to the suspected {tribe} incursion.",
            event_type="politics",
            importance=3
        )
        world.tribal_incidents[tribe].append("Border violation drew a forceful response")

    world.tribal_incidents[tribe] = world.tribal_incidents[tribe][-5:]
    world.pending_choice = None
    return

def handle_aid_delivery(world, option_id):
    choice = world.pending_choice
    tribe = choice.get("tribe")

    if not tribe:
        world.pending_choice = None
        return

    if tribe not in world.tribal_incidents:
        world.tribal_incidents[tribe] = []

    if option_id == "allow_aid":
        shift_relation(world, tribe, 3)
        log_event(
            world,
            f"The tribe allowed the {tribe}s to pass with their supplies, improving relations.",
            event_type="politics",
            importance=3
        )
        world.tribal_incidents[tribe].append("Aid delivery was allowed")

    elif option_id == "inspect_aid":
        shift_relation(world, tribe, 1)
        log_event(
            world,
            f"The tribe inspected the {tribe}s' supplies before allowing passage.",
            event_type="politics",
            importance=2
        )
        world.tribal_incidents[tribe].append("Aid delivery was inspected")

    elif option_id == "deny_aid":
        shift_relation(world, tribe, -4)
        world.tension += 0.2
        log_event(
            world,
            f"The tribe denied passage to the {tribe}s' aid convoy, worsening tensions.",
            event_type="politics",
            importance=3
        )
        world.tribal_incidents[tribe].append("Aid delivery was denied")

    world.tribal_incidents[tribe] = world.tribal_incidents[tribe][-5:]
    world.pending_choice = None
    return

