
import random

from core.world import World
from core.sim.logging import log_event

def handle_possible_death(world: World, dragon):
    if dragon.status != "Alive":
        return False

    death_chance = 0.0

    if dragon.age_moons >= 180:
        death_chance += 0.02
    if dragon.age_moons >= 220:
        death_chance += 0.05
    if dragon.age_moons >= 260:
        death_chance += 0.10

    if dragon.role == "Elder":
        death_chance += 0.03

    was_injured = (dragon.health == "Injured")
    if was_injured:
        death_chance += 0.05

    if random.random() < death_chance:
        dragon.status = "Dead"
        dragon.health = "Dead"

        if was_injured:
            dragon.cause_of_death = "injury"
        elif dragon.age_moons >= 180 or dragon.role == "Elder":
            dragon.cause_of_death = "natural"
        else:
            dragon.cause_of_death = "natural"

        surviving_mate = None

        if dragon.mate_id is not None:
            surviving_mate = next(
                (d for d in world.dragons if d.id == dragon.mate_id and d.status == "Alive"),
                None
            )

            if surviving_mate:
                flag = ("lost_mate", dragon.id, world.moon)

                already_recorded = any(
                    len(memory) >= 2 and memory[0] == "lost_mate" and memory[1] == dragon.id
                    for memory in surviving_mate.memory_flags
                )

                if not already_recorded:
                    surviving_mate.memory_flags.append(flag)

                surviving_mate.grief_level = 12
                surviving_mate.mate_id = None

                if hasattr(world, "tension"):
                    world.tension += 0.18

        if surviving_mate:
            texts = [
                f"{dragon.name} passed away under the stars, leaving {surviving_mate.name} behind in grief.",
                f"The tribe mourns the loss of {dragon.name}, and {surviving_mate.name} seems deeply shaken.",
                f"In the {world.tribe_name}, {dragon.name} died, leaving their mate {surviving_mate.name} to carry the loss.",
            ]
        else:
            texts = [
                f"{dragon.name} passed away under the stars.",
                f"The tribe mourns the loss of {dragon.name}.",
                f"In the {world.tribe_name}, {dragon.name} ascended to the sky after death.",
                f"{dragon.name} has died, leaving behind memories in the tribe."
            ]

        text = random.choice(texts)
        log_event(world, text, involved_ids=[dragon.id], event_type="death", importance=5)

        dragon.mate_id = None
        return True

    return False
