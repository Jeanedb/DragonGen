import random

from core.sim.logging import log_event
from core.sim.politics import get_most_hostile_relation
from core.sim.regions import (
    get_random_region,
    get_random_landmark,
    record_region_activity,
)
from core.sim.world_state import (
    get_tribe_climate,
    get_world_mood,
    get_eligible_non_dragonets,
)



def create_injured_patrol_choice(world):
    climate = get_tribe_climate(world)
    hostile_tribe, hostile_score = get_most_hostile_relation(world)

    region = None
    landmark = None

    if hostile_tribe and hostile_score <= -20:
        region = get_random_region(world, hostile_tribe)
        landmark = get_random_landmark(world, region)
        record_region_activity(world, region)

    candidates = get_eligible_non_dragonets(world)

    if len(candidates) < 2:
        return False

    possible_pairs = []

    for i in range(len(candidates)):
        for j in range(len(candidates)):
            if i == j:
                continue

            a = candidates[i]  # injured dragon
            b = candidates[j]  # helper dragon

            weight = 1.0

            if ("saved_by", b.id) in a.memory_flags:
                weight += 1.5

            if ("abandoned_by", b.id) in a.memory_flags:
                weight += 1.2

            if a.mate_id == b.id or b.mate_id == a.id:
                weight += 1.8

            weight += a.trust.get(b.id, 0) * 0.15
            weight += a.resentment.get(b.id, 0) * 0.20

            weight *= max(
                0.25,
                1.0
                + climate["risk_bias"]
                + (climate["conflict_bias"] * 0.35)
                - (climate["recovery_bias"] * 0.20)
            )

            if hostile_score <= -40:
                weight *= 1.35
            elif hostile_score <= -20:
                weight *= 1.15

            possible_pairs.append((a, b, weight))

    if not possible_pairs:
        return False

    pairs = [(a, b) for a, b, _ in possible_pairs]
    weights = [w for _, _, w in possible_pairs]
    a, b = random.choices(pairs, weights=weights, k=1)[0]

    if a.health != "Injured":
        a.health = "Injured"

        if hostile_tribe and hostile_score <= -20:
            location_text = f" near {landmark} in {region}" if region and landmark else ""
            injury_text = (
                f"{a.name} was injured while out on patrol with {b.name}{location_text}, "
                f"not far from territory where tension with the {hostile_tribe}s has been rising."
            )
        else:
            injury_text = f"{a.name} was injured while out on patrol with {b.name}."

        log_event(
            world,
            injury_text,
            involved_ids=[a.id, b.id],
            event_type="injury",
            importance=3
        )

    mood = get_world_mood(world)

    approaching_tribe_text = "rival dragons"
    if hostile_tribe and hostile_score <= -20:
        approaching_tribe_text = f"{hostile_tribe} dragons"

    if a.mate_id == b.id or b.mate_id == a.id:
        prompt_text = (
            f"{a.name} and {b.name} are on patrol together. When {a.name} is injured and "
            f"{approaching_tribe_text} can be heard approaching, "
            f"{b.name} must decide whether to stay with their mate or run for help."
        )
    elif ("saved_by", b.id) in a.memory_flags:
        prompt_text = (
            f"{a.name} and {b.name} are on patrol. {a.name} is injured again, and "
            f"{approaching_tribe_text} can be heard approaching. "
            f"{a.name} still remembers that {b.name} once stayed when it mattered. "
            f"What should {b.name} do now?"
        )
    elif ("abandoned_by", b.id) in a.memory_flags:
        prompt_text = (
            f"{a.name} and {b.name} are on patrol. {a.name} is injured, and "
            f"{approaching_tribe_text} can be heard approaching. "
            f"{a.name} has never forgotten the last time {b.name} left. "
            f"What should {b.name} do now?"
        )
    else:
        if mood in {"Volatile", "Crisis"}:
            prompt_text = (
                f"{a.name} and {b.name} are on patrol in a tribe already on edge. "
                f"{a.name} is injured, and {approaching_tribe_text} can be heard approaching through the darkness. "
                f"What should {b.name} do?"
            )
        elif climate["recovery_bias"] > 0.20:
            prompt_text = (
                f"{a.name} and {b.name} are on patrol. {a.name} is injured, and "
                f"{approaching_tribe_text} can be heard approaching. "
                f"In a tribe that still seems to hold together, what should {b.name} do?"
            )
        else:
            prompt_text = (
                f"{a.name} and {b.name} are on patrol. {a.name} is injured, and "
                f"{approaching_tribe_text} can be heard approaching. "
                f"What should {b.name} do?"
            )

    world.pending_choice = {
        "type": "injured_patrol_choice",
        "text": prompt_text,
        "involved_ids": [a.id, b.id],
        "options": [
            {"id": "stay_and_help", "text": f"Stay and help {a.name}"},
            {"id": "run_for_help", "text": "Return to camp for help"}
        ]
    }
    return True


