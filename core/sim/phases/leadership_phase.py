from core.sim.choice_generation.leadership import try_leader_event
from core.sim.leadership import get_leader_by_id
from core.sim.behavior import get_behavior_score

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

        for dragon in world.dragons:
            if dragon.status != "Alive":
                continue

            if dragon.id == leader.id:
                continue

            hierarchy = get_behavior_score(
                dragon,
                "hierarchy"
            )

            if pressure <= 0:
                continue

            if hierarchy >= 0.70:
                dragon.trust[leader.id] = (
                    dragon.trust.get(leader.id, 0)
                    + (pressure * 0.02)
                )

            elif hierarchy <= 0.30:
                dragon.resentment[leader.id] = (
                    dragon.resentment.get(leader.id, 0)
                    + (pressure * 0.02)
                )

    try_leader_event(world)