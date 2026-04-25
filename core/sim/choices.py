from core.sim.choice_handlers.leadership import handle_leader_decision
from core.sim.choice_handlers.diplomacy import (
    handle_diplomatic_choice,
    handle_tribal_policy_choice,
    handle_incoming_diplomacy_choice,
)
from core.sim.choice_handlers.border import (
    handle_border_sighting,
    handle_border_violation,
    handle_aid_delivery,
)
from core.sim.choice_handlers.personal import handle_personal_choice


def get_region_intensity(world, region):
    if not region:
        return 0.0

    activity = world.region_activity.get(region, 0)

    if activity >= 6:
        return 0.25
    elif activity >= 3:
        return 0.15
    elif activity >= 1:
        return 0.05
    else:
        return 0.0


def resolve_choice(world, option_id):
    choice = world.pending_choice
    if not choice:
        return

    choice_type = choice.get("type")

    if choice_type == "leader_decision":
        handle_leader_decision(world, option_id)

    elif choice_type == "diplomatic_choice":
        handle_diplomatic_choice(world, option_id)

    elif choice_type == "tribal_policy_choice":
        handle_tribal_policy_choice(world, option_id)

    elif choice_type == "incoming_diplomacy_choice":
        handle_incoming_diplomacy_choice(world, option_id)

    elif choice_type == "border_sighting":
        handle_border_sighting(world, option_id)

    elif choice_type == "border_violation":
        handle_border_violation(world, option_id)

    elif choice_type == "aid_delivery":
        handle_aid_delivery(world, option_id)

    elif choice_type in {
        "injured_patrol_choice",
        "rival_confrontation_choice",
    }:
        handle_personal_choice(world, option_id)

    world.pending_choice = None