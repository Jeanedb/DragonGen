import random
from core.sim.relationship_events import try_relationship_event
from core.sim.locations import shared_location, get_event_location_text


def get_conversation_pressure(a, b):
    trust = a.trust.get(b.id, 0)
    resentment = a.resentment.get(b.id, 0)
    perception = a.perceived_reputation.get(b.id, 0)

    score = trust - (resentment * 1.25) + (perception * 0.75)

    return score, trust, resentment, perception


def get_relationship_state(trust, resentment, perception):
    score = trust - (resentment * 1.25) + (perception * 0.75)

    if score >= 3:
        return "bonding"
    elif score >= 0.5:
        return "stable"
    elif score <= -3:
        return "hostile"
    elif score <= -0.5:
        return "deteriorating"
    else:
        return "uncertain"


def _has_memory(dragon, memory_type, other_id):
    return any(
        isinstance(memory, (tuple, list))
        and len(memory) >= 2
        and memory[0] == memory_type
        and memory[1] == other_id
        for memory in getattr(dragon, "memory_flags", [])
    )


def _conversation_context(initiator, target, state):
    state_labels = {
        "bonding": "A strong or growing bond",
        "stable": "Generally steady",
        "hostile": "Openly hostile",
        "deteriorating": "Growing strained",
        "uncertain": "Uncertain",
    }
    known_history = []

    if getattr(initiator, "mate_id", None) == target.id or getattr(target, "mate_id", None) == initiator.id:
        known_history.append("mates")
    if target.id in getattr(initiator, "friends", []) or initiator.id in getattr(target, "friends", []):
        known_history.append("friends")
    if target.id in getattr(initiator, "rivals", []) or initiator.id in getattr(target, "rivals", []):
        known_history.append("rivals")
    if _has_memory(initiator, "saved_by", target.id):
        known_history.append(f"{target.name} previously stayed to help {initiator.name}")
    if _has_memory(initiator, "abandoned_by", target.id):
        known_history.append(f"{initiator.name} remembers being left by {target.name}")

    return [
        {
            "label": "Dragons involved",
            "value": f"{initiator.name} and {target.name}",
        },
        {
            "label": "Current dynamic",
            "value": state_labels.get(state, "Uncertain"),
        },
        {
            "label": "Known history",
            "value": ", ".join(known_history) if known_history else "No defining history recorded",
        },
    ]
    


def create_ai_conversation_choice(world):
    living = [
        d for d in world.dragons
        if d.status == "Alive" and d.role != "Dragonet"
    ]

    if len(living) < 2:
        return False

    candidates = []

    for a in living:
        for b in living:
            if a.id == b.id:
                continue

            score, trust, resentment, perception = get_conversation_pressure(a, b)

            weight = abs(score) + trust + resentment + abs(perception)

            state = get_relationship_state(trust, resentment, perception)

            if try_relationship_event(world, a, b, state):
                return True

            if state in {"bonding", "hostile"}:
                weight *= 1.4

            # 🔥 LOCATION BIAS (must happen BEFORE append)
            if shared_location(a, b):
                weight *= 1.4
            else:
                weight *= 0.7

            if weight >= 1.5:
                candidates.append((a, b, score, weight))

    if not candidates:
        return False

    choices = [(a, b, score) for a, b, score, _ in candidates]
    weights = [w for _, _, _, w in candidates]

    initiator, target, score = random.choices(choices, weights=weights, k=1)[0]

    reason = None

    if score >= 1.5:
        mood = "friendly"

        if initiator.trust.get(target.id, 0) >= 3:
            reason = "strengthen_bond"
        else:
            reason = "build_trust"

    elif score <= -1.5:
        mood = "tense"

        if initiator.resentment.get(target.id, 0) >= 3:
            reason = "confront_past"
        else:
            reason = "growing_tension"

    else:

        mood = "neutral"
        reason = "unclear"

    loc = get_event_location_text(initiator, target)

    if reason == "strengthen_bond":
        text = f"{initiator.name} seeks out {target.name}{loc}, wanting to reinforce their bond."

    elif reason == "build_trust":
        text = f"{initiator.name} approaches {target.name}{loc}, trying to build trust."

    elif reason == "confront_past":
        text = f"{initiator.name} seeks out {target.name}{loc} to address something that hasn’t been resolved."

    elif reason == "growing_tension":
        text = f"{initiator.name} approaches {target.name}{loc}, tension clearly building between them."

    else:
        text = f"{initiator.name} asks to speak with {target.name}{loc}. The reason is unclear."
    world.pending_choice = {

        "reason": reason,
        "type": "ai_conversation_choice",
        "conversation_mood": mood,
        "involved_ids": [initiator.id, target.id],
        "text": text,
        "context": _conversation_context(initiator, target, get_relationship_state(
            initiator.trust.get(target.id, 0),
            initiator.resentment.get(target.id, 0),
            initiator.perceived_reputation.get(target.id, 0),
        )),
        "options": [
            {
                "id": "hear_them_out",
                "text": f"{target.name} hears {initiator.name} out calmly.",
            },
            {
                "id": "reassure",
                "text": f"{target.name} tries to reassure {initiator.name}.",
            },
            {
                "id": "challenge",
                "text": f"{target.name} challenges what {initiator.name} is saying.",
            },
            {
                "id": "dismiss",
                "text": f"{target.name} dismisses the conversation.",
            },
        ],
    }

    return True
