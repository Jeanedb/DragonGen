import random

from core.sim.regions import (
    get_random_region,
    get_random_landmark,
    record_region_activity,
)
from core.sim.politics import get_random_foreign_tribe


def create_diplomatic_choice(world):
    tribe = get_random_foreign_tribe(world)
    if not tribe:
        return False

    score = world.tribal_relations.get(tribe, 0)

    recent_incidents = world.tribal_incidents.get(tribe, [])
    incident_text = " ".join(recent_incidents[-2:]).lower()

    # ---- Influence scenario based on recent diplomacy ----

    if "pressure" in incident_text or "patrol" in incident_text:
        scenario = random.choices(
            ["border_misunderstanding", "safe_passage", "wounded_outsider"],
            weights=[0.5, 0.2, 0.3]
        )[0]

    elif "peace" in incident_text or "aid" in incident_text:
        scenario = random.choices(
            ["safe_passage", "wounded_outsider", "border_misunderstanding"],
            weights=[0.5, 0.3, 0.2]
        )[0]

    else:
        # fallback to your original logic
        if score <= -40:
            scenario = random.choices(
                ["border_misunderstanding", "wounded_outsider", "safe_passage"],
                weights=[0.5, 0.3, 0.2]
            )[0]
 
        elif score <= -10:
            scenario = random.choices(
                ["border_misunderstanding", "wounded_outsider", "safe_passage"],
                weights=[0.4, 0.3, 0.3]
            )[0]

        elif score < 10:
            scenario = random.choice([
                "safe_passage",
                "wounded_outsider",
                "border_misunderstanding"
            ])

        else:
            scenario = random.choices(
                ["safe_passage", "wounded_outsider", "border_misunderstanding"],
                weights=[0.5, 0.3, 0.2]
            )[0]

    region = get_random_region(world, tribe)
    landmark = get_random_landmark(world, region)
    record_region_activity(world, region)

    if scenario == "safe_passage":

        if score <= -40:
            prompt_text = (
                f"A small group of {tribe}s appears near the edge of your territory under a flag of truce. "
                f"Relations are already hostile. They ask for safe passage. How should the tribe respond?"
            )
        elif score <= -10:
            prompt_text = (
                f"A small group of {tribe}s approaches the edge of your territory seeking safe passage. "
                f"Relations are uneasy. How should the tribe respond?"
            )
        elif score < 10:
            prompt_text = (
                f"A small group of {tribe}s approaches the edge of your territory seeking safe passage. "
                f"Relations are neutral. How should the tribe respond?"
            )
        else:
            prompt_text = (
                f"A small group of {tribe}s approaches in peace, asking to pass safely through nearby territory. "
                f"Relations are reasonably positive. How should the tribe respond?"
            )

        options = [
            {"id": "allow_passage", "text": "Allow them safe passage"},
            {"id": "refuse_passage", "text": "Refuse and turn them away"},
            {"id": "escort_passage", "text": "Escort them through your territory"},
        ]

    elif scenario == "wounded_outsider":

        prompt_text = (
            f"A wounded {tribe} is found near the edge of your territory at {landmark} in {region}, separated from their own kind. "
            f"How should the tribe respond?"
        )

        options = [
            {"id": "help_wounded", "text": "Help them recover"},
            {"id": "ignore_wounded", "text": "Leave them and move on"},
            {"id": "detain_wounded", "text": "Detain and question them"},
        ]

    else:

        prompt_text = (
            f"A patrol from the {tribe}s is spotted near your border. They claim they crossed by mistake. "
            f"How should the tribe respond?"
        )

        options = [
            {"id": "accept_explanation", "text": "Accept the explanation and let them leave"},
            {"id": "issue_warning", "text": "Warn them harshly and send them away"},
            {"id": "escalate_border", "text": "Escalate and challenge their presence"},
        ]

    

    world.pending_choice = {
        "type": "diplomatic_choice",
        "scenario": scenario,
        "tribe": tribe,
        "region": region,
        "landmark": landmark,
        "text": prompt_text,
        "options": options,
    }

    return True


