import random
from core.sim.relationships import add_friendship, add_rivalry
from core.sim.leadership import try_leadership_event
from core.sim.family import try_family_event
from core.sim.injury import add_injury
from core.sim.mates import try_mate_event, try_mate_bond_event
from core.sim.role_behavior import try_leader_influence_event
from core.sim.locations import try_healer_den_event, try_training_grounds_event, try_queen_palace_event
from core.sim.autonomy import try_autonomous_social_behavior
from core.sim.world_state import get_eligible_non_dragonets
from core.sim.selection import (
    choose_friendship_pair,
    choose_rivalry_pair,
    choose_injury_dragon,
)


def run_event_phase(world):
    from core.simulation import (
        get_living_dragons,
        try_existing_relationship_event,
    )

    event_count = random.randint(2, 4)

    for _ in range(event_count):
        living = get_living_dragons(world)
        eligible = get_eligible_non_dragonets(world)

        if len(living) < 1:
            break

        roll = random.random()

        # Tension nudges the event table toward conflict.
        # Low tension nudges it toward relationship-building.
        if world.tension > 2.5:
            roll += 0.08
        elif world.tension < 1.0:
            roll -= 0.05

        roll = max(0.0, min(0.99, roll))

        if random.random() < 0.20:
            if try_leader_influence_event(world):
                continue

        # 🔥 NEW: autonomous behavior layer
        if random.random() < 0.25:
            if try_autonomous_social_behavior(world, living):
                continue

        # Location events are independent checks. Keep these outdented.
        if random.random() < 0.15:
            if try_healer_den_event(world):
                continue

        if random.random() < 0.15:
            if try_training_grounds_event(world):
                continue

        if random.random() < 0.15:
            if try_queen_palace_event(world):
                continue

        success = False
        attempts = 0

        while not success and attempts < 10:
            attempts += 1

            if roll < 0.15:
                success = try_leadership_event(world)
            elif roll < 0.30:
                success = try_family_event(world, living)
            elif roll < 0.55:
                success = try_existing_relationship_event(world, eligible)
            elif roll < 0.72:
                a, b = choose_friendship_pair(eligible)
                if a and b:
                    success = add_friendship(world, a, b)
            elif roll < 0.78:
                success = try_mate_bond_event(world, eligible)
            elif roll < 0.84:
                success = try_mate_event(world, eligible)
            elif roll < 0.94:
                a, b = choose_rivalry_pair(eligible)
                if a and b:
                    success = add_rivalry(world, a, b)
            else:
                dragon = choose_injury_dragon(eligible)
                if dragon:
                    success = add_injury(world, dragon)

            if success:
                break

            if world.tension > 2.5:
                roll += 0.1  # pushes toward rivalry side

            if world.tension < 1.0:
                roll -= 0.05  # pushes toward friendship side

            roll = random.random()