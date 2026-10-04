from dataclasses import dataclass, field
from core.sim.logging import log_event


def has_title(dragon, title):
    return title in getattr(dragon, "earned_titles", [])


def friendship_reputation_bonus(d1, d2):
    trust_bonus_1 = 0
    trust_bonus_2 = 0

    # Peacemakers are easier to trust
    if has_title(d1, "The Peacemaker"):
        trust_bonus_2 += 1
    if has_title(d2, "The Peacemaker"):
        trust_bonus_1 += 1

    # Harbingers make others hesitant
    if has_title(d1, "The Harbinger"):
        trust_bonus_2 -= 1
    if has_title(d2, "The Harbinger"):
        trust_bonus_1 -= 1

    # Watchful dragons are harder to fully trust
    if has_title(d1, "The Watchful"):
        trust_bonus_2 -= 1
    if has_title(d2, "The Watchful"):
        trust_bonus_1 -= 1

    return trust_bonus_1, trust_bonus_2


def rivalry_reputation_bonus(d1, d2):
    resentment_bonus_1 = 0
    resentment_bonus_2 = 0

    # Harbingers create fear and tension
    if has_title(d1, "The Harbinger"):
        resentment_bonus_2 += 1
    if has_title(d2, "The Harbinger"):
        resentment_bonus_1 += 1

    # The Betrayed carry social friction
    if has_title(d1, "The Betrayed"):
        resentment_bonus_2 += 1
    if has_title(d2, "The Betrayed"):
        resentment_bonus_1 += 1

    # Peacemakers soften rivalry formation
    if has_title(d1, "The Peacemaker"):
        resentment_bonus_2 -= 1
    if has_title(d2, "The Peacemaker"):
        resentment_bonus_1 -= 1

    return resentment_bonus_1, resentment_bonus_2


def add_friendship(world, d1, d2):
    if d2.id not in d1.friends:
        d1.friends.append(d2.id)
    if d1.id not in d2.friends:
        d2.friends.append(d1.id)

    if d2.id in d1.rivals:
        d1.rivals.remove(d2.id)
    if d1.id in d2.rivals:
        d2.rivals.remove(d1.id)

    bonus_1, bonus_2 = friendship_reputation_bonus(d1, d2)

    d1_gain = max(0, 1 + bonus_1)
    d2_gain = max(0, 1 + bonus_2)

    d1.trust[d2.id] = d1.trust.get(d2.id, 0) + d1_gain
    d2.trust[d1.id] = d2.trust.get(d1.id, 0) + d2_gain

    world.tension -= 0.08

    if has_title(d1, "The Peacemaker") or has_title(d2, "The Peacemaker"):
        log_event(
            world,
            f"The presence of a known peacemaker made trust come a little easier between {d1.name} and {d2.name}.",
            [d1.id, d2.id],
            event_type="title_influence",
            importance=1,
        )

    elif has_title(d1, "The Harbinger") or has_title(d2, "The Harbinger"):
        log_event(
            world,
            f"Even as {d1.name} and {d2.name} grew closer, reputation made full trust come more slowly.",
            [d1.id, d2.id],
            event_type="title_influence",
            importance=1,
        )

    log_event(
        world,
        f"{d1.name} and {d2.name} have become friends.",
        [d1.id, d2.id],
        event_type="friendship",
        importance=2,
)


