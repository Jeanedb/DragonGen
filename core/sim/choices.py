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
from core.sim.injury import add_injury
from core.sim.logging import log_event
from core.sim.memory import Memory, add_memory, current_moon


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


def handle_hunting_crisis(world, option_id):
    choice = getattr(world, "pending_choice", None) or {}
    injured_id = choice.get("injured_id")
    party_ids = choice.get("party_ids", [])
    party = [
        dragon
        for dragon in getattr(world, "dragons", [])
        if getattr(dragon, "id", None) in party_ids
        and getattr(dragon, "status", "") == "Alive"
    ]
    injured = next(
        (dragon for dragon in party if getattr(dragon, "id", None) == injured_id),
        None,
    )
    if injured is None:
        return

    injured.health = "Injured"
    add_memory(
        injured,
        Memory(
            type="injured_on_hunt",
            moon=current_moon(world),
            importance=4,
            reflection_weight=1.2,
            tags=["hunting", "injury", "danger"],
        ),
    )

    if not hasattr(world, "world_flags") or world.world_flags is None:
        world.world_flags = {}
    fatigue = world.world_flags.setdefault("dragon_fatigue", {})
    if not isinstance(fatigue, dict):
        fatigue = {}
        world.world_flags["dragon_fatigue"] = fatigue

    if option_id == "retreat_together":
        for dragon in party:
            key = str(dragon.id)
            fatigue[key] = max(0, int(fatigue.get(key, 0)) - 1)
            if dragon is not injured:
                dragon.trust[injured.id] = dragon.trust.get(injured.id, 0) + 0.15
        result_text = (
            f"The hunters abandoned the prey and brought {injured.name} home together. "
            "The expedition gained nothing more, but no one was left behind."
        )

    elif option_id == "stabilize_injured":
        healer = next(
            (
                dragon
                for dragon in party
                if str(getattr(dragon, "role", "")).lower() == "healer"
            ),
            None,
        )
        if healer is None:
            healer = next(
                (
                    dragon
                    for dragon in getattr(world, "dragons", [])
                    if getattr(dragon, "status", "") == "Alive"
                    and str(getattr(dragon, "role", "")).lower() == "healer"
                ),
                None,
            )

        if healer is not None and healer is not injured:
            injured.trust[healer.id] = injured.trust.get(healer.id, 0) + 0.6
            healer.trust[injured.id] = healer.trust.get(injured.id, 0) + 0.25
            add_memory(
                injured,
                Memory(
                    type="saved_by",
                    moon=current_moon(world),
                    other_id=healer.id,
                    importance=5,
                    reflection_weight=1.5,
                    tags=["hunting", "injury", "rescue", "gratitude"],
                ),
            )
            result_text = (
                f"{healer.name} stabilized {injured.name} and guided the party home. "
                "The rescue forged a lasting bond between them."
            )
        else:
            result_text = (
                f"The party protected {injured.name} until help arrived. The recovery "
                "will take time, but the hunters prevented the injury from worsening."
            )

    else:  # press_the_hunt
        for dragon in party:
            key = str(dragon.id)
            fatigue[key] = min(6, int(fatigue.get(key, 0)) + 1)

        active_hunters = [dragon for dragon in party if dragon is not injured]
        if active_hunters and random.random() < 0.55:
            extra_food = random.randint(15, 28)
            world.food_stores = getattr(world, "food_stores", 0) + extra_food
            leader = random.choice(active_hunters)
            leader.reputation["bold"] = leader.reputation.get("bold", 0) + 0.3
            result_text = (
                f"Part of the group carried {injured.name} home while the others continued. "
                f"The gamble succeeded, bringing back {extra_food} additional food."
            )
        else:
            world.tension += 0.15
            if active_hunters:
                second_injury = random.choice(active_hunters)
                second_injury.health = "Injured"
                add_memory(
                    second_injury,
                    Memory(
                        type="injured_on_hunt",
                        moon=current_moon(world),
                        importance=4,
                        tags=["hunting", "injury", "recklessness"],
                    ),
                )
                result_text = (
                    f"The party continued despite {injured.name}'s injury, but the prey escaped "
                    f"and {second_injury.name} was also hurt. The decision unsettled the tribe."
                )
            else:
                result_text = (
                    f"The attempt to continue collapsed. {injured.name} returned without the prey, "
                    "and the failed gamble unsettled the tribe."
                )

    log_event(
        world,
        result_text,
        involved_ids=[dragon.id for dragon in party],
        event_type="hunt",
        importance=5,
    )


def _get_border_flags(world):
    if not hasattr(world, "world_flags") or world.world_flags is None:
        world.world_flags = {}
    flags = world.world_flags
    flags.setdefault("border_security", 55)
    flags.setdefault("border_intel", 25)
    flags.setdefault("border_threat", 20)
    return flags


def _adjust_border(world, security=0, intel=0, threat=0):
    flags = _get_border_flags(world)
    for key, change in {
        "border_security": security,
        "border_intel": intel,
        "border_threat": threat,
    }.items():
        flags[key] = max(0, min(100, int(flags.get(key, 0)) + change))


