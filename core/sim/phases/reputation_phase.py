from core.sim.behavior import get_behavior_score

def run_reputation_phase(world):

    for observer in world.dragons:
        for target in world.dragons:

            if observer.id == target.id:
                continue

            rep_score = (
                target.reputation.get("kind", 0)
                - target.reputation.get("harsh", 0)
            )

            current = observer.perceived_reputation.get(target.id, 0)

            reputation_importance = get_behavior_score(
                observer,
                "reputation_importance"
            )

            # Dragons who care more about reputation form stronger opinions
            reputation_rate = 0.025 + (reputation_importance * 0.05)

            new_value = current + (rep_score * reputation_rate)

            # social influence: trusted dragons affect opinion
            for other in world.dragons:

                if other.id == observer.id or other.id == target.id:
                    continue

                trust = observer.trust.get(other.id, 0)

                if trust <= 0:
                    continue

                other_view = other.perceived_reputation.get(target.id, 0)

                personality = getattr(observer, "personality", "Neutral")

                resistance = 1.0

                if personality == "Stubborn":
                    resistance = 0.5
                elif personality == "Loyal":
                    resistance = 0.7
                elif personality == "Clever":
                    resistance = 0.6
                elif personality == "Moody":
                    resistance = 1.2

                social_reputation_rate = 0.01 + (reputation_importance * 0.02)

                new_value += (
                    other_view
                    * social_reputation_rate
                    * trust
                    * resistance
                )

            observer.perceived_reputation[target.id] = new_value