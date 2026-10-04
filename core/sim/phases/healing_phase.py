import random

from core.sim.logging import log_event


def run_healing_phase(world):
    for dragon in world.dragons:
        if dragon.status != "Alive":
            continue

        if dragon.health != "Injured":
            continue

        dragon.injury_duration = getattr(dragon, "injury_duration", 0) + 1

        # If no healer is assigned, injury cannot resolve before 3 moons.
        if dragon.assigned_healer_id is None:
            if dragon.injury_duration < 3:
                continue

            natural_recovery_chance = 0.20

            if random.random() < natural_recovery_chance:
                dragon.health = "Healthy"
                dragon.assigned_healer_id = None
                dragon.injury_duration = 0
                dragon.location = "village_center"

                log_event(
                    world,
                    f"{dragon.name}'s injuries finally healed on their own.",
                    involved_ids=[dragon.id],
                    event_type="natural_healing",
                    importance=2,
                )
                continue

            world.tension += 0.05
            continue

        healer = next(
            (
                d for d in world.dragons
                if d.id == dragon.assigned_healer_id and d.status == "Alive"
            ),
            None,
        )

        if not healer:
            dragon.assigned_healer_id = None
            continue

        # Ongoing care builds trust and healer reputation.
        dragon.trust[healer.id] = dragon.trust.get(healer.id, 0) + 0.1
        healer.reputation["kind"] = healer.reputation.get("kind", 0) + 0.05

        base_chance = 0.25
        skill_modifier = getattr(healer, "healer_skill", 1.0)
        chance = base_chance * skill_modifier

        if healer.trust.get(dragon.id, 0) >= 2:
            chance += 0.15

        chance = max(0.05, min(0.85, chance))

        if random.random() < chance:
            dragon.health = "Healthy"
            dragon.assigned_healer_id = None
            dragon.injury_duration = 0
            dragon.location = "village_center"

            old_skill = getattr(healer, "healer_skill", 1.0)
            healer.healer_skill = min(2.0, round(old_skill + 0.01, 2))

            healed_by_flag = ("healed_by", healer.id)
            healer_success_flag = ("healed", dragon.id)

            if healed_by_flag not in dragon.memory_flags:
                dragon.memory_flags.append(healed_by_flag)

            if healer_success_flag not in healer.memory_flags:
                healer.memory_flags.append(healer_success_flag)
            dragon.trust[healer.id] = dragon.trust.get(healer.id, 0) + 1.0
            healer.reputation["kind"] = healer.reputation.get("kind", 0) + 0.3

            log_event(
                world,
                f"{healer.name} (skill {old_skill} → {healer.healer_skill}) successfully treated {dragon.name}'s injuries.",
                involved_ids=[healer.id, dragon.id],
                event_type="healed",
                importance=3,
            )