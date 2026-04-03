import random
from core.sim.relationships import add_friendship, add_rivalry
from core.sim.leadership import try_leadership_event


def run_event_phase(world):
    from core.simulation import (
        get_living_dragons,
        try_family_event,
        try_existing_relationship_event,
        choose_friendship_pair,
        choose_rivalry_pair,
        choose_injury_dragon,
        add_injury,
    )

    event_count = random.randint(2, 4)

    for _ in range(event_count):
        living = get_living_dragons(world)
        if len(living) < 2:
            break

        roll = random.random()
        success = False
        attempts = 0

        while not success and attempts < 10:
            attempts += 1

            if roll < 0.15:
                success = try_leadership_event(world)
            elif roll < 0.30:
                success = try_family_event(world, living)
            elif roll < 0.55:
                success = try_existing_relationship_event(world, living)
            elif roll < 0.65:
                a, b = choose_friendship_pair(living)
                if a and b:
                    success = add_friendship(world, a, b)
            elif roll < 0.90:
                a, b = choose_rivalry_pair(living)
                if a and b:
                    success = add_rivalry(world, a, b)
            else:
                dragon = choose_injury_dragon(living)
                if dragon:
                    success = add_injury(world, dragon)

            if success:
                break

            roll = random.random()