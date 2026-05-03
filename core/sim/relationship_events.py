import random
from core.sim.role_behavior import try_healer_intervention
from core.sim.logging import log_event
from core.sim.locations import get_event_location_text



def try_relationship_event(world, a, b, state):
    if random.random() > 0.15:
        return False  # keep rare

    loc = get_event_location_text(a, b)


    if state == "bonding":
        a.trust[b.id] = a.trust.get(b.id, 0) + 2
        b.trust[a.id] = b.trust.get(a.id, 0) + 2

        a.memory_flags.append(("bonded_with", b.id, world.moon))
        b.memory_flags.append(("bonded_with", a.id, world.moon))

        log_event(
            world,
            f"{a.name} and {b.name} stood by each other when it mattered, strengthening their bond{loc}.",
            involved_ids=[a.id, b.id],
            event_type="loyalty_moment",
            importance=4,
        )
        return True

    elif state == "hostile":
        a.resentment[b.id] = a.resentment.get(b.id, 0) + 2
        b.resentment[a.id] = b.resentment.get(a.id, 0) + 2

        if a.location == "queen_palace" or b.location == "queen_palace":
            world.tension = max(0, world.tension - 0.1)

        world.tension += 0.1

        a.memory_flags.append(("major_conflict", b.id, world.moon))

        for d in world.dragons:
            if d.id not in {a.id, b.id} and d.status == "Alive":
                if random.random() < 0.4:
                    d.perceived_reputation[a.id] = d.perceived_reputation.get(a.id, 0) - 0.3
                    d.perceived_reputation[b.id] = d.perceived_reputation.get(b.id, 0) + 0.2

        b.memory_flags.append(("major_conflict", a.id, world.moon))

        log_event(
            world,
            f"The conflict between {a.name} and {b.name} escalated sharply{loc}.",
            involved_ids=[a.id, b.id],
            event_type="major_conflict",
            importance=4,
        )

        # small chance of injury
        injury_chance = 0.25

        if a.location == "training_grounds" or b.location == "training_grounds":
            injury_chance += 0.1

        if (
            (a.location == "training_grounds" or b.location == "training_grounds")
            and (a.role == "Warrior" or b.role == "Warrior")
        ):
            injury_chance += 0.1

        # warrior influence
        for d in world.dragons:
            if d.role == "Warrior" and d.status == "Alive":
                if d.perceived_reputation.get(a.id, 0) > 1:
                    injury_chance += 0.05
                if d.perceived_reputation.get(b.id, 0) > 1:
                    injury_chance += 0.05

        injury_chance = min(0.6, injury_chance)

        if random.random() < injury_chance:
            injured = random.choice([a, b])
            injured.health = "Injured"

            if injured.location == "healer_den":
                if random.random() < 0.5:
                    injured.health = "Healthy"

            if injured.health == "Injured":
                try_healer_intervention(world, injured)

                log_event(
                    world,
                    f"{injured.name} was injured during the conflict{loc}.",
                    involved_ids=[a.id, b.id],
                    event_type="injury",
                    importance=3,
                )
            else:
                log_event(
                    world,
                    f"{injured.name} was hurt during the conflict{loc}, but recovered quickly at the Healer's Den.",
                    involved_ids=[a.id, b.id],
                    event_type="healer_den_recovery",
                    importance=3,
                )

        return True

    elif state == "deteriorating":
        if b.id in a.friends:
            a.friends.remove(b.id)
        if a.id in b.friends:
            b.friends.remove(a.id)

        if b.id not in a.rivals:
            a.rivals.append(b.id)
        if a.id not in b.rivals:
            b.rivals.append(a.id)

        a.memory_flags.append(("relationship_broken", b.id, world.moon))
        b.memory_flags.append(("relationship_broken", a.id, world.moon))

        log_event(
            world,
            f"The relationship between {a.name} and {b.name} broke down completely{loc}.",
            involved_ids=[a.id, b.id],
            event_type="relationship_break",
            importance=4,
        )
        return True

    return False