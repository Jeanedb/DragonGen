import random

from core.sim.choice_handlers.leadership import handle_leader_decision
from core.sim.choice_handlers.conversation import handle_ai_conversation_choice
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
from core.sim.logging import log_event


def _hatchery_condition_label(score):
    if score >= 80:
        return "Healthy"
    if score >= 60:
        return "Stable"
    if score >= 40:
        return "Concerning"
    return "Critical"


def handle_hatchery_incident(world, option_id):
    choice = getattr(world, "pending_choice", None) or {}
    egg_id = choice.get("egg_id")
    egg = next(
        (
            candidate
            for candidate in getattr(world, "eggs", [])
            if candidate.get("egg_id") == egg_id
        ),
        None,
    )
    if egg is None:
        return

    parent_names = f"{egg.get('mother', 'Unknown')} and {egg.get('father', 'Unknown')}"
    score = int(egg.get("condition_score", 70))
    involved_ids = choice.get("involved_ids", [])

    if option_id == "call_healer":
        healer = next(
            (
                dragon
                for dragon in getattr(world, "dragons", [])
                if getattr(dragon, "status", "") == "Alive"
                and getattr(dragon, "role", "") == "Healer"
            ),
            None,
        )
        improvement = 20 if healer else 9
        score += improvement
        if healer:
            if healer.id not in involved_ids:
                involved_ids.append(healer.id)
            result_text = (
                f"{healer.name} treated the egg of {parent_names}, and its condition improved."
            )
        else:
            result_text = (
                f"The tribe carefully examined the egg of {parent_names}, but no healer "
                "was available to provide expert care."
            )
        egg["last_healer_check_moon"] = getattr(world, "moon", 0)

    elif option_id == "warm_nest":
        score += 13
        egg["reinforced_until_moon"] = getattr(world, "moon", 0) + 1
        result_text = (
            f"The egg of {parent_names} was moved to a warm, protected nest and stabilized."
        )

    elif option_id == "assist_hatching":
        score += 11
        result_text = (
            f"The tribe carefully assisted the egg of {parent_names} through its difficult hatching."
        )

    else:
        natural_change = random.choice([-10, -6, 4, 8])
        score += natural_change
        if natural_change >= 0:
            result_text = (
                f"The tribe allowed the egg of {parent_names} to recover naturally, and it steadied."
            )
        else:
            result_text = (
                f"The tribe avoided interfering with the egg of {parent_names}, but its condition worsened."
            )

    egg["condition_score"] = max(0, min(100, score))
    egg["condition"] = _hatchery_condition_label(egg["condition_score"])
    egg["pending_incident"] = False
    egg["care_actions_received"] = egg.get("care_actions_received", 0) + 1

    log_event(
        world,
        result_text,
        involved_ids=involved_ids,
        event_type="hatchery",
        importance=4,
    )


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

    elif choice_type == "ai_conversation_choice":
        handle_ai_conversation_choice(world, option_id)

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

    elif choice_type == "hatchery_incident":
        handle_hatchery_incident(world, option_id)

    world.pending_choice = None
