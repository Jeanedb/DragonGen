import random
from core.sim.logging import log_event
from core.sim.relationships import add_friendship, add_rivalry
from core.sim.politics import shift_relation
from core.sim.leadership import get_leader_by_id


def resolve_choice(world, option_id):
    choice = world.pending_choice
    if not choice:
        return

    if choice["type"] == "leader_decision":
        handle_leader_decision(world, option_id)
        world.pending_choice = None
        return

    elif choice["type"] == "diplomatic_choice":
        tribe = choice.get("tribe")
        scenario = choice.get("scenario")

        if tribe not in world.tribal_incidents:
            world.tribal_incidents[tribe] = []

        if scenario == "safe_passage":
            if option_id == "allow_passage":
                shift_relation(world, tribe, 4)
                log_event(
                    world,
                    f"The tribe allowed a group of {tribe}s safe passage, slightly improving relations.",
                    event_type="politics",
                    importance=2
                )
                world.tribal_incidents[tribe].append("Safe passage granted")

            elif option_id == "refuse_passage":
                shift_relation(world, tribe, -5)
                log_event(
                    world,
                    f"The tribe turned away a group of {tribe}s at the border, worsening relations.",
                    event_type="politics",
                    importance=2
                )
                world.tribal_incidents[tribe].append("Safe passage refused")

            elif option_id == "escort_passage":
                shift_relation(world, tribe, 6)
                log_event(
                    world,
                    f"The tribe escorted a group of {tribe}s safely through nearby territory, improving relations noticeably.",
                    event_type="politics",
                    importance=3
                )
                world.tribal_incidents[tribe].append("Escorted safely through territory")
   
        elif scenario == "wounded_outsider":
            if option_id == "help_wounded":
                shift_relation(world, tribe, 5)
                log_event(
                    world,
                    f"The tribe helped a wounded {tribe} recover, strengthening relations.",
                    event_type="politics",
                    importance=3
                )
                world.tribal_incidents[tribe].append("Wounded outsider was aided")

            elif option_id == "ignore_wounded":
                shift_relation(world, tribe, -3)
                log_event(
                    world,
                    f"The tribe left a wounded {tribe} without help, quietly damaging relations.",
                    event_type="politics",
                    importance=2
                )
                world.tribal_incidents[tribe].append("Wounded outsider was ignored")

            elif option_id == "detain_wounded":
                shift_relation(world, tribe, -6)
                log_event(
                    world,
                    f"The tribe detained a wounded {tribe} for questioning, sharply worsening relations.",
                    event_type="politics",
                    importance=3
                )
                world.tribal_incidents[tribe].append("Wounded outsider was detained")

        elif scenario == "border_misunderstanding":
            if option_id == "accept_explanation":
                shift_relation(world, tribe, 3)
                log_event(
                    world,
                    f"The tribe accepted the {tribe}s' explanation and allowed them to withdraw peacefully.",
                    event_type="politics",
                    importance=2
                )
                world.tribal_incidents[tribe].append("Border misunderstanding was defused")

            elif option_id == "issue_warning":
                shift_relation(world, tribe, -2)
                log_event(
                    world,
                    f"The tribe issued a harsh warning to a {tribe} patrol and sent them away.",
                    event_type="politics",
                    importance=2
                )
                world.tribal_incidents[tribe].append("Border warning issued")

            elif option_id == "escalate_border":
                shift_relation(world, tribe, -6)
                log_event(
                    world,
                    f"A border misunderstanding with the {tribe}s escalated into a serious diplomatic incident.",
                    event_type="politics",
                    importance=3
                )
                world.tribal_incidents[tribe].append("Border incident escalated")

        world.tribal_incidents[tribe] = world.tribal_incidents[tribe][-5:]
        world.pending_choice = None
        return

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

            a.trust[b.id] = a.trust.get(b.id, 0) + 2
            b.trust[a.id] = b.trust.get(a.id, 0) + 1

            b.peace_actions += 1
            b.legend_flags["loyal_responses"] = b.legend_flags.get("loyal_responses", 0) + 1
            a.legend_flags["hardship_marks"] = a.legend_flags.get("hardship_marks", 0) + 1

            flag = ("saved_by", b.id)
            if flag not in a.memory_flags:
                a.memory_flags.append(flag)

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

                a.resentment[b.id] = a.resentment.get(b.id, 0) + 2
                b.resentment[a.id] = b.resentment.get(a.id, 0) + 1

                flag = ("abandoned_by", b.id)
                if flag not in a.memory_flags:
                    a.memory_flags.append(flag)

                log_event(
                    world,
                    f"{a.name} felt abandoned when {b.name} left to seek help.",
                    involved_ids=[a.id, b.id],
                    event_type="choice_abandonment",
                    importance=3
                )

    elif choice["type"] == "rival_confrontation_choice":
        if option_id == "back_down":

            a.trust[b.id] = a.trust.get(b.id, 0) + 1
            b.trust[a.id] = b.trust.get(a.id, 0) + 1

            if "The Peacemaker" in a.earned_titles:
                a.trust[b.id] = a.trust.get(b.id, 0) + 1
                b.trust[a.id] = b.trust.get(a.id, 0) + 1

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

            a.resentment[b.id] = a.resentment.get(b.id, 0) + 2
            b.resentment[a.id] = b.resentment.get(a.id, 0) + 2

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
                    injury_weights = [0.8, 1.2]

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


    world.pending_choice = None

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

        log_event(
            world,
            f"{leader.name} urged vigilance, making the tribe more watchful.",
            involved_ids=[leader.id],
            event_type="leader_decision",
            importance=4
        )

        world.direction = "watchful"
        world.direction_timer = 3

    