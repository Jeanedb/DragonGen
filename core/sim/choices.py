import random
from core.sim.logging import log_event
from core.sim.relationships import add_friendship, add_rivalry


def resolve_choice(world, option_id):
    choice = world.pending_choice
    if not choice:
        return

    if choice["type"] == "leader_decision":
        handle_leader_decision(world, option_id)
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

            if random.random() < 0.35:
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

            log_event(
                world,
                f"{a.name} confronted {b.name} directly, and the patrol turned hostile.",
                involved_ids=[a.id, b.id],
                event_type="choice_confrontation",
                importance=4
            )

            if random.random() < 0.45:
                injured = random.choice([a, b])
                injured.health = "Injured"
                log_event(
                    world,
                    f"{injured.name} was injured in the confrontation between {a.name} and {b.name}.",
                    involved_ids=[a.id, b.id],
                    event_type="injury",
                    importance=3
                )

    world.pending_choice = None

def handle_leader_decision(world, option_id):
    leader = getattr(world, "leader", None)

    if not leader:
        return

    if option_id == "stabilize":
        world.tension = max(0.0, world.tension - 0.3)
        log_event(
            world,
            f"{leader.name} focused on unity, calming the tribe.",
            involved_ids=[leader.id],
            event_type="leader_decision",
            importance=4
        )

    elif option_id == "push_strength":
        world.tension += 0.25
        log_event(
            world,
            f"{leader.name} pushed the tribe harder, raising pressure on everyone.",
            involved_ids=[leader.id],
            event_type="leader_decision",
            importance=4
        )

    elif option_id == "watch_closely":
        world.tension += 0.1
        log_event(
            world,
            f"{leader.name} urged vigilance, making the tribe more watchful.",
            involved_ids=[leader.id],
            event_type="leader_decision",
            importance=4
        )