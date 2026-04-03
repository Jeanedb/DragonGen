import random
from core.sim.logging import log_event


def tick_dragon_progression(world, dragon, living):
    # Aging
    dragon.age_moons += 1

    # Role transition
    if dragon.role == "Dragonet" and dragon.age_moons >= 12:
        dragon.role = random.choice(["Hunter", "Scout", "Warrior", "Healer"])
        log_event(
            world,
            f"{dragon.name} is no longer a dragonet and now serves as a {dragon.role}.",
            involved_ids=[dragon.id],
            event_type="role_change",
            importance=3
        )

    # Healing
    heal_chance = 0.35
    if any(d.role == "Healer" and d.status == "Alive" for d in living):
        heal_chance += 0.10

    if dragon.health == "Injured" and random.random() < heal_chance:
        dragon.health = "Healthy"
        log_event(
            world,
            f"{dragon.name} recovered from their injuries.",
            involved_ids=[dragon.id],
            event_type="recovery"
        )