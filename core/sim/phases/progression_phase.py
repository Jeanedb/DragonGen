from core.sim.death import handle_possible_death
from core.sim.progression import tick_dragon_progression


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