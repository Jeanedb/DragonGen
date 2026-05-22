import random
from core.sim.logging import log_event
from core.world import World
from core.sim.role_behavior import try_healer_intervention



def add_injury(world: World, dragon):
    if dragon.health == "Injured" or dragon.status != "Alive":
        return False

    dragon.health = "Injured"
    dragon.location = "healer_den"
    
    dragon.injury_duration = 0
    dragon.assigned_healer_id = None

    healed = try_healer_intervention(world, dragon)

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