import random
from core.sim.logging import log_event
from core.sim.relationships import add_friendship, add_rivalry
from core.sim.politics import shift_relation
from core.sim.leadership import get_leader_by_id

def get_region_intensity(world, region):
    if not region:
        return 0.0

    activity = world.region_activity.get(region, 0)

    if activity >= 6:
        return 0.25
    elif activity >= 3:
        return 0.15
    elif activity >= 1:
        return 0.05
    else:
        return 0.0


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
        region = choice.get("region")
        intensity = get_region_intensity(world, region)

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
                penalty = max(1, int(round(5 * (1 + intensity))))
                shift_relation(world, tribe, -penalty)
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
                penalty = max(1, int(round(6 * (1 + intensity))))
                shift_relation(world, tribe, -penalty)
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
                penalty = max(1, int(round(2 * (1 + intensity))))
                shift_relation(world, tribe, -penalty)
                log_event(
                    world,
                    f"The tribe issued a harsh warning to a {tribe} patrol and sent them away.",
                    event_type="politics",
                    importance=2
                )
                world.tribal_incidents[tribe].append("Border warning issued")

            elif option_id == "escalate_border":
                penalty = max(1, int(round(6 * (1 + intensity))))
                shift_relation(world, tribe, -penalty)
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

    elif choice["type"] == "tribal_policy_choice":
        tribe = choice.get("tribe")

        if not tribe:
            world.pending_choice = None
            return

        if tribe not in world.tribal_incidents:
            world.tribal_incidents[tribe] = []

        other_tribes = [t for t in world.tribal_relations.keys() if t != tribe]
        secondary_tribe = random.choice(other_tribes) if other_tribes else None
        trait = world.tribal_traits.get(tribe, "neutral")

        if option_id == "peace_gesture":
            score = world.tribal_relations.get(tribe, 0)

            if score <= -30:
                reject_chance = 0.7
                tension_chance = 0.25

                if trait == "aggressive":
                    reject_chance += 0.15
                    tension_chance += 0.10
                elif trait == "cautious":
                    reject_chance -= 0.15
                    tension_chance -= 0.10
                elif trait == "opportunistic":
                    reject_chance -= 0.05

                if random.random() < reject_chance:
                    if random.random() < 0.5:
                        shift_relation(world, tribe, -1)

                    if random.random() < max(0.0, tension_chance):
                        world.tension += 0.05

                    if trait == "aggressive":
                        text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s dismissed the peace gesture as weakness and refused it outright."
                    elif trait == "cautious":
                        text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s refused the peace gesture, citing distrust and uncertainty."
                    elif trait == "opportunistic":
                        text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s showed no interest in the peace gesture and turned it away."
                    else:
                        text = f"The {tribe}s rejected the tribe's peace gesture, seeing it as suspicious or insincere."

                    log_event(
                        world,
                        text,
                        event_type="politics",
                        importance=3
                    )
                    world.tribal_incidents[tribe].append("Peace gesture was rejected")
                else:
                    gain = 1
                    if trait == "cautious":
                        gain = 2

                    shift_relation(world, tribe, gain)
                    if trait == "aggressive":
                        text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s accepted the gesture only grudgingly, without softening her stance."
                    elif trait == "cautious":
                        text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s accepted the peace gesture carefully, though suspicion remained."
                    elif trait == "opportunistic":
                        text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s accepted the peace gesture for now, seeing possible value in it."
                    else:
                        text = f"The {tribe}s accepted the peace gesture only cautiously, with visible suspicion."

                    log_event(
                        world,
                        text,
                        event_type="politics",
                        importance=3
                    )
                    world.tribal_incidents[tribe].append("Peace gesture was cautiously accepted")

            elif score <= -10:
                gain = 2
                if trait == "aggressive":
                    gain = 1
                elif trait == "cautious":
                    gain = 3

                shift_relation(world, tribe, gain)
                if trait == "aggressive":
                    text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s accepted the peace gesture without warmth. Relations improved only slightly."
                elif trait == "cautious":
                    text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s accepted the peace gesture with measured restraint, allowing a small improvement."
                elif trait == "opportunistic":
                    text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s accepted the peace gesture, seeing some advantage in keeping matters calm."
                else:
                    text = f"The {tribe}s accepted the peace gesture cautiously. Relations improved only slightly."

                log_event(
                    world,
                    text,
                    event_type="politics",
                    importance=3
                )
                world.tribal_incidents[tribe].append("Peace gesture cautiously accepted")

            else:
                gain = 4
                if trait == "aggressive":
                    gain = 3
                elif trait == "cautious":
                    gain = 5

                shift_relation(world, tribe, gain)
                if trait == "aggressive":
                    text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s accepted the peace gesture, though her response remained firm and unsentimental."
                elif trait == "cautious":
                    text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s accepted the peace gesture in a calm and measured way, improving relations."
                elif trait == "opportunistic":
                    text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s accepted the peace gesture, evidently seeing value in better relations."
                else:
                    text = f"The tribe sent a peace gesture to the {tribe}s, improving relations."

                log_event(
                    world,
                    text,
                    event_type="politics",
                    importance=3
                )
                world.tribal_incidents[tribe].append("Peace gesture sent")

            if secondary_tribe:
                shift_relation(world, secondary_tribe, -2)
                if secondary_tribe not in world.tribal_incidents:
                    world.tribal_incidents[secondary_tribe] = []
                world.tribal_incidents[secondary_tribe].append(
                    f"Became suspicious after peace gesture toward {tribe}"
                )
                log_event(
                    world,
                    f"The {secondary_tribe}s viewed the peace gesture toward the {tribe}s with suspicion.",
                    event_type="politics",
                    importance=2
                )

        elif option_id == "border_patrol":
            shift_relation(world, tribe, -2)
            log_event(
                world,
                f"The tribe increased patrols near {tribe} territory, making relations more tense.",
                event_type="politics",
                importance=3
            )
            world.tribal_incidents[tribe].append("Border patrols increased")

            leader = get_leader_by_id(world)
            if leader:
                leader.watchful_actions += 1

        elif option_id == "border_pressure":
            shift_relation(world, tribe, -5)
            world.tension += 0.2

            log_event(
                world,
                f"The tribe applied pressure along the {tribe} border, sharply worsening relations.",
                event_type="politics",
                importance=4
            )
            world.tribal_incidents[tribe].append("Border pressure applied")

            if secondary_tribe:
                shift_relation(world, secondary_tribe, 2)
                if secondary_tribe not in world.tribal_incidents:
                    world.tribal_incidents[secondary_tribe] = []
                world.tribal_incidents[secondary_tribe].append(
                    f"Approved of pressure against {tribe}"
                )
                log_event(
                    world,
                    f"The {secondary_tribe}s seemed to approve of the tribe's harder stance toward the {tribe}s.",
                    event_type="politics",
                    importance=2
                )

        elif option_id == "offer_aid":
            score = world.tribal_relations.get(tribe, 0)

            if score <= -30:
                reject_chance = 0.6

                if trait == "aggressive":
                    reject_chance += 0.15
                elif trait == "cautious":
                    reject_chance -= 0.10
                elif trait == "opportunistic":
                    reject_chance -= 0.15

                if random.random() < reject_chance:
                    if random.random() < 0.5:
                        shift_relation(world, tribe, -1)

                    if trait == "aggressive" and random.random() < 0.25:
                        world.tension += 0.05

                    if trait == "aggressive":
                        text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s treated the offered aid as an insult and refused it."
                    elif trait == "cautious":
                        text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s refused the aid, unwilling to trust the motive behind it."
                    elif trait == "opportunistic":
                        text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s declined the aid, apparently seeing little advantage in accepting it."
                    else:
                        text = f"The {tribe}s refused the offered aid, treating it as a provocation or hidden maneuver."

                    log_event(
                        world,
                        text,
                        event_type="politics",
                        importance=3
                    )
                    world.tribal_incidents[tribe].append("Aid was refused")
                else:
                    gain = 1
                    if trait == "opportunistic":
                        gain = 2

                    shift_relation(world, tribe, gain)
                    if trait == "aggressive":
                        text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s accepted the aid grudgingly, without any sign of trust."
                    elif trait == "cautious":
                        text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s accepted the aid carefully, though suspicion remained."
                    elif trait == "opportunistic":
                        text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s accepted the aid, clearly willing to take what benefit she could."
                    else:
                        text = f"The {tribe}s accepted the aid reluctantly, without trust."

                    log_event(
                        world,
                        text,
                        event_type="politics",
                        importance=3
                    )
                    world.tribal_incidents[tribe].append("Aid was reluctantly accepted")

            elif score <= -10:
                gain = 2
                if trait == "aggressive":
                    gain = 1
                elif trait == "cautious":
                    gain = 3
                elif trait == "opportunistic":
                    gain = 4

                shift_relation(world, tribe, gain)
                if trait == "aggressive":
                    text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s accepted the aid stiffly, allowing only a slight improvement."
                elif trait == "cautious":
                    text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s accepted the aid with measured caution, modestly improving relations."
                elif trait == "opportunistic":
                    text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s accepted the aid, seeing enough value in it to improve relations slightly."
                else:
                    text = f"The {tribe}s accepted the aid with caution. Relations improved, but only slightly."

                log_event(
                    world,
                    text,
                    event_type="politics",
                    importance=3
                )
                world.tribal_incidents[tribe].append("Aid cautiously accepted")

            else:
                gain = 5
                if trait == "aggressive":
                    gain = 4
                elif trait == "opportunistic":
                    gain = 6

                shift_relation(world, tribe, gain)
                if trait == "aggressive":
                    text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s accepted the practical aid, though her tone remained hard."
                elif trait == "cautious":
                    text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s accepted the practical aid in a careful but constructive spirit."
                elif trait == "opportunistic":
                    text = f"Queen {world.tribal_leaders.get(tribe, tribe).replace('Queen ', '')} of the {tribe}s accepted the practical aid readily, seeing clear value in it."
                else:
                    text = f"The tribe offered practical aid to the {tribe}s, improving relations noticeably."

                log_event(
                    world,
                    text,
                    event_type="politics",
                    importance=3
                )
                world.tribal_incidents[tribe].append("Practical aid offered")

            if secondary_tribe:
                shift_relation(world, secondary_tribe, -1)
                if secondary_tribe not in world.tribal_incidents:
                    world.tribal_incidents[secondary_tribe] = []
                world.tribal_incidents[secondary_tribe].append(
                    f"Disliked aid being offered to {tribe}"
                )
                log_event(
                    world,
                    f"The {secondary_tribe}s did not seem pleased by aid being offered to the {tribe}s.",
                    event_type="politics",
                    importance=2
                )

        world.tribal_incidents[tribe] = world.tribal_incidents[tribe][-5:]
        if secondary_tribe and secondary_tribe in world.tribal_incidents:
            world.tribal_incidents[secondary_tribe] = world.tribal_incidents[secondary_tribe][-5:]

        world.pending_choice = None
        return


    elif choice["type"] == "incoming_diplomacy_choice":
        tribe = choice.get("tribe")
        scenario = choice.get("scenario")
        region = choice.get("region")
        intensity = get_region_intensity(world, region)

        if not tribe:
            world.pending_choice = None
            return

        if tribe not in world.tribal_incidents:
            world.tribal_incidents[tribe] = []

        if scenario == "aid_request":
            if option_id == "grant_aid":
                shift_relation(world, tribe, 5)
                log_event(
                    world,
                    f"The tribe sent aid to the {tribe}s after their request, improving relations.",
                    event_type="politics",
                    importance=3
                )
                world.tribal_incidents[tribe].append("Aid request was granted")

            elif option_id == "refuse_aid":
                penalty = max(1, int(round(4 * (1 + intensity))))
                shift_relation(world, tribe, -penalty)
                log_event(
                    world,
                    f"The tribe refused the {tribe}s' request for aid, worsening relations.",
                    event_type="politics",
                    importance=3
                )
                world.tribal_incidents[tribe].append("Aid request was refused")

            elif option_id == "limited_aid":
                shift_relation(world, tribe, 2)
                log_event(
                    world,
                    f"The tribe sent only limited aid to the {tribe}s, improving relations slightly.",
                    event_type="politics",
                    importance=2
                )
                world.tribal_incidents[tribe].append("Limited aid was sent")

        elif scenario == "warning":
            if option_id == "deescalate_warning":
                shift_relation(world, tribe, 2)
                log_event(
                    world,
                    f"The tribe answered the {tribe}s' warning with restraint, easing tensions slightly.",
                    event_type="politics",
                    importance=2
                )
                world.tribal_incidents[tribe].append("Warning was de-escalated")

            elif option_id == "ignore_warning":
                penalty = max(1, int(round(2 * (1 + intensity))))
                shift_relation(world, tribe, -penalty)
                log_event(
                    world,
                    f"The tribe ignored the {tribe}s' warning, increasing distrust.",
                    event_type="politics",
                    importance=2
                )
                world.tribal_incidents[tribe].append("Warning was ignored")

            elif option_id == "answer_firmly":
                penalty = max(1, int(round(4 * (1 + intensity))))
                shift_relation(world, tribe, -penalty)
                world.tension += 0.1 * (1 + intensity)
                log_event(
                    world,
                    f"The tribe answered the {tribe}s' warning with a firm response of its own, worsening tensions.",
                    event_type="politics",
                    importance=3
                )
                world.tribal_incidents[tribe].append("Warning was answered firmly")

        elif scenario == "truce_offer":
            if option_id == "accept_truce":
                shift_relation(world, tribe, 4)
                log_event(
                    world,
                    f"The tribe accepted a temporary truce with the {tribe}s, improving relations.",
                    event_type="politics",
                    importance=3
                )
                world.tribal_incidents[tribe].append("Truce was accepted")

            elif option_id == "reject_truce":
                penalty = max(1, int(round(3 * (1 + intensity))))
                shift_relation(world, tribe, -penalty)
                log_event(
                    world,
                    f"The tribe rejected the {tribe}s' offer of truce, worsening relations.",
                    event_type="politics",
                    importance=3
                )
                world.tribal_incidents[tribe].append("Truce was rejected")

            elif option_id == "conditional_truce":
                shift_relation(world, tribe, 2)
                log_event(
                    world,
                    f"The tribe accepted a temporary truce with conditions, improving relations slightly.",
                    event_type="politics",
                    importance=2
                )
                world.tribal_incidents[tribe].append("Conditional truce accepted")




        world.tribal_incidents[tribe] = world.tribal_incidents[tribe][-5:]
        world.pending_choice = None
        return

    elif choice["type"] == "border_sighting":
        tribe = choice.get("tribe")

        if not tribe:
            world.pending_choice = None
            return

        if tribe not in world.tribal_incidents:
            world.tribal_incidents[tribe] = []

        if option_id == "observe":
            shift_relation(world, tribe, 1)
            log_event(
                world,
                f"The tribe kept watch on the {tribe}s from a distance without escalating the encounter.",
                event_type="politics",
                importance=2
            )
            world.tribal_incidents[tribe].append("Border patrol was observed")

        elif option_id == "approach":
            shift_relation(world, tribe, -1)
            log_event(
                world,
                f"The tribe approached the {tribe} patrol and questioned their presence.",
                event_type="politics",
                importance=2
            )
            world.tribal_incidents[tribe].append("Border patrol was questioned")

        elif option_id == "drive_off":
            shift_relation(world, tribe, -3)
            world.tension += 0.2
            log_event(
                world,
                f"The tribe drove off the {tribe} patrol forcefully, worsening tensions.",
                event_type="politics",
                importance=3
            )
            world.tribal_incidents[tribe].append("Border patrol was driven off")

        world.tribal_incidents[tribe] = world.tribal_incidents[tribe][-5:]
        world.pending_choice = None
        return


    elif choice["type"] == "border_violation":
        tribe = choice.get("tribe")

        if not tribe:
            world.pending_choice = None
            return

        if tribe not in world.tribal_incidents:
            world.tribal_incidents[tribe] = []

        if option_id == "ignore_tracks":
            log_event(
                world,
                f"The tribe chose not to respond immediately to signs of {tribe} movement near the border.",
                event_type="politics",
                importance=2
            )
            world.tribal_incidents[tribe].append("Border tracks were ignored")

        elif option_id == "investigate_tracks":
            shift_relation(world, tribe, -1)
            log_event(
                world,
                f"The tribe investigated suspicious tracks near the border, deepening mistrust slightly.",
                event_type="politics",
                importance=2
            )
            world.tribal_incidents[tribe].append("Border tracks were investigated")

        elif option_id == "respond_forcefully":
            shift_relation(world, tribe, -4)
            world.tension += 0.3
            log_event(
                world,
                f"The tribe prepared a forceful response to the suspected {tribe} incursion.",
                event_type="politics",
                importance=3
            )
            world.tribal_incidents[tribe].append("Border violation drew a forceful response")

        world.tribal_incidents[tribe] = world.tribal_incidents[tribe][-5:]
        world.pending_choice = None
        return


    elif choice["type"] == "aid_delivery":
        tribe = choice.get("tribe")

        if not tribe:
            world.pending_choice = None
            return

        if tribe not in world.tribal_incidents:
            world.tribal_incidents[tribe] = []

        if option_id == "allow_aid":
            shift_relation(world, tribe, 3)
            log_event(
                world,
                f"The tribe allowed the {tribe}s to pass with their supplies, improving relations.",
                event_type="politics",
                importance=3
            )
            world.tribal_incidents[tribe].append("Aid delivery was allowed")

        elif option_id == "inspect_aid":
            shift_relation(world, tribe, 1)
            log_event(
                world,
                f"The tribe inspected the {tribe}s' supplies before allowing passage.",
                event_type="politics",
                importance=2
            )
            world.tribal_incidents[tribe].append("Aid delivery was inspected")

        elif option_id == "deny_aid":
            shift_relation(world, tribe, -4)
            world.tension += 0.2
            log_event(
                world,
                f"The tribe denied passage to the {tribe}s' aid convoy, worsening tensions.",
                event_type="politics",
                importance=3
            )
            world.tribal_incidents[tribe].append("Aid delivery was denied")

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

            involved_ids = choice.get("involved_ids", [])
            if len(involved_ids) < 2:
                world.pending_choice = None
                return

            a = next((d for d in world.dragons if d.id == involved_ids[0]), None)
            b = next((d for d in world.dragons if d.id == involved_ids[1]), None)

            if not a or not b:
                world.pending_choice = None
                return

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

    