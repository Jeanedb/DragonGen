import random
from core.world import World
from core.generator import generate_dragonet
from core.sim.logging import log_event
from core.sim.relationships import add_friendship, add_rivalry
from core.sim.choices import resolve_choice
from core.sim.progression import tick_dragon_progression


def get_living_dragons(world: World):
    return [d for d in world.dragons if d.status == "Alive"]


def are_family(a, b):
    if a.id in b.parents or b.id in a.parents:
        return True
    if set(a.parents) & set(b.parents):
        return True
    return False


def friendship_weight(a, b):
    weight = 1.0

    friendly_traits = {"Kind", "Loyal", "Playful"}
    difficult_traits = {"Suspicious", "Moody", "Ambitious"}

    if a.personality in friendly_traits:
        weight += 0.4
    if b.personality in friendly_traits:
        weight += 0.4

    if a.personality in difficult_traits:
        weight -= 0.25
    if b.personality in difficult_traits:
        weight -= 0.25

    if are_family(a, b):
        weight += 0.6

    return max(0.2, weight)


def rivalry_weight(a, b):
    weight = 1.0

    rivalry_traits = {"Ambitious", "Moody", "Suspicious"}

    if a.personality in rivalry_traits:
        weight += 0.4
    if b.personality in rivalry_traits:
        weight += 0.4

    if a.role == "Warrior":
        weight += 0.2
    if b.role == "Warrior":
        weight += 0.2

    if a.role == "Dragonet":
        weight -= 0.6
    if b.role == "Dragonet":
        weight -= 0.6

    if are_family(a, b):
        weight -= 0.5

    return max(0.1, weight)


def injury_weight(dragon):
    weight = 1.0

    if dragon.personality == "Brave":
        weight += 0.5
    elif dragon.personality == "Clever":
        weight -= 0.2

    if dragon.role == "Hunter":
        weight += 0.35
    elif dragon.role == "Scout":
        weight += 0.25
    elif dragon.role == "Healer":
        weight -= 0.25
    elif dragon.role == "Dragonet":
        weight -= 0.40

    return max(0.2, weight)


def choose_friendship_pair(living):
    pairs = []

    for i in range(len(living)):
        for j in range(i + 1, len(living)):
            a = living[i]
            b = living[j]
            pairs.append((a, b))

    if not pairs:
        return None, None

    weights = [friendship_weight(a, b) for a, b in pairs]
    return random.choices(pairs, weights=weights, k=1)[0]


def choose_rivalry_pair(living):
    pairs = []

    for i in range(len(living)):
        for j in range(i + 1, len(living)):
            a = living[i]
            b = living[j]
            pairs.append((a, b))

    if not pairs:
        return None, None

    weights = [rivalry_weight(a, b) for a, b in pairs]
    return random.choices(pairs, weights=weights, k=1)[0]


def choose_injury_dragon(living):
    if not living:
        return None

    weights = [injury_weight(d) for d in living]
    return random.choices(living, weights=weights, k=1)[0]



def add_injury(world: World, dragon):
    if dragon.health == "Injured" or dragon.status != "Alive":
        return False

    dragon.health = "Injured"

    texts = [
        f"{dragon.name} was injured during a difficult patrol.",
        f"In the {world.tribe_name}, {dragon.name} was badly hurt.",
        f"{dragon.name} returned to camp injured after a dangerous outing.",
        f"{dragon.name} suffered an injury during the moon."
    ]
    text = random.choice(texts)
    log_event(world, text, involved_ids=[dragon.id], event_type="injury")
    return True


def add_friend_event(world: World, a, b):
    texts = [
        f"{a.name} and {b.name} spent the moon in easy company.",
        f"In the {world.tribe_name}, {a.name} and {b.name} spent time together.",
        f"{a.name} and {b.name} worked well together and strengthened their bond.",
        f"{a.name} sought out {b.name}, and the two enjoyed each other's company."
    ]
    text = random.choice(texts)
    log_event(world, text, involved_ids=[a.id, b.id], event_type="friend_event")
    return True


