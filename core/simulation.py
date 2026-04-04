import random
from core.world import World
from core.generator import generate_dragonet
from core.sim.logging import log_event
from core.sim.relationships import add_friendship, add_rivalry
from core.sim.choices import resolve_choice
from core.sim.progression import tick_dragon_progression
from core.sim.events import run_event_phase
from core.sim.leadership import maintain_hierarchy


def are_family(a, b):
    if a.id in b.parents or b.id in a.parents:
        return True
    if set(a.parents) & set(b.parents):
        return True
    return False

def get_living_dragons(world: World):
    return [d for d in world.dragons if d.status == "Alive"]



def add_friend_event(world, a, b):
    if ("saved_by", b.id) in a.memory_flags:
        text = f"{a.name} stayed close to {b.name}, still remembering when {b.name} helped them in a moment of danger."
    elif ("saved_by", a.id) in b.memory_flags:
        text = f"{b.name} sought out {a.name}, remembering the help they were once given."
    elif a.trust.get(b.id, 0) >= 3 or b.trust.get(a.id, 0) >= 3:
        text = f"{a.name} and {b.name} naturally fell into each other's company, their bond now an easy one."	
    else:
        texts = [
            f"{a.name} and {b.name} spent the moon in easy company.",
            f"In the {world.tribe_name}, {a.name} and {b.name} spent time together.",
            f"{a.name} and {b.name} worked well together and strengthened their bond.",
            f"{a.name} sought out {b.name}, and the two enjoyed each other's company."
        ]
        text = random.choice(texts)

    log_event(world, text, involved_ids=[a.id, b.id], event_type="friend_event")
    return True


def add_rival_event(world, a, b):
    if ("abandoned_by", b.id) in a.memory_flags:
        text = f"{a.name} clashed with {b.name}, still carrying the sting of being abandoned when it mattered."
    elif ("abandoned_by", a.id) in b.memory_flags:
        text = f"{b.name} met {a.name} with open hostility, old resentment still hanging between them."
    elif a.resentment.get(b.id, 0) >= 3 or b.resentment.get(a.id, 0) >= 3:
        text = f"The hostility between {a.name} and {b.name} no longer feels like a passing disagreement."
    else:
        texts = [
            f"{a.name} and {b.name} argued again, and neither backed down.",
            f"{a.name} and {b.name} clashed over a dispute in the tribe.",
            f"In the {world.tribe_name}, {a.name} and {b.name} had a heated argument.",
            f"Old tension flared between {a.name} and {b.name} this moon."
        ]
        text = random.choice(texts)

    log_event(world, text, involved_ids=[a.id, b.id], event_type="rival_event")
    return True

def add_new_dragonet(world: World):
    if not world.dragons:
        return False

    existing_ids = [d.id for d in world.dragons]
    new_id = max(existing_ids) + 1 if existing_ids else 1

    chosen_tribe = random.choice(world.dragons).tribe

    candidates = [
        d for d in world.dragons
        if d.status == "Alive" and d.role != "Dragonet"
    ]

    parents = []

    # Prefer living mate pairs
    mate_pairs = []
    seen_pairs = set()

    for d in candidates:
        if d.mate_id is None:
            continue

        mate = next((x for x in candidates if x.id == d.mate_id), None)
        if not mate:
            continue

        pair_key = tuple(sorted((d.id, mate.id)))
        if pair_key in seen_pairs:
            continue

        seen_pairs.add(pair_key)

        # optional light weighting by trust
        trust_bonus = d.trust.get(mate.id, 0) + mate.trust.get(d.id, 0)
        weight = 1.0 + (trust_bonus * 0.1)

        mate_pairs.append((d, mate, weight))

    if mate_pairs and random.random() < 0.8:
        pair_choices = [(a, b) for a, b, _ in mate_pairs]
        pair_weights = [w for _, _, w in mate_pairs]
        p1, p2 = random.choices(pair_choices, weights=pair_weights, k=1)[0]
        parents = [p1, p2]

    elif len(candidates) >= 2:
        parents = random.sample(candidates, 2)
    elif len(candidates) == 1:
        parents = [candidates[0]]

    dragonet = generate_dragonet(new_id, chosen_tribe, parents)
    dragonet.parents = [p.id for p in parents]

    world.dragons.append(dragonet)

    for p in parents:
        p.dragonets.append(dragonet.id)

    if parents:
        parent_names = " and ".join([p.name for p in parents])
        text = f"{parent_names} welcomed a new dragonet named {dragonet.name}."
        ids = [dragonet.id] + [p.id for p in parents]
    else:
        text = f"A new dragonet named {dragonet.name} appeared in the tribe."
        ids = [dragonet.id]

    log_event(world, text, involved_ids=ids, event_type="birth", importance=4)
    return True


