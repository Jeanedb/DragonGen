import random


def personality_from_event(event_type):
    mapping = {
        "friendship": "Kind",
        "family_bond": "Loyal",
        "parent_child": "Loyal",
        "rivalry": "Suspicious",
        "family_conflict": "Moody",
        "injury": "Moody",
        "leader_event": "Brave",
        "deputy_event": "Loyal",
        "death": "Moody",
        "choice_loyalty": "Loyal",
        "choice_abandonment": "Suspicious",
        "choice_restraint": "Clever",
        "choice_confrontation": "Brave",
    }
    return mapping.get(event_type)


def shift_personality(dragon, new_trait):
    if random.random() < 0.25 and dragon.personality != new_trait:
        old = dragon.personality
        dragon.personality = new_trait
        return old, new_trait
    return None, None


def log_event(world, text, involved_ids=None, event_type="general", importance=1):
    if involved_ids is None:
        involved_ids = []

    event = {
        "text": text,
        "involved_ids": involved_ids,
        "type": event_type,
        "moon": world.moon,
        "importance": importance,
    }

    world.event_log.append(event)

    if involved_ids:
        for d in world.dragons:
            if d.id in involved_ids:
                new_trait = personality_from_event(event_type)
                if new_trait:
                    old, new = shift_personality(d, new_trait)
                    if old:
                        world.event_log.append(
                            {
                                "text": f"{d.name} is becoming more {new.lower()} over time.",
                                "involved_ids": [d.id],
                                "type": "personality_shift",
                                "moon": world.moon,
                                "importance": 2,
                            }
                        )