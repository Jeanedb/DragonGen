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

        caretaker = next(
            (
                d for d in world.dragons
                if d.name == egg.get("caretaker")
                and d.status == "Alive"
            ),
            None
        )

        if parents:
            tribe = random.choice(parents).tribe
        else:
            tribe = random.choice(world.dragons).tribe

        dragonet = generate_dragonet(new_id, tribe, parents)
        dragonet.parents = [p.id for p in parents]
        dragonet.location = "hatchery"

        if caretaker:
            dragonet.trust[caretaker.id] = 2.0
            caretaker.trust[dragonet.id] = 1.0

            dragonet.caretaker_id = caretaker.id
            dragonet.caretaker_role = caretaker.role

            if caretaker.role == "Healer":
                dragonet.health = "Healthy"
                dragonet.reputation["reliable"] += 0.2

            elif caretaker.role == "Elder":
                dragonet.reputation["reliable"] += 0.3

            elif caretaker.role == "Warrior":
                dragonet.combat_skill += 1

            elif caretaker.role == "Scout":
                dragonet.watchful_actions += 1

            elif caretaker.role == "Hunter":
                dragonet.hardship_survived += 1

        world.dragons.append(dragonet)

        dragonet.age = 0
        dragonet.life_stage = "Dragonet"

        for parent in parents:
            parent.dragonets.append(dragonet.id)

        parent_names = " and ".join([p.name for p in parents]) if parents else "unknown parents"

        caretaker_text = (
            f" {caretaker.name}'s care left an early mark on them."
            if caretaker
            else ""
        )

        log_event(
            world,
            f"The egg of {parent_names} hatched. The dragonet {dragonet.name} was born.{caretaker_text}",
            involved_ids=[dragonet.id] + [p.id for p in parents],
            event_type="hatchery",
            importance=5,
        )