def add_rival_event(world: World, a, b):
    texts = [
        f"{a.name} and {b.name} argued again, and neither backed down.",
        f"{a.name} and {b.name} clashed over a dispute in the tribe.",
        f"In the {world.tribe_name}, {a.name} and {b.name} had a heated argument.",
        f"Old tension flared between {a.name} and {b.name} this moon."
    ]
    text = random.choice(texts)
    log_event(world, text, involved_ids=[a.id, b.id], event_type="rival_event")
    return True


def add_family_bond_event(world, a, b):
    texts = [
        f"{a.name} and {b.name} spent time together as kin and grew closer.",
        f"{a.name} and {b.name}, bound by family, supported each other this moon.",
    ]
    text = random.choice(texts)
    log_event(world, text, involved_ids=[a.id, b.id], event_type="family_bond")
    return True


def add_parent_child_event(world, parent, child):
    texts = [
        f"{parent.name} guided {child.name} through the challenges of the moon.",
        f"{parent.name} kept a close watch over {child.name}.",
    ]
    text = random.choice(texts)
    log_event(world, text, involved_ids=[parent.id, child.id], event_type="parent_child")
    return True


def add_family_conflict_event(world, a, b):
    texts = [
        f"{a.name} and {b.name} argued despite their shared blood.",
        f"Tension rose between {a.name} and {b.name}, even as family.",
    ]
    text = random.choice(texts)
    log_event(world, text, involved_ids=[a.id, b.id], event_type="family_conflict")
    return True


def try_family_event(world, living):
    family_pairs = []

    for i in range(len(living)):
        for j in range(i + 1, len(living)):
            a = living[i]
            b = living[j]

            if are_family(a, b):
                family_pairs.append((a, b))

    if not family_pairs:
        return False

    a, b = random.choice(family_pairs)
    roll = random.random()

    if a.id in b.parents:
        parent, child = a, b
    elif b.id in a.parents:
        parent, child = b, a
    else:
        parent, child = None, None

    if parent and child:
        return add_parent_child_event(world, parent, child)
    elif roll < 0.7:
        return add_family_bond_event(world, a, b)
    else:
        return add_family_conflict_event(world, a, b)


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
    if len(candidates) >= 2:
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

        texts = [
            f"{dragon.name} passed away under the stars.",
            f"The tribe mourns the loss of {dragon.name}.",
            f"In the {world.tribe_name}, {dragon.name} ascended to the sky after death.",
            f"{dragon.name} has died, leaving behind memories in the tribe."
        ]
        text = random.choice(texts)
        log_event(world, text, involved_ids=[dragon.id], event_type="death", importance=5)
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

    event_type, a, b = random.choice(candidates)

    if event_type == "friend":
        return add_friend_event(world, a, b)
    elif event_type == "rival":
        return add_rival_event(world, a, b)

    return False


def get_current_leader(world: World):
    for d in world.dragons:
        if d.status == "Alive" and d.rank == "Leader":
            return d
    return None


def get_current_deputy(world: World):
    for d in world.dragons:
        if d.status == "Alive" and d.rank == "Deputy":
            return d
    return None


def choose_leadership_candidate(world: World, exclude_ids=None):
    if exclude_ids is None:
        exclude_ids = []

    candidates = [
        d for d in world.dragons
        if d.status == "Alive"
        and d.role != "Dragonet"
        and d.id not in exclude_ids
    ]

    if not candidates:
        return None

    def candidate_weight(dragon):
        weight = 1.0

        if dragon.role in ["Warrior", "Scout", "Hunter"]:
            weight += 0.5
        if dragon.role == "Healer":
            weight -= 0.2
        if dragon.role == "Elder":
            weight -= 0.3

        if dragon.personality in ["Loyal", "Brave", "Clever", "Ambitious"]:
            weight += 0.4
        if dragon.personality == "Moody":
            weight -= 0.2

        return max(0.2, weight)

    weights = [candidate_weight(d) for d in candidates]
    return random.choices(candidates, weights=weights, k=1)[0]