def create_tribal_policy_choice(world):
    tribes = list(getattr(world, "tribal_relations", {}).keys())

    if not tribes:
        return False

    tribe = random.choice(tribes)
    score = world.tribal_relations.get(tribe, 0)

    if score <= -30:
        prompt_text = (
            f"The tribe has an opportunity to shape its stance toward the {tribe}s this moon. "
            f"Relations are already hostile. What approach should it take?"
        )
    elif score <= -10:
        prompt_text = (
            f"The tribe has an opportunity to shape its stance toward the {tribe}s this moon. "
            f"Relations are uneasy. What approach should it take?"
        )
    elif score < 10:
        prompt_text = (
            f"The tribe has an opportunity to shape its stance toward the {tribe}s this moon. "
            f"Relations are neutral. What approach should it take?"
        )
    else:
        prompt_text = (
            f"The tribe has an opportunity to shape its stance toward the {tribe}s this moon. "
            f"Relations are already fairly positive. What approach should it take?"
        )

    world.pending_choice = {
        "type": "tribal_policy_choice",
        "tribe": tribe,
        "text": prompt_text,
        "options": [
            {"id": "peace_gesture", "text": "Send a peace gesture"},
            {"id": "border_patrol", "text": "Increase border patrols"},
            {"id": "border_pressure", "text": "Apply border pressure"},
            {"id": "offer_aid", "text": "Offer practical aid"},
        ]
    }

    return True

def create_incoming_diplomacy_choice(world):
    tribes = [
        t for t in world.tribal_relations.keys()
        if world.diplomacy_cooldowns.get(t, 0) <= 0
    ]

    if not tribes:
        return False

    weights = []

    for t in tribes:
        score = world.tribal_relations.get(t, 0)
        weight = 1.0

        if score >= 10:
            weight += 1.0
        elif score <= -30:
            weight += 0.8
        elif score <= -10:
            weight += 0.4

        weights.append(weight)

    tribe = random.choices(tribes, weights=weights, k=1)[0]
    score = world.tribal_relations.get(tribe, 0)
    queen = world.tribal_leaders.get(tribe, f"Queen of the {tribe}s")
    trait = world.tribal_traits.get(tribe, "neutral")
    region = get_random_region(world, tribe)
    landmark = get_random_landmark(world, region)
    record_region_activity(world, region)

    if score <= -30:
        scenario = random.choices(
            ["warning", "truce_offer", "aid_request"],
            weights=[0.55, 0.25, 0.20]
        )[0]
    elif score <= -10:
        scenario = random.choices(
            ["warning", "truce_offer", "aid_request"],
            weights=[0.35, 0.35, 0.30]
        )[0]
    elif score < 10:
        scenario = random.choices(
            ["aid_request", "truce_offer", "warning"],
            weights=[0.35, 0.35, 0.30]
        )[0]
    else:
        scenario = random.choices(
            ["aid_request", "truce_offer", "warning"],
            weights=[0.45, 0.40, 0.15]
        )[0]

    if trait == "aggressive":
        warning_bias = 1.3
        truce_bias = 0.8
        aid_bias = 0.8
    elif trait == "cautious":
        warning_bias = 0.9
        truce_bias = 1.2
        aid_bias = 1.1
    elif trait == "opportunistic":
        warning_bias = 1.0
        truce_bias = 1.0
        aid_bias = 1.3
    else:
        warning_bias = truce_bias = aid_bias = 1.0

    if scenario == "aid_request":
        text = (
            f"{queen} of the {tribe}s has sent word requesting practical aid after hardship near {landmark} in {region}. "
            f"How should the tribe respond?"
        )
        options = [
            {"id": "grant_aid", "text": "Send aid"},
            {"id": "refuse_aid", "text": "Refuse"},
            {"id": "limited_aid", "text": "Send limited aid"},
        ]

    elif scenario == "warning":
        text = (
            f"{queen} of the {tribe}s has sent a stern warning about recent tensions near {landmark} in {region}. "
            f"How should the tribe respond?"
        )
        options = [
            {"id": "deescalate_warning", "text": "De-escalate diplomatically"},
            {"id": "ignore_warning", "text": "Ignore the warning"},
            {"id": "answer_firmly", "text": "Respond with a firm warning of your own"},
        ]

    else:  # truce_offer
        text = (
            f"{queen} of the {tribe}s has proposed a temporary truce to ease tensions. "
            f"How should the tribe respond?"
        )
        options = [
            {"id": "accept_truce", "text": "Accept the truce"},
            {"id": "reject_truce", "text": "Reject it"},
            {"id": "conditional_truce", "text": "Accept with conditions"},
        ]

    world.pending_choice = {
        "type": "incoming_diplomacy_choice",
        "tribe": tribe,
        "scenario": scenario,
        "region": region,
        "landmark": landmark,
        "text": text,
        "options": options,
    }

    world.diplomacy_cooldowns[tribe] = 3
    return True
