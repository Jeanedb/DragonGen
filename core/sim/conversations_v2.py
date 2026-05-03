# EXPERIMENTAL ONLY
# Do not import this into the main UI yet.
# Current production conversation system is core/sim/conversations.py.

import random
from core.sim.logging import log_event


def clamp(value, low=-10, high=10):
    return max(low, min(high, value))


def adjust_relationship(a, b, trust=0, resentment=0):
    a.trust[b.id] = clamp(a.trust.get(b.id, 0) + trust)
    b.trust[a.id] = clamp(b.trust.get(a.id, 0) + trust)

    a.resentment[b.id] = clamp(a.resentment.get(b.id, 0) + resentment)
    b.resentment[a.id] = clamp(b.resentment.get(a.id, 0) + resentment)


def start_conversation(world, a, b, topic):
    return {
        "dragon_a_id": a.id,
        "dragon_b_id": b.id,
        "topic": topic,
        "turn": 1,
        "max_turns": 2,
        "tone": topic,
        "history": [],
        "complete": False,
    }


def get_conversation_choices(world, convo):
    topic = convo["topic"]
    turn = convo["turn"]

    if turn == 1:
        if topic == "friendly":
            return [
                {"id": "open_up", "text": "Open up honestly"},
                {"id": "joke", "text": "Keep things light"},
                {"id": "ask_personal", "text": "Ask something personal"},
            ]

        if topic == "tense":
            return [
                {"id": "explain", "text": "Explain your side"},
                {"id": "challenge", "text": "Challenge them directly"},
                {"id": "back_down", "text": "Back down for now"},
            ]

        if topic == "repair":
            return [
                {"id": "apologize", "text": "Apologize sincerely"},
                {"id": "justify", "text": "Explain why it happened"},
                {"id": "blame", "text": "Put the blame back on them"},
            ]

        if topic == "rumor":
            return [
                {"id": "ask_rumor", "text": "Ask what they have heard"},
                {"id": "warn", "text": "Warn them not to spread it"},
                {"id": "spread", "text": "Encourage the rumor"},
            ]

    # second turn / resolution choices
    return [
        {"id": "soften", "text": "Soften your tone"},
        {"id": "press", "text": "Press the issue"},
        {"id": "end", "text": "End the conversation"},
    ]


def apply_conversation_choice(world, convo, choice_id):
    a = next(d for d in world.dragons if d.id == convo["dragon_a_id"])
    b = next(d for d in world.dragons if d.id == convo["dragon_b_id"])

    topic = convo["topic"]
    turn = convo["turn"]

    text = ""

    if turn == 1:
        if topic == "friendly":
            if choice_id == "open_up":
                adjust_relationship(a, b, trust=2)
                text = f"{a.name} speaks honestly, and {b.name} seems to appreciate the trust."
            elif choice_id == "joke":
                adjust_relationship(a, b, trust=1)
                text = f"{a.name} keeps the conversation light. {b.name} relaxes a little."
            elif choice_id == "ask_personal":
                adjust_relationship(a, b, trust=1)
                text = f"{a.name} asks something personal. {b.name} answers carefully."

        elif topic == "tense":
            if choice_id == "explain":
                adjust_relationship(a, b, trust=1, resentment=-1)
                text = f"{a.name} explains their side. The tension does not vanish, but it eases."
            elif choice_id == "challenge":
                adjust_relationship(a, b, resentment=2)
                text = f"{a.name} challenges {b.name} directly. The air between them sharpens."
            elif choice_id == "back_down":
                adjust_relationship(a, b, resentment=-1)
                text = f"{a.name} backs down. It avoids a fight, but leaves things unfinished."

        elif topic == "repair":
            if choice_id == "apologize":
                adjust_relationship(a, b, trust=1, resentment=-2)
                text = f"{a.name} apologizes sincerely. {b.name} does not fully forgive them, but listens."
            elif choice_id == "justify":
                adjust_relationship(a, b, resentment=-1)
                text = f"{a.name} explains why it happened. {b.name} seems uncertain."
            elif choice_id == "blame":
                adjust_relationship(a, b, resentment=2)
                text = f"{a.name} turns the blame back on {b.name}. The conversation worsens."

        elif topic == "rumor":
            if choice_id == "ask_rumor":
                text = f"{a.name} asks what {b.name} has heard. The rumor becomes harder to ignore."
            elif choice_id == "warn":
                adjust_relationship(a, b, trust=1)
                text = f"{a.name} warns {b.name} to be careful with loose talk."
            elif choice_id == "spread":
                adjust_relationship(a, b, resentment=1)
                world.tension += 0.2
                text = f"{a.name} leans into the rumor. The tribe feels a little less stable."

        convo["history"].append((choice_id, text))
        convo["turn"] += 1
        return text

    # Turn 2: resolve
    if choice_id == "soften":
        adjust_relationship(a, b, trust=1, resentment=-1)
        text = f"{a.name} softens their tone. The conversation ends on steadier ground."
    elif choice_id == "press":
        adjust_relationship(a, b, resentment=1)
        text = f"{a.name} presses the issue. {b.name} remembers the pressure."
    else:
        text = f"{a.name} lets the conversation end before it becomes too much."

    convo["history"].append((choice_id, text))
    convo["complete"] = True

    a.memory_flags.append(("conversation", b.id, world.moon))
    b.memory_flags.append(("conversation", a.id, world.moon))

    log_event(
        world,
        f"{a.name} and {b.name} had a {topic} conversation.",
        involved_ids=[a.id, b.id],
        event_type="conversation",
        importance=1,
    )

    return text