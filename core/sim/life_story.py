"""Connect durable personal memories to later village events."""

from core.sim.logging import log_event
from core.sim.memory import Memory, add_memory

STORY_EVENT_TYPES = {
    "received_ration": "shared_ration",
    "received_returned_ration": "returned_ration",
    "went_without_ration": "kept_rations",
    "went_without_returned_ration": "kept_rations_when_owed",
    "accused_of_favouritism": "resented_ration_sharing",
    "received_expedition_credit": "shared_expedition_credit",
    "denied_expedition_credit": "claimed_expedition_credit",
}

STORY_LINES = {
    "shared_ration": "{dragon} shared a meal with {other} when they were recovering.",
    "received_ration": "{other} shared a meal with {dragon} during a hard recovery.",
    "returned_ration": "{dragon} remembered {other}'s kindness and returned the favour when they needed food.",
    "received_returned_ration": "{other} returned the kindness {dragon} had shown them.",
    "kept_rations": "{dragon} kept the food in reserve when {other} was recovering.",
    "went_without_ration": "{dragon} went without a shared meal while the tribe kept its stores in reserve.",
    "kept_rations_when_owed": "{dragon} kept the food in reserve when {other} needed help.",
    "went_without_returned_ration": "{dragon} remembered helping {other}, who kept the food in reserve this time.",
    "resented_ration_sharing": "{dragon} thought {other} had played favourites with the tribe's food.",
    "accused_of_favouritism": "{other} saw {dragon}'s shared meal as favouritism.",
    "shared_expedition_credit": "{dragon} gave their training rival {other} credit for guiding the party home.",
    "received_expedition_credit": "{other} gave {dragon} credit for guiding the expedition home.",
    "claimed_expedition_credit": "{dragon} took the credit for an expedition that {other} guided home.",
    "denied_expedition_credit": "{other} took the credit for an expedition that {dragon} guided home.",
    "mentored": "{dragon} trained {other} as their student.",
    "mentored_by": "{dragon} learned from their mentor, {other}.",
    "returned_mentor_help": "{dragon} stayed to help their injured mentor, {other}.",
    "helped_by_former_student": "{dragon}'s former student {other} stayed to help them on patrol.",
    "lost_mentor": "{dragon} mourned the loss of their mentor, {other}.",
    "defected_after_betrayal": "{dragon} left the tribe after their dispute with {other}.",
    "tribemate_defected": "{other} left the tribe after their dispute with {dragon}.",
    "heard_at_border": "{dragon} told {other} how it felt to be left behind.",
    "heard_former_tribemate": "{dragon} heard {other} out at the border.",
    "turned_away_at_border": "{other} turned {dragon} away at the border.",
    "turned_away_former_tribemate": "{dragon} turned {other} away at the border.",
    "lost_student": "{dragon} mourned the loss of their student, {other}.",
}


def can_return_mentor_help(mentor, student, moon):
    return (
        any(m.type == "mentored_by" and m.other_id == mentor.id and m.moon < moon for m in student.memories)
        and not any(m.type == "returned_mentor_help" and m.other_id == mentor.id for m in student.memories)
    )


def record_mentor_rescue(world, mentor, student):
    add_memory(student, Memory("returned_mentor_help", world.moon, mentor.id, importance=6))
    add_memory(mentor, Memory("helped_by_former_student", world.moon, student.id, importance=6))
    log_event(
        world, STORY_LINES["returned_mentor_help"].format(dragon=student.name, other=mentor.name),
        involved_ids=[student.id, mentor.id], event_type="returned_mentor_help", importance=6,
    )


def mourn_mentor_relationships(world, deceased):
    for survivor in world.dragons:
        if survivor.status != "Alive":
            continue
        for bond, loss in (("mentored_by", "lost_mentor"), ("mentored", "lost_student")):
            if not any(m.type == bond and m.other_id == deceased.id for m in survivor.memories):
                continue
            if any(m.type == loss and m.other_id == deceased.id for m in survivor.memories):
                continue
            survivor.grief_level = max(survivor.grief_level, 4)
            add_memory(survivor, Memory(loss, world.moon, deceased.id, importance=6))
            log_event(
                world, STORY_LINES[loss].format(dragon=survivor.name, other=deceased.name),
                involved_ids=[survivor.id, deceased.id], event_type=loss, importance=6,
            )


def defining_memories(dragon):
    """Keep the first lesson with each dragon, plus recurring story milestones."""
    seen_lessons = set()
    for memory in sorted(dragon.memories, key=lambda item: item.moon):
        if memory.type not in STORY_LINES:
            continue
        if memory.type in {"mentored", "mentored_by"}:
            key = (memory.type, memory.other_id)
            if key in seen_lessons:
                continue
            seen_lessons.add(key)
        yield memory


def life_story_paragraph(dragon, world):
    """Summarize a relationship through up to three recorded turning points."""
    names = {member.id: member.name for member in world.dragons}
    by_partner = {}
    for memory in defining_memories(dragon):
        if memory.other_id in names:
            moments = by_partner.setdefault(memory.other_id, {})
            moments.setdefault(memory.type, memory)

    def story_priority(moments):
        return (
            min(3, len(moments)),
            max(memory.importance for memory in moments),
            moments[-1].moon,
        )

    story = max(
        (list(moments.values()) for moments in by_partner.values()),
        key=story_priority,
        default=[],
    )
    # Preserve where a longer relationship began and its two most recent turns.
    if len(story) > 3:
        story = [story[0], *story[-2:]]
    return " ".join(
        f"On Moon {memory.moon}, "
        + STORY_LINES[memory.type].format(dragon=dragon.name, other=names[memory.other_id])
        for memory in story
    )


def set_followed(world, dragon_id, following):
    followed = world.world_flags.setdefault("followed_dragons", [])
    if following and dragon_id not in followed:
        followed.append(dragon_id)
    elif not following and dragon_id in followed:
        followed.remove(dragon_id)


def decision_follow_candidate(world, events, option_id):
    # Each event lists participants in its own narrative order.
    spotlight = {
        "choice_loyalty": 1,
        "returned_mentor_help": 0,
        "shared_expedition_credit": 0,
        "shared_ration": 0,
        "returned_ration": 0,
    }
    if option_id == "hear_out":
        spotlight["defector_return"] = 1

    followed = world.world_flags.get("followed_dragons", [])
    for event in events:
        event_type = event.get("type")
        if event_type not in spotlight:
            continue
        index = spotlight[event_type]
        ids = event.get("involved_ids") or []
        if index < len(ids) and ids[index] not in followed:
            return next((dragon for dragon in world.dragons if dragon.id == ids[index]), None)
    return None
