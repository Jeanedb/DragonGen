import random
from core.sim.logging import log_event
from core.sim.memory import Memory, add_memory
from core.world import World
from core.sim.role_behavior import try_healer_intervention



def add_injury(world: World, dragon, *, text=None):
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

    if text is None:
        text = random.choice(texts)
    
    world.tension += 0.09

    log_event(world, text, involved_ids=[dragon.id], event_type="injury")
    return True


def escort_injured_sib(world: World, injured, patrol):
    """Return the MudWing patrolmate who escorts a wounded sib to care."""
    if injured.tribe != "MudWing" or not injured.sib_group_id:
        return None

    escort = max(
        (
            dragon for dragon in patrol
            if dragon.id != injured.id
            and dragon.tribe == "MudWing"
            and dragon.sib_group_id == injured.sib_group_id
            and dragon.status == "Alive"
            and dragon.health == "Healthy"
            and dragon.role != "Dragonet"
        ),
        key=lambda dragon: (dragon.is_bigwings, injured.trust.get(dragon.id, 0)),
        default=None,
    )
    if escort is None:
        return None

    escort.location = "healer_den"
    injured.trust[escort.id] = injured.trust.get(escort.id, 0) + 1.0
    for dragon, other, memory_type in (
        (injured, escort, "escorted_by_sib"),
        (escort, injured, "escorted_injured_sib"),
    ):
        add_memory(
            dragon,
            Memory(
                type=memory_type,
                moon=world.moon,
                other_id=other.id,
                importance=4,
                tags=["mudwing", "sib", "border"],
            ),
        )
    return escort
