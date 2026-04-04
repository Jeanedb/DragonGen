import random
from core.sim.logging import log_event
from core.world import World


def add_injury(world: World, dragon):
    if dragon.health == "Injured" or dragon.status != "Alive":
        return False

    dragon.health = "Injured"

    texts = [
        f"{dragon.name} was injured during a difficult patrol.",
        f"In the {world.tribe_name}, {dragon.name} was badly hurt.",
        f"{dragon.name} returned to camp injured after a dangerous outing.",
        f"{dragon.name} suffered an injury during the moon."
    ]

    text = random.choice(texts)
    
    world.tension += 0.09

    log_event(world, text, involved_ids=[dragon.id], event_type="injury")
    return True