def handle_possible_death(world: World, dragon):
    if dragon.status != "Alive":
        return False

    death_chance = 0.0

    if dragon.age_moons >= 180:
        death_chance += 0.02
    if dragon.age_moons >= 220:
        death_chance += 0.05
    if dragon.age_moons >= 260:
        death_chance += 0.10

    if dragon.role == "Elder":
        death_chance += 0.03

    if dragon.health == "Injured":
        death_chance += 0.05

    if random.random() < death_chance:
        dragon.status = "Dead"
        dragon.health = "Dead"

        surviving_mate = None

        if dragon.mate_id is not None:
            surviving_mate = next(
                (d for d in world.dragons if d.id == dragon.mate_id and d.status == "Alive"),
                None
            )

            if surviving_mate:
                flag = ("lost_mate", dragon.id)
                if flag not in surviving_mate.memory_flags:
                    surviving_mate.memory_flags.append(flag)

                surviving_mate.mate_id = None

                if hasattr(world, "tension"):
                    world.tension += 0.18

        if surviving_mate:
            texts = [
                f"{dragon.name} passed away under the stars, leaving {surviving_mate.name} behind in grief.",
                f"The tribe mourns the loss of {dragon.name}, and {surviving_mate.name} seems deeply shaken.",
                f"In the {world.tribe_name}, {dragon.name} died, leaving their mate {surviving_mate.name} to carry the loss.",
            ]
        else:
            texts = [
                f"{dragon.name} passed away under the stars.",
                f"The tribe mourns the loss of {dragon.name}.",
                f"In the {world.tribe_name}, {dragon.name} ascended to the sky after death.",
                f"{dragon.name} has died, leaving behind memories in the tribe."
            ]

        text = random.choice(texts)
        log_event(world, text, involved_ids=[dragon.id], event_type="death", importance=5)

        dragon.mate_id = None
        return True

    return False


def try_existing_relationship_event(world: World, living):
    candidates = []

    for dragon in living:
        for friend_id in dragon.friends:
            friend = next((d for d in living if d.id == friend_id), None)
            if friend and dragon.id < friend.id:
                candidates.append(("friend", dragon, friend))

        for rival_id in dragon.rivals:
            rival = next((d for d in living if d.id == rival_id), None)
            if rival and dragon.id < rival.id:
                candidates.append(("rival", dragon, rival))

    if not candidates:
        return False

    # grief check first
    grief_candidates = [
        d for d in living
        if any(flag == "lost_mate" for flag, _ in d.memory_flags)
    ]

    if grief_candidates and random.random() < 0.25:
        d = random.choice(grief_candidates)

        texts = [
            f"{d.name} kept to themselves this moon, still grieving their loss.",
            f"{d.name} seemed distant and withdrawn, the loss of their mate still weighing heavily.",
            f"{d.name} avoided others this moon, grief still close beneath the surface."
        ]

        log_event(
            world,
            random.choice(texts),
            involved_ids=[d.id],
            event_type="grief_event",
            importance=3
        )
        return True

    event_type, a, b = random.choice(candidates)

    if event_type == "friend":
        return add_friend_event(world, a, b)
    elif event_type == "rival":
        return add_rival_event(world, a, b)

    return False



# ---------- PLAYER CHOICES ----------

