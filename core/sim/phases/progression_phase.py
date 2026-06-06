import random
from core.sim.death import handle_possible_death
from core.sim.progression import tick_dragon_progression
from core.generator import generate_dragonet
from core.sim.logging import log_event


def run_progression_phase(world, living):

    for dragon in living:

        tick_dragon_progression(world, dragon, living)

        handle_possible_death(world, dragon)

        if (
            dragon.status == "Alive"
            and dragon.legend_flags.get("pending_survival_check") == 1
        ):
            dragon.hardship_survived += 1
            dragon.legend_flags["pending_survival_check"] = 0

    # ------------------------
    # Egg Progression
    # ------------------------

    if not hasattr(world, "eggs"):
        world.eggs = []

    hatched_eggs = []

    for egg in world.eggs:
        egg["age"] += 1

        if egg["age"] >= egg["hatch_time"]:
            hatched_eggs.append(egg)

    for egg in hatched_eggs:
        world.eggs.remove(egg)

        existing_ids = [d.id for d in world.dragons]
        new_id = max(existing_ids) + 1 if existing_ids else 1

        parents = [
            d for d in world.dragons
            if d.name in {egg.get("mother"), egg.get("father")}
        ]

        if parents:
            tribe = random.choice(parents).tribe
        else:
            tribe = random.choice(world.dragons).tribe

        dragonet = generate_dragonet(new_id, tribe, parents)
        dragonet.parents = [p.id for p in parents]
        dragonet.location = "hatchery"

        world.dragons.append(dragonet)

        dragonet.age = 0
        dragonet.life_stage = "Dragonet"

        for parent in parents:
            parent.dragonets.append(dragonet.id)

        parent_names = " and ".join([p.name for p in parents]) if parents else "unknown parents"

        log_event(
            world,
            f"The egg of {parent_names} hatched. The dragonet {dragonet.name} was born.",
            involved_ids=[dragonet.id] + [p.id for p in parents],
            event_type="hatchery",
            importance=5,
        )