from core.sim.logging import log_event
from core.sim.leadership import get_leader_by_id

def handle_leader_decision(world, option_id):
    leader = get_leader_by_id(world)

    if not leader:
        return

    if option_id == "stabilize":
        calm_amount = 0.3

        if "The Peacemaker" in leader.earned_titles:
            calm_amount += 0.15

        world.tension = max(0.0, world.tension - calm_amount)

        leader.peace_actions += 1

        for dragon in world.dragons:
            if dragon.id != leader.id and dragon.status == "Alive":
                dragon.trust[leader.id] = dragon.trust.get(leader.id, 0) + 1

        log_event(
            world,
            f"{leader.name} focused on unity, calming the tribe.",
            involved_ids=[leader.id],
            event_type="leader_decision",
            importance=4
        )

        world.direction = "stabilizing"
        world.direction_timer = 3

    elif option_id == "push_strength":
        world.tension += 0.25

        if "The Harbinger" in leader.earned_titles:
            for dragon in world.dragons:
                if dragon.id != leader.id and dragon.status == "Alive":
                    dragon.resentment[leader.id] = dragon.resentment.get(leader.id, 0) + 0.5

        log_event(
            world,
            f"{leader.name} pushed the tribe harder, raising pressure on everyone.",
            involved_ids=[leader.id],
            event_type="leader_decision",
            importance=4
        )

        world.direction = "pressuring"
        world.direction_timer = 3

    elif option_id == "watch_closely":
        tension_increase = 0.1

        if "The Watchful" in leader.earned_titles:
            tension_increase += 0.05

        world.tension += tension_increase

        leader.watchful_actions += 1

        for dragon in world.dragons:
            if dragon.id != leader.id and dragon.status == "Alive":
                dragon.trust[leader.id] = max(0, dragon.trust.get(leader.id, 0) - 0.25)
                dragon.resentment[leader.id] = dragon.resentment.get(leader.id, 0) + 0.25

        log_event(
            world,
            f"{leader.name} urged vigilance, making the tribe more watchful.",
            involved_ids=[leader.id],
            event_type="leader_decision",
            importance=4
        )

        world.direction = "watchful"
        world.direction_timer = 3