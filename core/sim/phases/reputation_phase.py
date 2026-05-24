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

            # base drift toward objective reputation
            new_value = current + (rep_score * 0.05)

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

                new_value += other_view * 0.02 * trust * resistance

            observer.perceived_reputation[target.id] = new_value