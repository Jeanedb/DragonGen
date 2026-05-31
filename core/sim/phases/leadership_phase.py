from core.sim.choice_generation.leadership import try_leader_event
from core.sim.leadership import get_leader_by_id


def run_leadership_phase(world):

    leader = get_leader_by_id(world)

    if leader and leader.status == "Alive":
        pressure = 0

        pressure += int(getattr(world, "tension", 0))

        injured = sum(
            1 for d in world.dragons
            if d.health == "Injured"
        )
        pressure += injured * 0.5

        recent_deaths = [
            e for e in world.event_log[-5:]
            if isinstance(e, dict) and e.get("type") == "death"
        ]
        pressure += len(recent_deaths) * 1.5

        leader.leadership_pressure += int(pressure)

    try_leader_event(world)