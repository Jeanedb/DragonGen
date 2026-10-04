from data.tribe_data import get_culture_value


PERSONALITY_BEHAVIOR_MODIFIERS = {
    "Brave": {
        "aggression": 0.15,
        "cooperation": 0.05,
        "hierarchy": -0.05,
        "reputation_importance": 0.10,
        "family_loyalty": 0.10,
        "forgiveness": 0.00,
    },

    "Clever": {
        "aggression": -0.05,
        "cooperation": 0.05,
        "hierarchy": -0.05,
        "reputation_importance": 0.05,
        "family_loyalty": 0.00,
        "forgiveness": 0.05,
    },

    "Kind": {
        "aggression": -0.20,
        "cooperation": 0.20,
        "hierarchy": 0.00,
        "reputation_importance": -0.10,
        "family_loyalty": 0.15,
        "forgiveness": 0.20,
    },

    "Loyal": {
        "aggression": -0.05,
        "cooperation": 0.20,
        "hierarchy": 0.10,
        "reputation_importance": 0.00,
        "family_loyalty": 0.20,
        "forgiveness": 0.10,
    },

    "Suspicious": {
        "aggression": 0.10,
        "cooperation": -0.15,
        "hierarchy": -0.10,
        "reputation_importance": 0.10,
        "family_loyalty": 0.05,
        "forgiveness": -0.20,
    },

    "Moody": {
        "aggression": 0.15,
        "cooperation": -0.10,
        "hierarchy": -0.05,
        "reputation_importance": 0.10,
        "family_loyalty": 0.00,
        "forgiveness": -0.10,
    },

    "Ambitious": {
        "aggression": 0.20,
        "cooperation": -0.05,
        "hierarchy": 0.10,
        "reputation_importance": 0.20,
        "family_loyalty": -0.05,
        "forgiveness": -0.10,
    },

    "Playful": {
        "aggression": -0.10,
        "cooperation": 0.10,
        "hierarchy": -0.15,
        "reputation_importance": -0.10,
        "family_loyalty": 0.05,
        "forgiveness": 0.15,
    },
}


def get_personality_modifier(dragon, behavior_name):
    personality = getattr(dragon, "personality", "")

    personality_data = PERSONALITY_BEHAVIOR_MODIFIERS.get(
        personality,
        {}
    )

    return personality_data.get(behavior_name, 0.0)


def get_behavior_score(dragon, behavior_name, default=0.5):
    culture_value = get_culture_value(
        getattr(dragon, "tribe", "Mixed"),
        behavior_name,
        default
    )

    personality_modifier = get_personality_modifier(
        dragon,
        behavior_name
    )

    score = culture_value + personality_modifier

    return max(0.0, min(1.0, score))