def add_rivalry(world, d1, d2):
    if d2.id not in d1.rivals:
        d1.rivals.append(d2.id)
    if d1.id not in d2.rivals:
        d2.rivals.append(d1.id)

    if d2.id in d1.friends:
        d1.friends.remove(d2.id)
    if d1.id in d2.friends:
        d2.friends.remove(d1.id)

    bonus_1, bonus_2 = rivalry_reputation_bonus(d1, d2)

    d1_gain = max(0, 1 + bonus_1)
    d2_gain = max(0, 1 + bonus_2)

    d1.resentment[d2.id] = d1.resentment.get(d2.id, 0) + d1_gain
    d2.resentment[d1.id] = d2.resentment.get(d1.id, 0) + d2_gain

    world.tension += 0.16

    if has_title(d1, "The Harbinger") or has_title(d2, "The Harbinger"):
        log_event(
            world,
            f"Reputation made the tension between {d1.name} and {d2.name} sharpen more quickly.",
            [d1.id, d2.id],
            event_type="title_influence",
            importance=1,
        )

    elif has_title(d1, "The Peacemaker") or has_title(d2, "The Peacemaker"):
        log_event(
            world,
            f"Even in conflict, a peacemaker's reputation seemed to keep the hostility from deepening as fast.",
            [d1.id, d2.id],
            event_type="title_influence",
            importance=1,
        )

    log_event(
        world,
        f"Tension grows between {d1.name} and {d2.name}; they are now rivals.",
        [d1.id, d2.id],
        event_type="rivalry",
        importance=2,
    )



@dataclass
class Relationship:
    type: str
    other_id: int
    strength: float = 1.0
    created_moon: int = 0
    last_changed_moon: int = 0
    history: list = field(default_factory=list)

    def display_name(self):
        names = {
            "bond": "Bond",
            "mentor": "Mentor",
            "student": "Student",
            "rivalry": "Rival",
        }

        return names.get(self.type, self.type.title())

    def description(self):
        descriptions = {
            "bond": "These dragons work well together.",
            "mentor": "Has taken this dragon under their wing.",
            "student": "Looks up to this dragon for guidance.",
            "rivalry": "Competition has become personal.",
        }

        return descriptions.get(self.type, "")


def add_relationship(dragon, relationship):
    if not hasattr(dragon, "relationships") or dragon.relationships is None:
        dragon.relationships = []

    for existing in dragon.relationships:
        if existing.other_id == relationship.other_id and existing.type == relationship.type:
            existing.strength += relationship.strength
            existing.last_changed_moon = relationship.last_changed_moon

            for memory in relationship.history:
                if memory not in existing.history:
                    existing.history.append(memory)

            return existing

    dragon.relationships.append(relationship)
    return relationship

def get_relationship(dragon, other_id, relationship_type=None):
    for relationship in getattr(dragon, "relationships", []):
        if relationship.other_id != other_id:
            continue

        if relationship_type is not None and relationship.type != relationship_type:
            continue

        return relationship

    return None


def strengthen_relationship(dragon, other_id, amount, world=None, relationship_type="bond", memory=None):
    moon = getattr(world, "moon", 0) if world else 0

    relationship = get_relationship(dragon, other_id, relationship_type)

    if not hasattr(dragon, "relationships") or dragon.relationships is None:
        dragon.relationships = []

    if relationship is None:
        relationship = Relationship(
            type=relationship_type,
            other_id=other_id,
            strength=0,
            created_moon=moon,
            last_changed_moon=moon,
        )
        dragon.relationships.append(relationship)

    relationship.strength += amount
    relationship.last_changed_moon = moon

    if memory is not None and memory not in relationship.history:
        relationship.history.append(memory)

    return relationship


def weaken_relationship(dragon, other_id, amount, world=None, relationship_type="bond", memory=None):
    relationship = get_relationship(dragon, other_id, relationship_type)

    if not hasattr(dragon, "relationships") or dragon.relationships is None:
        dragon.relationships = []

    if relationship is None:
        return None

    moon = getattr(world, "moon", 0) if world else 0

    relationship.strength -= amount
    relationship.last_changed_moon = moon

    if memory is not None and memory not in relationship.history:
        relationship.history.append(memory)

    return relationship


def has_relationship(dragon, relationship_type, other_id=None):
    for relationship in getattr(dragon, "relationships", []):
        if relationship.type != relationship_type:
            continue

        if other_id is not None and relationship.other_id != other_id:
            continue

        return True

    return False

def get_relationships(dragon):
    return sorted(
        getattr(dragon, "relationships", []),
        key=lambda relationship: relationship.strength,
        reverse=True
    )