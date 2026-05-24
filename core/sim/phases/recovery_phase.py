from core.sim.phases.recovery_events import (
    try_recovery_visit_event,
    try_recovery_neglect_event,
    try_injury_strain_event,
)


def run_recovery_phase(world):

    for dragon in world.dragons:
        if dragon.status == "Alive" and dragon.health == "Injured":

            visited = try_recovery_visit_event(world, dragon)

            if not visited and getattr(dragon, "injury_duration", 0) >= 2:
                try_recovery_neglect_event(world, dragon)

    try_injury_strain_event(world)