def create_injured_patrol_choice(world):
    candidates = [
        d for d in world.dragons
        if d.status == "Alive" and d.role != "Dragonet"
    ]

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

            # If b once saved a, make it more likely they end up in this kind of moment again
            if ("saved_by", b.id) in a.memory_flags:
                weight += 1.5

            # If b once abandoned a, also make it more likely they cross paths again
            if ("abandoned_by", b.id) in a.memory_flags:
                weight += 1.2

            if a.mate_id == b.id or b.mate_id == a.id:
                weight += 1.8

            # existing strong feelings also increase likelihood of meaningful encounters
            weight += a.trust.get(b.id, 0) * 0.15
            weight += a.resentment.get(b.id, 0) * 0.20

            possible_pairs.append((a, b, weight))

    if not possible_pairs:
        return False

    pairs = [(a, b) for a, b, _ in possible_pairs]
    weights = [w for _, _, w in possible_pairs]
    a, b = random.choices(pairs, weights=weights, k=1)[0]

    if a.health != "Injured":
        a.health = "Injured"
        log_event(
            world,
            f"{a.name} was injured while out on patrol with {b.name}.",
            involved_ids=[a.id, b.id],
            event_type="injury",
            importance=3
        )

    if a.mate_id == b.id or b.mate_id == a.id:
        prompt_text = (
            f"{a.name} and {b.name} are on patrol together. When {a.name} is injured and rival dragons can be heard approaching, "
            f"{b.name} must decide whether to stay with their mate or run for help."
        )
    elif ("saved_by", b.id) in a.memory_flags:
        prompt_text = (
            f"{a.name} and {b.name} are on patrol. {a.name} is injured again, and rival dragons can be heard approaching. "
            f"{a.name} still remembers that {b.name} once stayed when it mattered. What should {b.name} do now?"
        )
    elif ("abandoned_by", b.id) in a.memory_flags:
        prompt_text = (
            f"{a.name} and {b.name} are on patrol. {a.name} is injured, and rival dragons can be heard approaching. "
            f"{a.name} has never forgotten the last time {b.name} left. What should {b.name} do now?"
        )
    else:
        prompt_text = (
            f"{a.name} and {b.name} are on patrol. {a.name} is injured, and "
            f"rival dragons can be heard approaching. What should {b.name} do?"
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
    living = get_living_dragons(world)

    rival_pairs = []
    weights = []

    for dragon in living:
        for rival_id in dragon.rivals:
            rival = next((d for d in living if d.id == rival_id), None)
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

                rival_pairs.append((dragon, rival))
                weights.append(weight)

    if not rival_pairs:
        return False

    a, b = random.choices(rival_pairs, weights=weights, k=1)[0]

    if ("abandoned_by", b.id) in a.memory_flags:
        prompt_text = (
            f"{a.name} and {b.name}, long-standing rivals, cross paths during a tense patrol. "
            f"{a.name} still carries the memory of being abandoned by {b.name}. What should {a.name} do?"
        )
    elif ("abandoned_by", a.id) in b.memory_flags:
        prompt_text = (
            f"{a.name} and {b.name}, long-standing rivals, cross paths during a tense patrol. "
            f"Old resentment still hangs between them. What should {a.name} do?"
        )
    elif a.resentment.get(b.id, 0) >= 3 or b.resentment.get(a.id, 0) >= 3:
        prompt_text = (
            f"{a.name} and {b.name}, long-standing rivals, cross paths during a tense patrol. "
            f"The hostility between them no longer feels like a passing disagreement. What should {a.name} do?"
        )
    else:
        prompt_text = (
            f"{a.name} and {b.name}, long-standing rivals, cross paths during a tense patrol. "
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




def advance_moon(world: World):
    if world.pending_choice is not None:
        return False

    world.moon += 1
    living = get_living_dragons(world)

    for dragon in living:
        tick_dragon_progression(world, dragon, living)
        handle_possible_death(world, dragon)

    maintain_hierarchy(world)

    if random.random() < 0.20:
        add_new_dragonet(world)

    # occasional player choice
    if world.pending_choice is None:
        choice_roll = random.random()

        if choice_roll < 0.08:
            created = create_injured_patrol_choice(world)
            if created:
                world.event_log = world.event_log[-100:]
                return True

        elif choice_roll < 0.14:
            created = create_rival_confrontation_choice(world)
            if created:
                world.event_log = world.event_log[-100:]
                return True
        


    run_event_phase(world)

    for dragon in world.dragons:
        for k in list(dragon.trust.keys()):
            dragon.trust[k] *= 0.95
            if dragon.trust[k] < 0.1:
                del dragon.trust[k]

        for k in list(dragon.resentment.keys()):
            dragon.resentment[k] *= 0.95
            if dragon.resentment[k] < 0.1:
                del dragon.resentment[k]

    world.tension = max(0.0, min(5.0, world.tension))

    world.event_log = world.event_log[-100:]
    return True