from core.sim.logging import log_event


def handle_ai_conversation_choice(world, option_id):
    choice = world.pending_choice
    ids = choice.get("involved_ids", [])

    if len(ids) < 2:
        return

    initiator = next((d for d in world.dragons if d.id == ids[0]), None)
    target = next((d for d in world.dragons if d.id == ids[1]), None)

    if not initiator or not target:
        return

    mood = choice.get("conversation_mood", "neutral")

    if option_id == "hear_them_out":
        initiator.trust[target.id] = initiator.trust.get(target.id, 0) + 0.6
        target.trust[initiator.id] = target.trust.get(initiator.id, 0) + 0.3
        world.tension = max(0, world.tension - 0.04)

        text = f"{target.name} heard {initiator.name} out, and the conversation eased some of the distance between them."

    elif option_id == "reassure":
        initiator.trust[target.id] = initiator.trust.get(target.id, 0) + 0.9
        target.trust[initiator.id] = target.trust.get(initiator.id, 0) + 0.4
        world.tension = max(0, world.tension - 0.06)

        text = f"{target.name} reassured {initiator.name}, strengthening the trust between them."

    elif option_id == "challenge":
        initiator.resentment[target.id] = initiator.resentment.get(target.id, 0) + 0.6
        target.resentment[initiator.id] = target.resentment.get(initiator.id, 0) + 0.3
        world.tension += 0.06

        text = f"{target.name} challenged {initiator.name}, and the conversation sharpened the tension between them."

    elif option_id == "dismiss":
        initiator.resentment[target.id] = initiator.resentment.get(target.id, 0) + 0.8
        world.tension += 0.08

        text = f"{target.name} dismissed {initiator.name}, leaving the issue unresolved."

    else:
        return

    log_event(
        world,
        text,
        involved_ids=[initiator.id, target.id],
        event_type="ai_conversation",
        importance=3,
        cause=f"{initiator.name} initiated the conversation",
    )