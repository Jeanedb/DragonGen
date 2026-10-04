TRIBE_DATA = {
    "SkyWing": {
        "menu_id": "skywing",
        "display_name": "SkyWing",
        "description": "Proud, fierce, and battle-ready.",
        "personality_bias": ["Brave", "Ambitious"],
        "culture": {
            "aggression": 0.80,
            "cooperation": 0.45,
            "hierarchy": 0.65,
            "reputation_importance": 0.70,
            "family_loyalty": 0.45,
            "forgiveness": 0.35,
        },
    },

    "SeaWing": {
        "menu_id": "seawing",
        "display_name": "SeaWing",
        "description": "Diplomatic, aquatic, and socially complex.",
        "personality_bias": ["Loyal", "Clever"],
        "culture": {
            "aggression": 0.40,
            "cooperation": 0.75,
            "hierarchy": 0.65,
            "reputation_importance": 0.60,
            "family_loyalty": 0.70,
            "forgiveness": 0.60,
        },
    },

    "RainWing": {
        "menu_id": "rainwing",
        "display_name": "RainWing",
        "description": "Colorful, emotional, and unpredictable.",
        "personality_bias": ["Kind", "Playful"],
        "culture": {
            "aggression": 0.20,
            "cooperation": 0.75,
            "hierarchy": 0.25,
            "reputation_importance": 0.30,
            "family_loyalty": 0.55,
            "forgiveness": 0.85,
        },
    },

    "SandWing": {
        "menu_id": "sandwing",
        "display_name": "SandWing",
        "description": "Harsh, political, and survival-minded.",
        "personality_bias": ["Ambitious", "Moody"],
        "culture": {
            "aggression": 0.65,
            "cooperation": 0.40,
            "hierarchy": 0.60,
            "reputation_importance": 0.80,
            "family_loyalty": 0.45,
            "forgiveness": 0.30,
        },
    },

    "IceWing": {
        "menu_id": "icewing",
        "display_name": "IceWing",
        "description": "Formal, hierarchical, and reputation-driven.",
        "personality_bias": ["Ambitious", "Suspicious"],
        "culture": {
            "aggression": 0.50,
            "cooperation": 0.55,
            "hierarchy": 0.95,
            "reputation_importance": 0.95,
            "family_loyalty": 0.60,
            "forgiveness": 0.25,
        },
    },

    "NightWing": {
        "menu_id": "nightwing",
        "display_name": "NightWing",
        "description": "Secretive, clever, and prophecy-haunted.",
        "personality_bias": ["Clever", "Suspicious"],
        "culture": {
            "aggression": 0.40,
            "cooperation": 0.40,
            "hierarchy": 0.60,
            "reputation_importance": 0.75,
            "family_loyalty": 0.45,
            "forgiveness": 0.35,
        },
    },

    "MudWing": {
        "menu_id": "mudwing",
        "display_name": "MudWing",
        "description": "Loyal, grounded, and family-focused.",
        "personality_bias": ["Loyal", "Kind"],
        "culture": {
            "aggression": 0.50,
            "cooperation": 0.90,
            "hierarchy": 0.50,
            "reputation_importance": 0.45,
            "family_loyalty": 0.95,
            "forgiveness": 0.70,
        },
    },

    "HiveWing": {
        "menu_id": "hivewing",
        "display_name": "HiveWing",
        "description": "Structured, ambitious, and hierarchy-focused.",
        "personality_bias": ["Ambitious", "Loyal"],
        "culture": {
            "aggression": 0.50,
            "cooperation": 0.70,
            "hierarchy": 0.95,
            "reputation_importance": 0.80,
            "family_loyalty": 0.55,
            "forgiveness": 0.35,
        },
    },

    "SilkWing": {
        "menu_id": "silkwing",
        "display_name": "SilkWing",
        "description": "Cooperative, expressive, and community-minded.",
        "personality_bias": ["Kind", "Playful"],
        "culture": {
            "aggression": 0.20,
            "cooperation": 0.90,
            "hierarchy": 0.35,
            "reputation_importance": 0.40,
            "family_loyalty": 0.75,
            "forgiveness": 0.80,
        },
    },

    "LeafWing": {
        "menu_id": "leafwing",
        "display_name": "LeafWing",
        "description": "Independent, protective, and deeply resilient.",
        "personality_bias": ["Brave", "Suspicious"],
        "culture": {
            "aggression": 0.55,
            "cooperation": 0.60,
            "hierarchy": 0.30,
            "reputation_importance": 0.45,
            "family_loyalty": 0.80,
            "forgiveness": 0.45,
        },
    },

    "Mixed": {
        "menu_id": "mixed",
        "display_name": "Mixed Tribe",
        "description": "A varied tribe with unpredictable dynamics.",
        "personality_bias": [],
        "culture": {
            "aggression": 0.50,
            "cooperation": 0.50,
            "hierarchy": 0.50,
            "reputation_importance": 0.50,
            "family_loyalty": 0.50,
            "forgiveness": 0.50,
        },
    },
}

def get_tribe_data(tribe_name):
    return TRIBE_DATA.get(tribe_name, TRIBE_DATA["Mixed"])


def get_culture_value(tribe_name, value_name, default=0.5):
    tribe_data = get_tribe_data(tribe_name)
    culture = tribe_data.get("culture", {})

    return culture.get(value_name, default)