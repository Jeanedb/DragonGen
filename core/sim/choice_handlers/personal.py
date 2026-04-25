import random
from core.sim.logging import log_event
from core.sim.consequences import schedule_consequence


def handle_personal_choice(world, option_id):
    choice = world.pending_choice

    involved_ids = choice.get("involved_ids", [])
    involved_dragons = [d for d in world.dragons if d.id in involved_ids]

    if len(involved_dragons) < 2:
        world.pending_choice = None
        return

    a = involved_dragons[0]
    b = involved_dragons[1]

    if choice["type"] == "injured_patrol_choice":
        if option_id == "stay_and_help":
            if b.id not in a.friends:
                a.friends.append(b.id)
            if a.id not in b.friends:
                b.friends.append(a.id)

            helper_bonus = 0

            if "The Peacemaker" in b.earned_titles:
                helper_bonus += 1
            if "The Harbinger" in b.earned_titles:
                helper_bonus -= 1
            if "The Watchful" in b.earned_titles:
                helper_bonus -= 1

            a_gain = max(0, 2 + helper_bonus)

            a.trust[b.id] = a.trust.get(b.id, 0) + a_gain
            b.trust[a.id] = b.trust.get(a.id, 0) + 1

            if "The Peacemaker" in b.earned_titles and random.random() < 0.25:
                log_event(
                    world,
                    f"{a.name} seemed especially reassured by {b.name}'s reputation for steadiness.",
                    involved_ids=[a.id, b.id],
                    event_type="title_influence",
                    importance=2
                )

            b.peace_actions += 1
            b.legend_flags["loyal_responses"] = b.legend_flags.get("loyal_responses", 0) + 1
            a.legend_flags["hardship_marks"] = a.legend_flags.get("hardship_marks", 0) + 1

            saved_flag = ("saved_by", b.id, world.moon)
            already_recorded = any(
                len(memory) >= 2 and memory[0] == "saved_by" and memory[1] == b.id
                for memory in a.memory_flags
            )
            if not already_recorded:
                a.memory_flags.append(saved_flag)

            trusted_flag = ("trusted_decision", b.id, world.moon)
            already_trusted = any(
                len(memory) >= 2 and memory[0] == "trusted_decision" and memory[1] == b.id
                for memory in a.memory_flags
            )
            if not already_trusted:
                a.memory_flags.append(trusted_flag)

            log_event(
                world,
                f"{b.name} stayed with {a.name} and tried to help despite the danger.",
                involved_ids=[a.id, b.id],
                event_type="choice_loyalty",
                importance=4
            )

            if random.random() < 0.35:
                b.health = "Injured"
                log_event(
                    world,
                    f"{b.name} was also injured while helping {a.name}.",
                    involved_ids=[a.id, b.id],
                    event_type="injury",
                    importance=3
                )
        elif option_id == "run_for_help":
            b.watchful_actions += 1
            a.legend_flags["hardship_marks"] = a.legend_flags.get("hardship_marks", 0) + 1

            abandoned_flag = ("abandoned_by", b.id, world.moon)
            already_recorded = any(
                len(memory) >= 2 and memory[0] == "abandoned_by" and memory[1] == b.id
                for memory in a.memory_flags
            )
            if not already_recorded:
                a.memory_flags.append(abandoned_flag)

            unreliable_flag = ("seen_as_unreliable", b.id, world.moon)
            already_unreliable = any(
                len(memory) >= 2 and memory[0] == "seen_as_unreliable" and memory[1] == b.id
                for memory in a.memory_flags
            )
            if not already_unreliable:
                a.memory_flags.append(unreliable_flag)

            log_event(
                world,
                f"{b.name} ran back to camp to get help for {a.name}.",
                involved_ids=[a.id, b.id],
                event_type="choice_resolution",
                importance=4
            )

            if random.random() < 0.30:
                if b.id not in a.rivals:
                    a.rivals.append(b.id)
                if a.id not in b.rivals:
                    b.rivals.append(a.id)

                resentment_bonus = 0

                if "The Harbinger" in b.earned_titles:
                    resentment_bonus += 1
                if "The Betrayed" in a.earned_titles:
                    resentment_bonus += 1
                if "The Peacemaker" in b.earned_titles:
                    resentment_bonus -= 1

                a_gain = max(0, 2 + resentment_bonus)

                a.resentment[b.id] = a.resentment.get(b.id, 0) + a_gain
                b.resentment[a.id] = b.resentment.get(a.id, 0) + 1

                log_event(
                    world,
                    f"{a.name} felt abandoned when {b.name} left to seek help.",
                    involved_ids=[a.id, b.id],
                    event_type="choice_abandonment",
                    importance=3
                )

                schedule_consequence(world, delay=4, data={
                    "type": "abandoned_return",
                    "abandoned": a.id,
                    "abandoner": b.id
                })

                schedule_consequence(world, delay=6, data={
                    "type": "possible_defection",
                    "dragon_id": a.id,
                    "caused_by": b.id
                })

    elif choice["type"] == "rival_confrontation_choice":
        if option_id == "back_down":

            a.trust[b.id] = a.trust.get(b.id, 0) + 1
            b.trust[a.id] = b.trust.get(a.id, 0) + 1

            if "The Peacemaker" in a.earned_titles:
                a.trust[b.id] = a.trust.get(b.id, 0) + 1
                b.trust[a.id] = b.trust.get(a.id, 0) + 1

            if "The Harbinger" in a.earned_titles:
                b.trust[a.id] = max(0, b.trust.get(a.id, 0) - 1)

            if "The Peacemaker" in a.earned_titles and random.random() < 0.25:
                log_event(
                    world,
                    f"{a.name}'s reputation as a peacemaker seemed to soften the encounter.",
                    involved_ids=[a.id, b.id],
                    event_type="title_influence",
                    importance=2
                )

            a.peace_actions += 1

            if b.id in a.resentment:
                a.resentment[b.id] = max(0, a.resentment[b.id] - 1)
            if a.id in b.resentment:
                b.resentment[a.id] = max(0, b.resentment[a.id] - 1)

            log_event(
                world,
                f"{a.name} chose restraint and backed down rather than escalating the conflict with {b.name}.",
                involved_ids=[a.id, b.id],
                event_type="choice_restraint",
                importance=4
            )

            ease_chance = 0.35

            if "The Peacemaker" in a.earned_titles:
                ease_chance += 0.20

            if random.random() < ease_chance:
                if b.id in a.rivals:
                    a.rivals.remove(b.id)
                if a.id in b.rivals:
                    b.rivals.remove(a.id)

                log_event(
                    world,
                    f"The tension between {a.name} and {b.name} eased slightly after the encounter.",
                    involved_ids=[a.id, b.id],
                    event_type="relationship_shift",
                    importance=3
                )

        elif option_id == "confront":

            a_bonus = 0
            b_bonus = 0

            if "The Harbinger" in a.earned_titles:
                b_bonus += 1
            if "The Harbinger" in b.earned_titles:
                a_bonus += 1

            if "The Betrayed" in a.earned_titles:
                b_bonus += 1
            if "The Betrayed" in b.earned_titles:
                a_bonus += 1

            if "The Peacemaker" in a.earned_titles:
                b_bonus -= 1
            if "The Peacemaker" in b.earned_titles:
                a_bonus -= 1

            a.resentment[b.id] = a.resentment.get(b.id, 0) + max(0, 2 + a_bonus)
            b.resentment[a.id] = b.resentment.get(a.id, 0) + max(0, 2 + b_bonus)

            injury_chance = 0.45

            if "The Harbinger" in a.earned_titles:
                injury_chance += 0.15

            if "The Watchful" in b.earned_titles:
                injury_chance -= 0.10

            a.combat_wins += 1
            b.combat_losses += 1

            if "The Harbinger" in a.earned_titles and random.random() < 0.25:
                log_event(
                    world,
                    f"{a.name}'s reputation made the confrontation feel more dangerous from the start.",
                    involved_ids=[a.id, b.id],
                    event_type="title_influence",
                    importance=2
                )

            log_event(
                world,
                f"{a.name} confronted {b.name} directly, and the patrol turned hostile.",
                involved_ids=[a.id, b.id],
                event_type="choice_confrontation",
                importance=4
            )

            if random.random() < injury_chance:
                injury_pool = [a, b]
                injury_weights = [1.0, 1.0]

                if "The Harbinger" in a.earned_titles:
                    injury_weights[0] -= 0.2
                    injury_weights[1] += 0.2

                if "The Watchful" in a.earned_titles:
                    injury_weights[0] -= 0.2
                if "The Watchful" in b.earned_titles:
                    injury_weights[1] -= 0.2

                injury_weights = [max(0.2, w) for w in injury_weights]
                injured = random.choices(injury_pool, weights=injury_weights, k=1)[0]

                injured.legend_flags["hardship_marks"] = injured.legend_flags.get("hardship_marks", 0) + 1

                # 20% chance the confrontation is lethal
                if random.random() < 0.2:
                    injured.status = "Dead"
                    injured.health = "Dead"
                    injured.cause_of_death = "conflict"

                    log_event(
                        world,
                        f"{injured.name} was killed during the confrontation between {a.name} and {b.name}.",
                        involved_ids=[a.id, b.id, injured.id],
                        event_type="death",
                        importance=5 
                    )

                else:
                    injured.health = "Injured"
                    injured.legend_flags["pending_survival_check"] = 1

                    log_event(
                        world,
                        f"{injured.name} was injured in the confrontation between {a.name} and {b.name}.",
                        involved_ids=[a.id, b.id],
                        event_type="injury",
                        importance=3
                    )