def maintain_hierarchy(world: World):
    leader = get_current_leader(world)
    deputy = get_current_deputy(world)

    if leader is None:
        if deputy is not None:
            deputy.rank = "Leader"
            log_event(
                world,
                f"{deputy.name} has become the new Leader of the tribe.",
                involved_ids=[deputy.id],
                event_type="leadership_change",
                importance=5
            )
            leader = deputy
            deputy = None
        else:
            new_leader = choose_leadership_candidate(world)
            if new_leader:
                new_leader.rank = "Leader"
                log_event(
                    world,
                    f"{new_leader.name} has been chosen as Leader of the tribe.",
                    involved_ids=[new_leader.id],
                    event_type="leadership_change",
                    importance=5
                )
                leader = new_leader

    deputy = get_current_deputy(world)
    if deputy is None:
        exclude_ids = [leader.id] if leader else []
        new_deputy = choose_leadership_candidate(world, exclude_ids=exclude_ids)

        if new_deputy and new_deputy.rank != "Leader":
            new_deputy.rank = "Deputy"
            log_event(
                world,
                f"{new_deputy.name} has been appointed Deputy.",
                involved_ids=[new_deputy.id],
                event_type="leadership_change",
                importance=5
            )


def add_leader_event(world, leader):
    texts = [
        f"{leader.name}, leader of the tribe, made a decision that shaped the moon.",
        f"{leader.name} addressed the tribe, guiding them through the moon's challenges.",
        f"{leader.name} took charge during a tense moment in the tribe.",
    ]
    text = random.choice(texts)
    log_event(world, text, involved_ids=[leader.id], event_type="leader_event")
    return True


def add_deputy_event(world, deputy):
    texts = [
        f"{deputy.name}, the deputy, ensured order within the tribe.",
        f"{deputy.name} stepped in to support the leader during the moon.",
        f"{deputy.name} took responsibility and kept the tribe steady.",
    ]
    text = random.choice(texts)
    log_event(world, text, involved_ids=[deputy.id], event_type="deputy_event")
    return True


def try_leadership_event(world):
    leader = get_current_leader(world)
    deputy = get_current_deputy(world)

    roll = random.random()

    if leader and roll < 0.7:
        return add_leader_event(world, leader)
    elif deputy:
        return add_deputy_event(world, deputy)

    return False


# ---------- PLAYER CHOICES ----------

def create_injured_patrol_choice(world):
    candidates = [
        d for d in world.dragons
        if d.status == "Alive" and d.role != "Dragonet"
    ]

    if len(candidates) < 2:
        return False

    a, b = random.sample(candidates, 2)

    if a.health != "Injured":
        a.health = "Injured"
        log_event(
            world,
            f"{a.name} was injured while out on patrol with {b.name}.",
            involved_ids=[a.id, b.id],
            event_type="injury",
            importance=3
        )

    world.pending_choice = {
        "type": "injured_patrol_choice",
        "text": (
            f"{a.name} and {b.name} are on patrol. {a.name} is injured, and "
            f"rival dragons can be heard approaching. What should {b.name} do?"
        ),
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
    for dragon in living:
        for rival_id in dragon.rivals:
            rival = next((d for d in living if d.id == rival_id), None)
            if rival and dragon.id < rival.id:
                rival_pairs.append((dragon, rival))

    if not rival_pairs:
        return False

    a, b = random.choice(rival_pairs)

    world.pending_choice = {
        "type": "rival_confrontation_choice",
        "text": (
            f"{a.name} and {b.name}, long-standing rivals, cross paths during a tense patrol. "
            f"What should {a.name} do?"
        ),
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

    event_count = random.randint(2, 4)

    for _ in range(event_count):
        living = get_living_dragons(world)
        if len(living) < 2:
            break

        roll = random.random()
        success = False
        attempts = 0

        while not success and attempts < 10:
            attempts += 1

            if roll < 0.15:
                success = try_leadership_event(world)
            elif roll < 0.30:
                success = try_family_event(world, living)
            elif roll < 0.55:
                success = try_existing_relationship_event(world, living)
            elif roll < 0.65:
                a, b = choose_friendship_pair(living)
                if a and b:
                    success = add_friendship(world, a, b)
            elif roll < 0.90:
                a, b = choose_rivalry_pair(living)
                if a and b:
                    success = add_rivalry(world, a, b)
            else:
                dragon = choose_injury_dragon(living)
                if dragon:
                    success = add_injury(world, dragon)

            if success:
                break

            roll = random.random()

    world.event_log = world.event_log[-100:]
    return True