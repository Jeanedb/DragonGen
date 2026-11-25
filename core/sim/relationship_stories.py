"""Choices that revisit a specific relationship in a new situation."""

import random

from core.sim.life_story import STORY_LINES
from core.sim.logging import log_event
from core.sim.memory import Memory, add_memory

RATION_COST = 2
RETURN_DELAY = 3


def remembers(dragon, kinds, other):
    return any(memory.type in kinds and memory.other_id == other.id for memory in dragon.memories)


def living_adults(world):
    return [dragon for dragon in world.dragons if dragon.status == "Alive" and dragon.role != "Dragonet"]


def record_story(world, actor, other, kinds):
    for dragon, partner, kind in ((actor, other, kinds[0]), (other, actor, kinds[1])):
        add_memory(dragon, Memory(kind, world.moon, partner.id, importance=5))
    text = STORY_LINES[kinds[0]].format(dragon=actor.name, other=other.name)
    log_event(world, text, involved_ids=[actor.id, other.id], event_type=kinds[0], importance=5)


def offer_ration_story(world, actor, recipient, returning):
    if returning:
        text = (
            f"{actor.name} remembers the meal {recipient.name} shared when they were recovering. "
            f"Now {recipient.name} is struggling, and {actor.name} wants to return the favour."
        )
    else:
        text = (
            f"Food is running low, and {recipient.name} is still recovering. "
            f"Their friend {actor.name} wants to bring them something from the reserve."
        )
    world.pending_choice = {
        "type": "friendship_rations",
        "location": "village",
        "actor_id": actor.id,
        "other_id": recipient.id,
        "returning": returning,
        "text": text,
        "options": [
            {"id": "share", "text": f"Share a meal with {recipient.name} ({RATION_COST} food)"},
            {"id": "reserve", "text": "Keep the food in the communal reserve"},
        ],
    }


def try_friendship_rations(world):
    if world.pending_choice is not None or world.food_stores < RATION_COST:
        return False

    adults = living_adults(world)
    short_on_food = world.food_stores <= sum(dragon.status == "Alive" for dragon in world.dragons)
    adults_by_id = {dragon.id: dragon for dragon in adults}
    for actor in adults:
        if actor.health != "Healthy":
            continue
        for memory in actor.memories:
            if memory.type != "received_ration" or world.moon - memory.moon < RETURN_DELAY:
                continue
            donor = adults_by_id.get(memory.other_id)
            if donor is None or not (short_on_food or donor.health == "Injured"):
                continue
            if not remembers(actor, {"returned_ration", "kept_rations_when_owed"}, donor):
                offer_ration_story(world, actor, donor, returning=True)
                return True

    if not short_on_food or world.moon < world.world_flags.get("last_friendship_rations_moon", -4) + 4:
        return False
    pairs = [
        (actor, recipient)
        for recipient in adults if recipient.health == "Injured"
        for actor in adults
        if actor.health == "Healthy"
        and (recipient.id in actor.friends or actor.id in recipient.friends)
        and not remembers(actor, {"shared_ration", "kept_rations"}, recipient)
    ]
    if not pairs or random.random() >= 0.25:
        return False
    actor, recipient = random.choice(pairs)
    offer_ration_story(world, actor, recipient, returning=False)
    world.world_flags["last_friendship_rations_moon"] = world.moon
    return True


def story_participants(world):
    choice = world.pending_choice
    adults = {dragon.id: dragon for dragon in living_adults(world)}
    return adults.get(choice["actor_id"]), adults.get(choice["other_id"])


def resolve_friendship_rations(world, option_id):
    actor, recipient = story_participants(world)
    if actor is None or recipient is None:
        return "The meal can no longer take place."

    returning = world.pending_choice["returning"]
    if option_id == "reserve":
        kinds = (
            ("kept_rations_when_owed", "went_without_returned_ration")
            if returning else ("kept_rations", "went_without_ration")
        )
        record_story(world, actor, recipient, kinds)
        return "The food stayed in reserve. Both dragons will remember the decision."

    if option_id != "share" or world.food_stores < RATION_COST:
        return "The shared meal is no longer available."

    world.food_stores -= RATION_COST
    recipient.trust[actor.id] = recipient.trust.get(actor.id, 0) + (1.5 if returning else 1)
    actor.trust[recipient.id] = actor.trust.get(recipient.id, 0) + 0.5
    kinds = ("returned_ration", "received_returned_ration") if returning else ("shared_ration", "received_ration")
    record_story(world, actor, recipient, kinds)
    # A dragon who already resents the donor can see the meal as favouritism.
    if not returning:
        witness = next(
            (dragon for dragon in living_adults(world)
             if dragon.id not in {actor.id, recipient.id} and dragon.resentment.get(actor.id, 0) >= 2),
            None,
        )
        if witness:
            witness.resentment[actor.id] += 0.5
            record_story(world, witness, actor, ("resented_ration_sharing", "accused_of_favouritism"))
    return f"The tribe spent {RATION_COST} food. {recipient.name} trusts {actor.name} more."


def try_expedition_credit(world, party):
    if world.pending_choice is not None:
        return False

    for actor in party:
        for other in party:
            if actor.id == other.id or not remembers(actor, {"was_embarrassed_by"}, other):
                continue
            if remembers(actor, {"shared_expedition_credit", "received_expedition_credit",
                                 "claimed_expedition_credit", "denied_expedition_credit"}, other):
                continue
            world.pending_choice = {
                "type": "expedition_credit",
                "location": "border",
                "actor_id": actor.id,
                "other_id": other.id,
                "text": (
                    f"{actor.name} still remembers being embarrassed by {other.name} during training. "
                    f"On today's expedition, {other.name} found the way back when the party lost its bearings. "
                    f"Now the tribe is waiting to hear {actor.name}'s report."
                ),
                "options": [
                    {"id": "credit_rival", "text": f"Give {other.name} credit for guiding the party home"},
                    {"id": "claim_credit", "text": f"Let {actor.name} take the credit"},
                ],
            }
            return True
    return False


def resolve_expedition_credit(world, option_id):
    actor, other = story_participants(world)
    if actor is None or other is None:
        return "The expedition report can no longer be given."

    if option_id == "credit_rival":
        for dragon, partner in ((actor, other), (other, actor)):
            dragon.trust[partner.id] = dragon.trust.get(partner.id, 0) + 0.75
            dragon.resentment[partner.id] = max(0, dragon.resentment.get(partner.id, 0) - 1)
        other.reputation["reliable"] = other.reputation.get("reliable", 0) + 0.5
        record_story(world, actor, other, ("shared_expedition_credit", "received_expedition_credit"))
        return f"{actor.name} and {other.name} trust each other more. Both will remember who gave credit."
    if option_id == "claim_credit":
        actor.reputation["reliable"] = actor.reputation.get("reliable", 0) + 0.5
        other.resentment[actor.id] = other.resentment.get(actor.id, 0) + 2
        if actor.id not in other.rivals:
            other.rivals.append(actor.id)
        record_story(world, actor, other, ("claimed_expedition_credit", "denied_expedition_credit"))
        return f"{actor.name}'s reputation improved, and {other.name} resents them for taking the credit."
    return "That response to the expedition report is unavailable."
