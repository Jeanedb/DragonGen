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

    if random.random() < 0.25:
        resolve_old_training_memories(world, living)

def resolve_old_training_memories(world, living):
    import random

    if not living:
        return

    dragon = random.choice(living)
    memories = getattr(dragon, "memory_flags", [])

    if not memories:
        return

    memory = random.choice(memories)

    if not isinstance(memory, tuple):
        return

    memory_type = memory[0]

    if memory_type == "mentored_by":
        mentor_id = memory[1]
        mentor = next((d for d in living if d.id == mentor_id), None)

        if mentor:
            dragon.trust[mentor.id] = dragon.trust.get(mentor.id, 0) + 0.2

            world.event_log.append({
                "type": "social",
                "text": f"{dragon.name} sought advice from {mentor.name}, remembering their time as a student."
            })

    elif memory_type == "was_embarrassed_by":
        rival_id = memory[1]
        rival = next((d for d in living if d.id == rival_id), None)

        if rival:
            dragon.resentment[rival.id] = dragon.resentment.get(rival.id, 0) + 0.2

            world.event_log.append({
                "type": "social",
                "text": f"{dragon.name} still remembers being humiliated by {rival.name} during training."
            })

    elif memory_type == "won_team_drill":
        dragon.reputation["reliable"] = dragon.reputation.get("reliable", 0) + 0.1

        world.event_log.append({
            "type": "social",
            "text": f"The tribe still remembers {dragon.name}'s strong performance in past team drills."
        })