def handle_border_crisis(world, option_id):
    choice = getattr(world, "pending_choice", None) or {}
    incident = choice.get("incident", "border_incursion")
    party_ids = choice.get("party_ids", [])
    party = [
        dragon
        for dragon in getattr(world, "dragons", [])
        if getattr(dragon, "id", None) in party_ids
        and getattr(dragon, "status", "") == "Alive"
    ]
    result_text = "The border situation passed without a clear resolution."

    if option_id == "question_stranger":
        _adjust_border(world, intel=9, threat=-3)
        result_text = (
            "The patrol questioned the stranger carefully and confirmed several useful details "
            "about activity beyond the border before escorting them away."
        )
    elif option_id == "escort_away":
        _adjust_border(world, security=6, threat=-5)
        result_text = "The patrol firmly escorted the stranger out of tribal territory without violence."
    elif option_id == "detain_stranger":
        _adjust_border(world, security=8, intel=3, threat=-1)
        world.tension = getattr(world, "tension", 0) + 0.06
        result_text = (
            "The stranger was detained while the tribe investigated. The border feels more secure, "
            "but the decision created unease."
        )

    elif option_id == "offer_sanctuary":
        _adjust_border(world, security=-3, intel=5, threat=2)
        for dragon in party:
            dragon.reputation["kind"] = dragon.reputation.get("kind", 0) + 0.18
        result_text = (
            "The wounded outsider was brought into the village under guard. Their gratitude may "
            "become valuable, though the tribe has accepted some risk."
        )
    elif option_id == "limited_aid":
        cost = min(6, max(0, int(getattr(world, "food_stores", 0))))
        world.food_stores = max(0, getattr(world, "food_stores", 0) - cost)
        _adjust_border(world, intel=3, threat=-2)
        result_text = (
            f"The patrol provided {cost} food and basic aid before directing the outsider onward. "
            "Compassion was shown without opening the border."
        )
    elif option_id == "turn_away":
        _adjust_border(world, security=3, threat=1)
        world.tension = getattr(world, "tension", 0) + 0.04
        result_text = "The outsider was turned away. The border remained closed, but the decision troubled some dragons."

    elif option_id == "lay_trap":
        if random.random() < 0.62:
            _adjust_border(world, security=9, intel=7, threat=-9)
            result_text = "The trap exposed the observers and drove them from the border, revealing how they operated."
        else:
            _adjust_border(world, security=-5, threat=8)
            injured = random.choice(party) if party else None
            if injured is not None and add_injury(world, injured):
                result_text = f"The suspected spies anticipated the trap and escaped. {injured.name} was injured in the pursuit."
            else:
                result_text = "The suspected spies anticipated the trap and escaped, leaving the border more exposed."
    elif option_id == "reinforce_routes":
        _adjust_border(world, security=8, threat=-4)
        result_text = "The tribe reinforced the watched approaches and quietly denied the spies useful access."
    elif option_id == "observe_spies":
        _adjust_border(world, intel=12, threat=3)
        result_text = "The patrol allowed the observers to remain long enough to learn their routes and habits."

    elif option_id == "rescue_egg":
        if not hasattr(world, "eggs") or world.eggs is None:
            world.eggs = []
        world.eggs.append({
            "mother": "Unknown",
            "father": "Unknown",
            "age": 0,
            "hatch_time": random.randint(4, 7),
            "caretaker": None,
            "condition": "Concerning",
            "condition_score": 48,
            "movement": "rests quietly",
        })
        _adjust_border(world, intel=2)
        result_text = "The abandoned egg was carried carefully to the hatchery. Its origins remain unknown."
    elif option_id == "search_for_parents":
        _adjust_border(world, intel=10, threat=3)
        result_text = (
            "The patrol searched the surrounding territory and uncovered fresh tracks, but the egg's "
            "parents were nowhere to be found."
        )
    elif option_id == "leave_egg":
        _adjust_border(world, security=1)
        world.tension = getattr(world, "tension", 0) + 0.05
        result_text = "The patrol left the egg untouched. Some dragons continue to question whether that was right."

    elif option_id == "send_supplies":
        available = max(0, int(getattr(world, "food_stores", 0)))
        cost = min(12, available)
        world.food_stores = available - cost
        if cost >= 8:
            _adjust_border(world, intel=5, threat=-5)
            for dragon in party:
                dragon.reputation["kind"] = dragon.reputation.get("kind", 0) + 0.2
            result_text = f"The tribe sent {cost} food in aid. The gesture strengthened trust beyond the border."
        else:
            _adjust_border(world, threat=-1)
            result_text = f"The tribe sent the {cost} food it could spare, though the limited aid fell short of what was needed."
    elif option_id == "send_escort":
        fatigue = _get_border_flags(world).setdefault("dragon_fatigue", {})
        if not isinstance(fatigue, dict):
            fatigue = {}
            world.world_flags["dragon_fatigue"] = fatigue
        for dragon in party:
            key = str(dragon.id)
            fatigue[key] = min(6, int(fatigue.get(key, 0)) + 1)
        _adjust_border(world, security=-2, intel=7, threat=-4)
        result_text = "The patrol escorted the messengers home and returned with valuable knowledge of the neighbouring territory."
    elif option_id == "refuse_aid":
        _adjust_border(world, security=4, threat=3)
        result_text = "The tribe refused the request and concentrated its strength at home, damaging goodwill beyond the border."

    elif option_id == "engage_group":
        if random.random() < 0.58:
            _adjust_border(world, security=10, threat=-10)
            result_text = "The patrol confronted the armed group decisively and forced it away from tribal territory."
        else:
            _adjust_border(world, security=-7, threat=11)
            injured = random.choice(party) if party else None
            if injured is not None and add_injury(world, injured):
                result_text = f"The confrontation went badly. The group escaped and {injured.name} was injured."
            else:
                result_text = "The confrontation went badly, and the armed group escaped with a better understanding of the border."
    elif option_id == "shadow_group":
        _adjust_border(world, intel=11, threat=-3)
        result_text = "The patrol followed the armed group unseen and learned where it entered the region."
    elif option_id == "withdraw_report":
        _adjust_border(world, security=3, intel=4, threat=2)
        result_text = "The patrol withdrew safely and delivered a careful warning, avoiding a fight but leaving the group at large."

    elif option_id == "fortify_border":
        _adjust_border(world, security=12, threat=-7)
        result_text = "The tribe fortified vulnerable crossings and weathered the surge in hostile activity."
    elif option_id == "counter_patrol":
        if random.random() < 0.6:
            _adjust_border(world, security=7, intel=8, threat=-13)
            result_text = "A counter-patrol found the source of the incursions and drove it away from the territory."
        else:
            _adjust_border(world, security=-5, threat=8)
            result_text = "The counter-patrol failed to locate the intruders, leaving the border stretched and uncertain."
    elif option_id == "close_routes":
        _adjust_border(world, security=6, intel=-5, threat=-4)
        result_text = "The tribe temporarily closed its outer routes, increasing safety at the cost of awareness and movement."

    for dragon in party:
        add_memory(
            dragon,
            Memory(
                type=f"border_choice_{incident}",
                moon=current_moon(world),
                importance=4,
                reflection_weight=1.2,
                tags=["border", "decision", incident],
            ),
        )

    log_event(
        world,
        result_text,
        involved_ids=[dragon.id for dragon in party],
        event_type="border",
        importance=5,
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


def _format_choice_outcome(new_events, handler_result=None):
    """Build the short player-facing consequence summary for a choice."""
    texts = []

    if isinstance(handler_result, str) and handler_result.strip():
        texts.append(handler_result.strip())

    for event in new_events:
        if not isinstance(event, dict):
            continue
        text = str(event.get("text", "")).strip()
        if text and text not in texts:
            texts.append(text)

    if not texts:
        return "The decision was carried out. No immediate consequence was recorded."

    # Most choices produce one to three events.  Keep an exceptional chain
    # readable without allowing the popup to become an endless event log.
    visible = texts[:4]
    lines = [f"• {text}" for text in visible]
    if len(texts) > len(visible):
        lines.append(
            f"• {len(texts) - len(visible)} additional effect(s) were recorded in the chronicle."
        )
    return "\n".join(lines)


def resolve_choice(world, option_id):
    choice = world.pending_choice
    if not choice:
        return "There is no longer a pending decision to resolve."

    choice_type = choice.get("type")
    event_log = getattr(world, "event_log", None)
    event_start = len(event_log) if isinstance(event_log, list) else 0
    handler_result = None

    if choice_type == "leader_decision":
        handler_result = handle_leader_decision(world, option_id)

    elif choice_type == "ai_conversation_choice":
        handler_result = handle_ai_conversation_choice(world, option_id)

    elif choice_type == "diplomatic_choice":
        handler_result = handle_diplomatic_choice(world, option_id)

    elif choice_type == "tribal_policy_choice":
        handler_result = handle_tribal_policy_choice(world, option_id)

    elif choice_type == "incoming_diplomacy_choice":
        handler_result = handle_incoming_diplomacy_choice(world, option_id)

    elif choice_type == "border_sighting":
        handler_result = handle_border_sighting(world, option_id)

    elif choice_type == "border_violation":
        handler_result = handle_border_violation(world, option_id)

    elif choice_type == "aid_delivery":
        handler_result = handle_aid_delivery(world, option_id)

    elif choice_type in {
        "injured_patrol_choice",
        "rival_confrontation_choice",
    }:
        handler_result = handle_personal_choice(world, option_id)

    elif choice_type == "hatchery_incident":
        handler_result = handle_hatchery_incident(world, option_id)

    elif choice_type == "hunting_crisis":
        handler_result = handle_hunting_crisis(world, option_id)

    elif choice_type == "border_crisis":
        handler_result = handle_border_crisis(world, option_id)

    else:
        handler_result = "The decision type was not recognized. No consequence was applied."

    world.pending_choice = None

    event_log = getattr(world, "event_log", None)
    new_events = event_log[event_start:] if isinstance(event_log, list) else []
    return _format_choice_outcome(new_events, handler_result)
