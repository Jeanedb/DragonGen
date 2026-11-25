"""Persistent patrol milestones and the decisions they affect."""

from core.sim.logging import log_event
from core.sim.memory import Memory, add_memory, has_memory

PATROL_MILESTONE = "proven_patrolmate"


def rescue_injury_risk(dragon):
    return 0.20 if has_memory(dragon, PATROL_MILESTONE) else 0.35


def patrol_milestone_text(dragon):
    return f"{dragon.name} became a proven patrolmate after successful patrols on three different moons."


def record_patrol_milestone(world, dragon):
    if has_memory(dragon, PATROL_MILESTONE):
        return
    successful_moons = {
        memory.moon for memory in dragon.memories if memory.type == "border_patrol_success"
    }
    if len(successful_moons) < 3:
        return

    add_memory(dragon, Memory(
        type=PATROL_MILESTONE, moon=world.moon, importance=6, tags=["border", "milestone"],
    ))
    log_event(
        world, patrol_milestone_text(dragon), involved_ids=[dragon.id],
        event_type=PATROL_MILESTONE, importance=6,
    )