def create_rival_confrontation_choice(world):
    climate = get_tribe_climate(world)
    mood = get_world_mood(world)
    eligible = get_eligible_non_dragonets(world)

    rival_pairs = []
    weights = []

    for dragon in eligible:
        for rival_id in dragon.rivals:
            rival = next((d for d in eligible if d.id == rival_id), None)
            if rival and dragon.id < rival.id:
                weight = 1.0

                # abandonment history makes confrontation more likely
                if ("abandoned_by", rival.id) in dragon.memory_flags:
                    weight += 1.2
                if ("abandoned_by", dragon.id) in rival.memory_flags:
                    weight += 1.2

                # stronger resentment makes this pair more likely to surface
                weight += dragon.resentment.get(rival.id, 0) * 0.20
                weight += rival.resentment.get(dragon.id, 0) * 0.20

                # perceived reputation can make certain rivalries surface more often
                weight -= dragon.perceived_reputation.get(rival.id, 0) * 0.10
                weight -= rival.perceived_reputation.get(dragon.id, 0) * 0.10

                # climate effect:
                # tense, suspicious, conflict-heavy tribes surface more confrontation dilemmas
                weight *= max(
                    0.25,
                    1.0
                    + climate["conflict_bias"]
                    + (climate["suspicion_bias"] * 0.40)
                    - (climate["recovery_bias"] * 0.20)
                    - (climate["mercy_bias"] * 0.15)
                )

                rival_pairs.append((dragon, rival))
                weights.append(weight)

    if not rival_pairs:
        return False



    a, b = random.choices(rival_pairs, weights=weights, k=1)[0]

    if ("abandoned_by", b.id) in a.memory_flags:
        prompt_text = (
            f"{a.name} and {b.name}, long-standing rivals, cross paths on patrol. "
            f"{a.name} still carries the memory of being abandoned by {b.name}. What should {a.name} do?"
        )
    elif ("abandoned_by", a.id) in b.memory_flags:
        prompt_text = (
            f"{a.name} and {b.name}, long-standing rivals, cross paths on patrol. "
            f"Old resentment still hangs between them. What should {a.name} do?"
        )
    elif a.resentment.get(b.id, 0) >= 3 or b.resentment.get(a.id, 0) >= 3:
        prompt_text = (
            f"{a.name} and {b.name}, long-standing rivals, cross paths on patrol. "
            f"The hostility between them no longer feels like a passing disagreement. What should {a.name} do?"
        )
    else:
        if mood in {"Volatile", "Crisis"}:
            prompt_text = (
                f"{a.name} and {b.name}, long-standing rivals, cross paths during a patrol while the tribe is already on edge. "
                f"What should {a.name} do?"
            )
        elif climate["mercy_bias"] > 0.20:
            prompt_text = (
                f"{a.name} and {b.name}, long-standing rivals, cross paths on patrol. "
                f"The tribe seems steadier than usual, but the tension between them remains. What should {a.name} do?"
            )
        elif climate["suspicion_bias"] > 0.20:
            prompt_text = (
                f"{a.name} and {b.name}, long-standing rivals, cross paths on patrol in a tribe grown watchful and uneasy. "
                f"What should {a.name} do?"
            )
        else:
            prompt_text = (
                f"{a.name} and {b.name}, long-standing rivals, cross paths on patrol. "
                f"What should {a.name} do?"
            )

    world.pending_choice = {
        "type": "rival_confrontation_choice",
        "text": prompt_text,
        "involved_ids": [a.id, b.id],
        "options": [
            {"id": "back_down", "text": f"Have {a.name} back down and avoid a fight"},
            {"id": "confront", "text": f"Have {a.name} confront {b.name} directly"}
        ]
    }
    return True

