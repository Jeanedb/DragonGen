import random
from core.sim.consequences import cancel_scheduled_event
from core.sim.logging import log_event


def get_conversation_type(a, b):
    trust_ab = a.trust.get(b.id, 0)
    trust_ba = b.trust.get(a.id, 0)
    resentment_ab = a.resentment.get(b.id, 0)
    resentment_ba = b.resentment.get(a.id, 0)

    if resentment_ab >= 4 or resentment_ba >= 4:
        return "repair"

    if b.id in a.rivals or a.id in b.rivals or resentment_ab >= 2 or resentment_ba >= 2:
        return "tense"

    if b.id in a.friends or a.id in b.friends or trust_ab >= 2 or trust_ba >= 2:
        return "friendly"

    return "neutral"


def get_personality_line(dragon, mood):
    personality = getattr(dragon, "personality", "Neutral")

    lines = {
        "Kind": {
            "friendly": [
                f'"It’s good to have a quiet moment with you… things have been loud lately, and not in a good way," {dragon.name} said softly.',
                f'"I’ve been meaning to talk to you for a while now… it just never felt like the right moment until this one," {dragon.name} said.',
                f'"It’s strange how much easier things feel when I’m talking to you instead of everyone else," {dragon.name} admitted quietly.',
                f'"I didn’t realize how much I needed this… just a normal conversation without everything weighing on it," {dragon.name} said.',
                f'"I trust you more than I probably should… but I don’t regret that," {dragon.name} said with a small, careful smile.',
                f'"You ever notice how things feel less complicated when it’s just us talking like this?" {dragon.name} asked gently.',
                f'"I don’t say this often, but… I’m glad it’s you I’m talking to right now," {dragon.name} said softly.',
                f'"There’s a lot I don’t understand lately… but talking to you makes it feel like I don’t have to figure it all out alone," {dragon.name} said.',
            ],
            "neutral": [
                f'"Things have felt… heavier than usual lately. I’m still trying to figure out why," {dragon.name} said.',
                f'"I wasn’t sure if this conversation would matter… but it felt wrong not to try," {dragon.name} admitted.',
                f'"There’s been a lot left unsaid between dragons lately… I don’t want that to keep happening," {dragon.name} said.',
                f'"I don’t know where we stand exactly, but I’d rather understand than keep guessing," {dragon.name} said carefully.',
            ],
            "tense": [
                f'"I don’t want this to keep getting worse… even if part of me thinks it already has," {dragon.name} said quietly.',
                f'"We can’t keep pretending this doesn’t matter… because it does, whether we admit it or not," {dragon.name} said.',
                f'"I’m trying to let this go… but it’s harder than I thought it would be," {dragon.name} admitted.',
                f'"Something broke between us, and I don’t know if we’re fixing it or just ignoring it," {dragon.name} said.',
            ]
        },
        "Ambitious": {
            "friendly": [
                f'"If we’re going to keep moving forward, it helps to know who’s actually worth standing beside… you’ve proven that much," {dragon.name} said.',
                f'"Most dragons slow each other down. You don’t… and I respect that," {dragon.name} said evenly.',
                f'"There’s value in having someone who doesn’t waste time pretending… I think that’s why I don’t mind talking to you," {dragon.name} said.',
                f'"We could both go further if we stop working around each other and start working with each other," {dragon.name} said thoughtfully.',
                f'"You ever think about how far we could push things if we actually trusted the right dragons?" {dragon.name} asked.',
                f'"We could be making each other stronger instead of wasting time standing apart," {dragon.name} said.',
                f'"There’s no reason we both can’t come out ahead… if we’re smart about this," {dragon.name} added.',
                f'"I don’t invest time in dragons unless there’s a reason… you’re one of the few worth it," {dragon.name} said.',
                f'"You’ve proven you’re not dead weight… that matters more than most realize," {dragon.name} said evenly.',
            ],
            "neutral": [
                f'"If we understand each other better, that could be useful," {dragon.name} said.',
                f'"There’s value in knowing where we stand," {dragon.name} said.',
                f'"Understanding where we stand has value… even if we don’t like the answer," {dragon.name} said.',
                f'"I prefer clarity over guessing… and right now, things feel unclear," {dragon.name} said.',
                f'"There’s always an angle to a conversation like this… I’m just trying to see it," {dragon.name} said thoughtfully.',
            ],
            "tense": [
                f'"I keep telling myself this isn’t worth holding onto… but it keeps coming back anyway," {dragon.name} said quietly.',
                f'"We both know this didn’t start today… so don’t pretend it ends with this conversation," {dragon.name} said coldly.',
                f'"You can act like things are fine now, but that doesn’t erase what already happened," {dragon.name} said.',
                f'"I’ve replayed that moment more times than I want to admit… and it still doesn’t sit right," {dragon.name} said tightly.',
                f'"Maybe this could’ve gone differently… but it didn’t, and now we’re here," {dragon.name} said.',
                f'"If you have something to say, say it plainly… I don’t deal in half-truths," {dragon.name} said coldly.',
                f'"I’m not interested in pretending this is fine if it isn’t," {dragon.name} said.',
                f'"You either stand with me or against me… I’m done guessing which it is," {dragon.name} said.',
            ]
        },
        "Suspicious": {
            "friendly": [
                f'"I’m still not used to trusting anyone this much," {dragon.name} admitted.',
                f'"Trust doesn’t come easily, but you’ve earned some of mine," {dragon.name} said.',
                f'"I don’t trust easily… but you’ve given me fewer reasons to doubt than most," {dragon.name} admitted.',
                f'"I still question things… but not you, at least not the way I do others," {dragon.name} said.',
                f'"Trust isn’t something I hand out… so don’t take this lightly," {dragon.name} said quietly.',
            ],
            "neutral": [
                f'"I never really know what others are thinking," {dragon.name} said.',
                f'"It’s hard to tell where anyone truly stands," {dragon.name} muttered.',
                f'"It’s hard to tell what anyone really means anymore… words don’t always match actions," {dragon.name} muttered.',
                f'"I’ve learned to pay attention to what’s not being said… that usually matters more," {dragon.name} said.',
            ],
            "tense": [
                f'"You expect me to just forget what happened?" {dragon.name} asked.',
                f'"I haven’t stopped thinking about it," {dragon.name} said coldly.',
                f'"You expect me to just forget what happened? That’s not how this works," {dragon.name} said sharply.',
                f'"I’ve been thinking about it… and the more I do, the less it makes sense," {dragon.name} said coldly.',
            ]
        },
        "Moody": {
            "friendly": [
                f'"Some days I don’t know what I’d do without this," {dragon.name} said.',
                f'"It’s easier to breathe when things are calm between us," {dragon.name} said.',
                f'"Some days feel heavier than others… today’s easier, talking like this," {dragon.name} said.',
                f'"I don’t always know what I’m feeling… but this feels better than most things lately," {dragon.name} admitted.',
            ],
            "neutral": [
                f'"I don’t even know what kind of day this is anymore," {dragon.name} said.',
                f'"Everything feels strange lately," {dragon.name} muttered.',
                f'"I don’t even know what kind of day this is anymore… everything just blurs together," {dragon.name} said.',
                f'"Things feel off… like something shifted and didn’t settle right," {dragon.name} muttered.',
            ],
            "tense": [
                f'"Maybe I’m still angry. Maybe I should be," {dragon.name} said.',
                f'"You always manage to drag this back up," {dragon.name} snapped.',
                f'"Maybe I’m still angry… or maybe I just don’t know how to stop being angry," {dragon.name} said.',
                f'"You always manage to drag this back up… even when I’m trying to move past it," {dragon.name} snapped.',
            ]
        },
        "Loyal": {
            "friendly": [
                f'"Whatever happens, I want you to know I’m with you," {dragon.name} said.',
                f'"Some bonds are worth protecting," {dragon.name} said firmly.',
                f'"Whatever happens, I stand with the dragons I trust… and you’re one of them," {dragon.name} said firmly.',
                f'"Some bonds aren’t convenient… they’re chosen, and that matters more," {dragon.name} said.',
            ],
            "neutral": [
                f'"I think dragons should say what they mean more often," {dragon.name} said.',
                f'"It matters to me where we stand," {dragon.name} said.',
                f'"I think dragons should say what they mean more often… loyalty doesn’t work without honesty," {dragon.name} said.',
                f'"It matters to me where we stand… I don’t like uncertainty between allies," {dragon.name} said.',
            ],
            "tense": [
                f'"Loyalty means something to me. That’s why this still stings," {dragon.name} said.',
                f'"I don’t forget when trust is broken," {dragon.name} said.',
                f'"Loyalty means something to me… that’s why this still matters," {dragon.name} said.',
                f'"I don’t forget when trust is broken… even if I want to," {dragon.name} said.',
            ]
        },
        "Clever": {
                "friendly": [
                    f'"It’s strange how much easier things are when two dragons actually understand each other," {dragon.name} said.',
                       f'"Talking plainly solves more than most dragons realize," {dragon.name} said.',
                    f'"It’s interesting how much simpler things become when two dragons actually understand each other," {dragon.name} said.',
                    f'"Most problems aren’t as complicated as they look… just poorly communicated," {dragon.name} added.',
                ],
                "neutral": [
                    f'"There’s usually more going on beneath the surface," {dragon.name} observed.',
                    f'"Misunderstandings tend to grow when nobody speaks first," {dragon.name} said.',
                    f'"There’s usually more going on beneath the surface… there always is," {dragon.name} observed.',
                    f'"Misunderstandings grow fastest when nobody says anything first," {dragon.name} said.',
                 ],
             "tense": [
                    f'"We both know this didn’t start today," {dragon.name} said.',
                    f'"Pretending nothing happened would be the stupidest option," {dragon.name} said.',
                    f'"We both know this didn’t start today… so let’s not pretend it ends here," {dragon.name} said.',
                    f'"Ignoring the problem would be convenient… but also incredibly stupid," {dragon.name} said bluntly.',
             ]


}
    }

    if personality in lines and mood in lines[personality]:
        return random.choice(lines[personality][mood])



    fallback = {
        "friendly": [
            f'"It’s good to talk like this," {dragon.name} said.',
            f'"Things feel easier when we speak honestly," {dragon.name} said.'
        ],
        "neutral": [
            f'"We don’t talk enough," {dragon.name} said.',
            f'"I’ve been meaning to say something for a while," {dragon.name} said.'
        ],
        "tense": [
            f'"There’s still something between us," {dragon.name} said.',
            f'"We can’t keep pretending everything is fine," {dragon.name} said.'
        ]
    }

    return random.choice(fallback[mood])


def build_conversation(world, a, b):
    convo_type = get_conversation_type(a, b)

    if convo_type == "repair":
        options = [
            {"id": "apologize", "text": f"{a.name} apologizes and tries to repair the damage"},
            {"id": "explain", "text": f"{a.name} explains what happened and asks to be heard"},
            {"id": "accuse", "text": f"{a.name} confronts {b.name} and demands honesty"},
        ]

        text = (
            f'"This has been sitting between us for too long," {a.name} said.\n\n'
            f'"Then say what you came here to say," {b.name} replied.\n\n'
            "The conversation felt fragile, like one wrong word could make things worse."
        )

        return {
            "type": convo_type,
            "text": text,
            "options": options,
        }

    memory_override = None

    for memory in a.memory_flags:
        if len(memory) >= 2:
            flag, other_id = memory[0], memory[1]

            if other_id == b.id:
                if flag == "abandoned_by":
                    memory_override = "abandonment"
                elif flag == "saved_by":
                    memory_override = "gratitude"

    if memory_override is None:
        if b.id in a.rivals or a.id in b.rivals:
            memory_override = "rivalry"
        elif (
            (b.id in a.friends or a.id in b.friends)
            and (a.trust.get(b.id, 0) >= 3 or b.trust.get(a.id, 0) >= 3)
        ):
            memory_override = "bond"

    if memory_override == "abandonment":
        line1 = f'"You left me out there," {a.name} said quietly.'
        line2 = random.choice([
            f'"I didn’t have a choice," {b.name} replied.',
            f'"You don’t understand what happened," {b.name} said.',
            f'"I’ve thought about that moment more than you think," {b.name} answered.'
        ])

    elif memory_override == "gratitude":
        line1 = f'"I haven’t forgotten what you did for me," {a.name} said.'
        line2 = random.choice([
            f'"You would’ve done the same," {b.name} replied.',
            f'"You don’t owe me anything," {b.name} said.',
            f'"That’s what we’re supposed to do," {b.name} answered.'
        ])

    elif memory_override == "rivalry":
        line1 = f'"You and I were never going to make this easy," {a.name} said.'
        line2 = random.choice([
            f'"Then stop pretending otherwise," {b.name} replied.',
            f'"At least we’re finally being honest about it," {b.name} said.',
            f'"Some dragons are never meant to agree," {b.name} answered.'
        ])

    elif memory_override == "bond":
        a_personality = getattr(a, "personality", "Neutral")
        b_personality = getattr(b, "personality", "Neutral")

        bond_openers = {
            "Kind": [
                f'"I feel safer when things are good between us," {a.name} said softly.',
                f'"You matter to me more than I usually know how to say," {a.name} admitted.'
            ],
            "Loyal": [
                f'"I trust you more than most, and I don’t say that lightly," {a.name} said firmly.',
                f'"Some bonds are worth standing by no matter what," {a.name} said.'
            ],
            "Moody": [
                f'"I don’t always know how to say it, but I trust you," {a.name} said quietly.',
                f'"Some days you’re the only dragon I don’t want to push away," {a.name} admitted.'
            ],
            "Suspicious": [
                f'"Trust does not come easily to me, but you’ve earned it," {a.name} said.',
                f'"I still doubt most dragons. Not you," {a.name} said carefully.'
            ],
            "Ambitious": [
                f'"I trust you more than most because you’ve proven your worth," {a.name} said.',
                f'"You’re one of the few dragons I’d actually choose beside me," {a.name} said.'
            ],
            "Clever": [
                f'"Trust is rare enough that I notice when it’s real," {a.name} said.',
                f'"I’ve thought about it, and I trust you more than most," {a.name} said.'
            ],
        }

        bond_replies = {
            "Kind": [
                f'"That means more to me than you know," {b.name} replied gently.',
                f'"I’m glad you said it," {b.name} said warmly.'
            ],
            "Loyal": [
                f'"That trust goes both ways," {b.name} replied at once.',
                f'"Then I’ll do my best not to fail it," {b.name} said firmly.'
            ],
            "Moody": [
                f'"...I’m glad it’s still there," {b.name} said after a pause.',
                f'"I don’t always make this easy, but that matters to me," {b.name} replied.'
            ],
            "Suspicious": [
                f'"I don’t give trust lightly either," {b.name} replied.',
                f'"Then I’ll remember that," {b.name} said carefully.'
            ],
            "Ambitious": [
                f'"Good. Trust is worth more when it’s earned," {b.name} replied.',
                f'"Then let’s make sure that trust remains deserved," {b.name} said.'
            ],
            "Clever": [
                f'"That kind of trust is hard to build. Harder to keep," {b.name} replied.',
                f'"Then we should be careful with it," {b.name} said.'
            ],
        }

        default_openers = [
            f'"I trust you more than most," {a.name} said.',
            f'"There aren’t many dragons I’d say this to, but I trust you," {a.name} said.'
        ]

        default_replies = [
            f'"That trust goes both ways," {b.name} replied.',
            f'"I won’t forget that," {b.name} said firmly.',
            f'"Then I’ll do my best not to fail it," {b.name} answered.'
        ]

        line1 = random.choice(bond_openers.get(a_personality, default_openers))
        line2 = random.choice(bond_replies.get(b_personality, default_replies))

    else:
        line1 = get_personality_line(a, convo_type)


        if convo_type == "friendly":
            line2_options = [
                f'"Maybe that’s why I don’t mind talking with you," {b.name} replied.',
                f'"I feel the same," {b.name} said after a pause.',
                f'"It’s easier when I know I’m being heard," {b.name} said.',
                f'"I was thinking the same thing… just didn’t know how to say it," {b.name} replied quietly.',
                f'"It’s easier when I know I’m not the only one feeling it," {b.name} said.',
                f'"Yeah… this feels different from most conversations," {b.name} admitted.',
            ]
        elif convo_type == "tense":
            line2_options = [
                f'"That doesn’t erase what happened," {b.name} replied.',
                f'"You say that now, but I still remember," {b.name} said.',
                f'"Some things don’t fade just because we’re speaking calmly," {b.name} answered.',
                f'"That doesn’t erase what happened… it just puts words around it," {b.name} said.',
                f'"You say that now, but I remember things differently," {b.name} replied coldly.',
                f'"Some things don’t settle just because we’re talking about them," {b.name} said.',
            ]
        else:
            line2_options = [
                f'"Maybe talking now is better than waiting longer," {b.name} replied.',
                f'"I wasn’t sure if this conversation would ever happen," {b.name} said.',
                f'"At least we’re saying something now," {b.name} said.',
                f'"Maybe this matters more than either of us expected," {b.name} said.',
                f'"At least we’re not avoiding it anymore," {b.name} replied.',
                f'"It’s a start… even if it’s not much yet," {b.name} said.',
            ]

        line2 = random.choice(line2_options)

    if convo_type == "friendly":
        options = [
            {"id": "open_up", "text": f"{a.name} shares something more personal"},
            {"id": "stay_guarded", "text": f"{a.name} keeps things light"},
            {"id": "push_issue", "text": f"{a.name} brings up something uncomfortable"},
        ]

    elif convo_type == "tense":
        options = [
            {"id": "open_up", "text": f"{a.name} tries to explain honestly"},
            {"id": "stay_guarded", "text": f"{a.name} avoids saying too much"},
            {"id": "push_issue", "text": f"{a.name} confronts {b.name} directly"},
        ]
 
    else:  # neutral
        options = [
            {"id": "open_up", "text": f"{a.name} opens up a little"},
            {"id": "stay_guarded", "text": f"{a.name} keeps things surface-level"},
            {"id": "push_issue", "text": f"{a.name} shifts the conversation toward tension"},
        ]

    if convo_type == "friendly":
        line3_options = [
            f'The moment felt steady, like something had settled between them.',
            f'The tension that once lingered seemed quieter now.',
        ]
    elif convo_type == "tense":
        line3_options = [
            f'The air between them tightened, heavy with what wasn’t said.',
            f'Neither dragon looked away, but neither relaxed either.',
        ]
    else:
        line3_options = [
            f'The moment passed quietly, leaving more unsaid than resolved.',
            f'It wasn’t much, but it was something.',
        ]

    line3 = random.choice(line3_options)

    text = f"{line1}\n\n{line2}\n\n{line3}"

    return {
        "type": convo_type,
        "text": text,
        "options": options,
    }

def get_personality_conversation_modifiers(dragon):
    personality = getattr(dragon, "personality", "Neutral")

    modifiers = {
        "open_up_bonus": 0,
        "guarded_bonus": 0,
        "push_bonus": 0,
        "trust_bonus": 0,
        "resentment_bonus": 0,
    }

    if personality == "Kind":
        modifiers["open_up_bonus"] += 1
        modifiers["trust_bonus"] += 1

    elif personality == "Loyal":
        modifiers["open_up_bonus"] += 1
        modifiers["trust_bonus"] += 1

    elif personality == "Suspicious":
        modifiers["guarded_bonus"] += 1

    elif personality == "Ambitious":
        modifiers["push_bonus"] += 1
        modifiers["resentment_bonus"] += 1

    elif personality == "Moody":
        modifiers["push_bonus"] += 1
        modifiers["resentment_bonus"] += 1

    elif personality == "Clever":
        modifiers["guarded_bonus"] += 1

    return modifiers


def get_player_response_line(a, b, convo_type, option_id):
    personality = getattr(a, "personality", "Neutral")

    lines = {
        "friendly": {
            "open_up": {
                "Kind": [
                    f'"I don’t say things like this easily, but I’m glad we have this," {a.name} said.',
                    f'"You matter to me more than I usually know how to explain," {a.name} admitted.'
                ],
                "Loyal": [
                    f'"I trust you, and I mean that," {a.name} said firmly.',
                    f'"If I’m opening up, it’s because I believe you’ve earned it," {a.name} said.'
                ],
                "Moody": [
                    f'"I’m not always good at saying this, but… I’m glad you’re here," {a.name} said.',
                    f'"I don’t always understand my own head, but I know this matters to me," {a.name} admitted.'
                ],
                "Suspicious": [
                    f'"I don’t lower my guard for many dragons, but I am now," {a.name} said carefully.',
                    f'"I’m trusting you with more than I usually would," {a.name} said.'
                ],
                "Ambitious": [
                    f'"I don’t waste honesty on dragons who don’t matter," {a.name} said.',
                    f'"If I’m saying this plainly, it’s because I think it’s worth saying," {a.name} said.'
                ],
                "Clever": [
                    f'"I’ve thought about this more than once, and I’d rather say it honestly," {a.name} said.',
                    f'"There’s no point pretending this doesn’t matter to me," {a.name} said.'
                ],
                "Neutral": [
                    f'"I’m glad we’re talking honestly," {a.name} said.',
                    f'"I’d rather say it clearly than leave it unspoken," {a.name} said.'
                ],
            },
            "stay_guarded": {
                "Kind": [
                    f'"I’m not ready to say everything, but I didn’t want to stay silent either," {a.name} said.',
                ],
                "Loyal": [
                    f'"There are some things I’ll keep to myself for now, but that doesn’t mean they don’t matter," {a.name} said.',
                ],
                "Moody": [
                    f'"I don’t really know how to say what I mean right now," {a.name} muttered.',
                ],
                "Suspicious": [
                    f'"I’m not saying more than I have to," {a.name} said carefully.',
                ],
                "Ambitious": [
                    f'"Not everything needs to be said aloud," {a.name} said evenly.',
                ],
                "Clever": [
                    f'"I’d rather be careful with my words than regret them later," {a.name} said.',
                ],
                "Neutral": [
                    f'"Maybe I’ll leave it there for now," {a.name} said.',
                ],
            },
            "push_issue": {
                "Kind": [
                    f'"I’m trying to be honest, but I can’t just ignore what’s bothering me," {a.name} said.',
                ],
                "Loyal": [
                    f'"If something matters, then pretending otherwise helps no one," {a.name} said.',
                ],
                "Moody": [
                    f'"No. I’m not letting this slide past again," {a.name} snapped.',
                ],
                "Suspicious": [
                    f'"I’m not going to pretend this doesn’t raise questions," {a.name} said sharply.',
                ],
                "Ambitious": [
                    f'"Then let’s stop circling around it and say what this really is," {a.name} said.',
                ],
                "Clever": [
                    f'"Then let’s stop dressing it up and deal with the real problem," {a.name} said.',
                ],
                "Neutral": [
                    f'"There’s something here that shouldn’t just be brushed aside," {a.name} said.',
                ],
            },
        },

        "tense": {
            "open_up": {
                "Kind": [
                    f'"I’m not asking you to forget it. I’m asking you to hear me," {a.name} said quietly.',
                    f'"I know things are damaged between us, but I don’t want to keep making them worse," {a.name} said.'
                ],
                "Loyal": [
                    f'"I still think broken trust can be mended, if both dragons mean it," {a.name} said.',
                    f'"I’m being honest because I think this is still worth trying to save," {a.name} said.'
                ],
                "Moody": [
                    f'"I’m trying to say this without turning it into another fight," {a.name} muttered.',
                    f'"I’m angry, but that’s not the only thing I feel," {a.name} said.'
                ],
                "Suspicious": [
                    f'"I’m saying more than I usually would, so don’t waste that," {a.name} said carefully.',
                    f'"I still have doubts, but I’m trying to be honest anyway," {a.name} said.'
                ],
                "Ambitious": [
                    f'"This doesn’t get fixed by avoiding it. So I’m saying it plainly," {a.name} said.',
                    f'"I’d rather deal with this honestly than keep dragging it around," {a.name} said.'
                ],
                "Clever": [
                    f'"Pretending this is simple would be a lie, so I’ll just be direct," {a.name} said.',
                    f'"I think honesty gives us better odds than silence does," {a.name} said.'
                ],
                "Neutral": [
                    f'"I’d rather tell the truth than keep feeding the distance between us," {a.name} said.',
                    f'"I’m trying to be honest, even if it comes late," {a.name} said.'
                ],
            },
            "stay_guarded": {
                "Kind": [
                    f'"I don’t want to make this worse by saying the wrong thing," {a.name} said softly.',
                ],
                "Loyal": [
                    f'"I’m holding my tongue because I’d rather not damage this further," {a.name} said.',
                ],
                "Moody": [
                    f'"I’m not in the mood to spill everything just to regret it after," {a.name} muttered.',
                ],
                "Suspicious": [
                    f'"I’m not giving you more than I have to right now," {a.name} said coldly.',
                ],
                "Ambitious": [
                    f'"Saying less is smarter than saying too much," {a.name} said.',
                ],
                "Clever": [
                    f'"I’d rather choose my words carefully than hand you the wrong one," {a.name} said.',
                ],
                "Neutral": [
                    f'"I’m not sure saying more would help right now," {a.name} said.',
                ],
            },
            "push_issue": {
                "Kind": [
                    f'"I’ve tried being patient, but I’m not going to pretend this doesn’t hurt," {a.name} said.',
                ],
                "Loyal": [
                    f'"You don’t get to talk about trust like it means nothing," {a.name} said firmly.',
                ],
                "Moody": [
                    f'"No. I’m done swallowing this just to keep things quiet," {a.name} snapped.',
                ],
                "Suspicious": [
                    f'"You expect me to accept that explanation? Not a chance," {a.name} said sharply.',
                ],
                "Ambitious": [
                    f'"Then stop dodging and answer me plainly," {a.name} said coldly.',
                ],
                "Clever": [
                    f'"Then let’s stop pretending and drag the real issue into the light," {a.name} said.',
                ],
                "Neutral": [
                    f'"No. I’m not letting this pass without saying what it is," {a.name} said.',
                ],
            },
        },

        "neutral": {
            "open_up": {
                "Kind": [
                    f'"I thought it might be better to say something honest for once," {a.name} said.',
                ],
                "Loyal": [
                    f'"I’d rather know where we stand than keep guessing," {a.name} said.',
                ],
                "Moody": [
                    f'"I’m not even sure why I’m saying this, but I think I need to," {a.name} admitted.',
                ],
                "Suspicious": [
                    f'"I’m saying more than I usually would, so take that for what it is," {a.name} said.',
                ],
                "Ambitious": [
                    f'"If we’re speaking, we might as well speak honestly," {a.name} said.',
                ],
                "Clever": [
                    f'"This seemed more useful than leaving everything unspoken," {a.name} said.',
                ],
                "Neutral": [
                    f'"I thought honesty might be the better path here," {a.name} said.',
                ],
            },
            "stay_guarded": {
                "Kind": [
                    f'"Maybe it’s enough just to talk, even if I don’t say everything," {a.name} said softly.',
                ],
                "Loyal": [
                    f'"I’ll leave some things unsaid for now," {a.name} said.',
                ],
                "Moody": [
                    f'"I don’t think I have the words for more than this right now," {a.name} muttered.',
                ],
                "Suspicious": [
                    f'"I’d rather keep a little distance for now," {a.name} said carefully.',
                ],
                "Ambitious": [
                    f'"Not every thought needs to be offered up," {a.name} said evenly.',
                ],
                "Clever": [
                    f'"A measured answer is usually the safer one," {a.name} said.',
                ],
                "Neutral": [
                    f'"I think I’ll leave it there for now," {a.name} said.',
                ],
            },
            "push_issue": {
                "Kind": [
                    f'"I know this may sour the moment, but I can’t ignore it either," {a.name} said.',
                ],
                "Loyal": [
                    f'"If something matters, then it deserves to be said clearly," {a.name} said.',
                ],
                "Moody": [
                    f'"I wasn’t going to bring it up, but I can’t seem to let it rest," {a.name} said.',
                ],
                "Suspicious": [
                    f'"There’s still something about this that doesn’t sit right with me," {a.name} said.',
                ],
                "Ambitious": [
                    f'"Then let’s stop circling around it and say what’s actually wrong," {a.name} said.',
                ],
                "Clever": [
                    f'"We might as well address the tension instead of pretending it isn’t there," {a.name} said.',
                ],
                "Neutral": [
                    f'"There’s something underneath this that I don’t want to ignore," {a.name} said.',
                ],
            },
        },
    }

    mood_block = lines.get(convo_type, {})
    option_block = mood_block.get(option_id, {})
    choices = option_block.get(personality, option_block.get("Neutral", [f'"..." {a.name} said.']))

    return random.choice(choices)


def get_personality_reply_line(b, convo_type, option_id):
    personality = getattr(b, "personality", "Neutral")

    replies = {
        "friendly": {
            "open_up": {
                "Kind": [
                    f'"That means a lot to hear," {b.name} said warmly.',
                    f'"I’m really glad you told me that," {b.name} said softly.'
                ],
                "Loyal": [
                    f'"Then I’ll stand by that trust," {b.name} said firmly.',
                    f'"You won’t regret trusting me," {b.name} replied.'
                ],
                "Moody": [
                    f'"...I didn’t expect that, but I’m glad you said it," {b.name} said.',
                ],
                "Suspicious": [
                    f'"I’ll remember that," {b.name} said carefully.',
                ],
                "Ambitious": [
                    f'"Good. Honesty has its uses," {b.name} said.',
                ],
                "Clever": [
                    f'"That clears more than you might think," {b.name} said.',
                ],
                "Neutral": [
                    f'"I’m glad you said that," {b.name} replied.',
                ],
            },

            "stay_guarded": {
                "Kind": [
                    f'"That’s alright. You don’t have to say everything," {b.name} said gently.',
                ],
                "Loyal": [
                    f'"I’ll take what you’re willing to give," {b.name} said.',
                ],
                "Moody": [
                    f'"Yeah… I get that," {b.name} muttered.',
                ],
                "Suspicious": [
                    f'"Keeping things close isn’t always a bad move," {b.name} said.',
                ],
                "Ambitious": [
                    f'"Not everything needs to be said out loud," {b.name} said.',
                ],
                "Clever": [
                    f'"Measured words are usually better ones," {b.name} said.',
                ],
                "Neutral": [
                    f'"Fair enough," {b.name} said.',
                ],
            },

            "push_issue": {
                "Kind": [
                    f'"I didn’t think this needed to turn into that," {b.name} said sadly.',
                ],
                "Loyal": [
                    f'"There’s a better way to handle this," {b.name} said firmly.',
                ],
                "Moody": [
                    f'"There it is… I knew it would turn like this," {b.name} snapped.',
                ],
                "Suspicious": [
                    f'"So that’s what this really is about," {b.name} said coldly.',
                ],
                "Ambitious": [
                    f'"If that’s the direction you want, then fine," {b.name} said sharply.',
                ],
                "Clever": [
                    f'"You just made this more complicated than it needed to be," {b.name} said.',
                ],
                "Neutral": [
                    f'"That wasn’t necessary," {b.name} said.',
                ],
            },
        },

        "tense": {
            "open_up": {
                "Kind": [
                    f'"...I didn’t expect that from you," {b.name} said quietly.',
                ],
                "Loyal": [
                    f'"Then I’ll meet you halfway," {b.name} said firmly.',
                ],
                "Moody": [
                    f'"That… actually matters more than I thought it would," {b.name} said.',
                ],
                "Suspicious": [
                    f'"I’ll consider what you’ve said," {b.name} replied cautiously.',
                ],
                "Ambitious": [
                    f'"Honesty is a better approach than avoidance," {b.name} said.',
                ],
                "Clever": [
                    f'"That gives me something to work with," {b.name} said.',
                ],
                "Neutral": [
                    f'"That helps… a little," {b.name} said.',
                ],
            },

            "stay_guarded": {
                "Kind": [
                    f'"I wish you’d say more, but I understand," {b.name} said.',
                ],
                "Loyal": [
                    f'"Holding back won’t fix this," {b.name} said.',
                ],
                "Moody": [
                    f'"Of course you’re holding back," {b.name} muttered.',
                ],
                "Suspicious": [
                    f'"Still keeping things hidden," {b.name} said coldly.',
                ],
                "Ambitious": [
                    f'"That doesn’t move us forward," {b.name} said.',
                ],
                "Clever": [
                    f'"Avoidance rarely solves anything," {b.name} said.',
                ],
                "Neutral": [
                    f'"Then I suppose that’s all for now," {b.name} said.',
                ],
            },

            "push_issue": {
                "Kind": [
                    f'"I didn’t want it to go this way," {b.name} said quietly.',
                ],
                "Loyal": [
                    f'"Then let’s not pretend this is nothing," {b.name} said firmly.',
                ],
                "Moody": [
                    f'"Fine. If that’s how you want this to go," {b.name} snapped.',
                ],
                "Suspicious": [
                    f'"I knew you’d push this sooner or later," {b.name} said.',
                ],
                "Ambitious": [
                    f'"Then we deal with it directly," {b.name} said coldly.',
                ],
                "Clever": [
                    f'"So we’ve reached the real issue at last," {b.name} said.',
                ],
                "Neutral": [
                    f'"That just made things worse," {b.name} said.',
                ],
            },
        },

        "neutral": {
            "open_up": {
                "Kind": [
                    f'"That was… good to hear," {b.name} said gently.',
                ],
                "Loyal": [
                    f'"I respect that honesty," {b.name} said.',
                ],
                "Moody": [
                    f'"Didn’t expect that… but alright," {b.name} said.',
                ],
                "Suspicious": [
                    f'"I’ll keep that in mind," {b.name} said.',
                ],
                "Ambitious": [
                    f'"Useful to know," {b.name} said.',
                ],
                "Clever": [
                    f'"That clarifies things somewhat," {b.name} said.',
                ],
                "Neutral": [
                    f'"That makes sense," {b.name} said.',
                ],
            },

            "stay_guarded": {
                "Kind": [
                    f'"That’s alright," {b.name} said softly.',
                ],
                "Loyal": [
                    f'"Fair enough," {b.name} said.',
                ],
                "Moody": [
                    f'"Yeah… okay," {b.name} said.',
                ],
                "Suspicious": [
                    f'"Expected as much," {b.name} said.',
                ],
                "Ambitious": [
                    f'"Noted," {b.name} said.',
                ],
                "Clever": [
                    f'"That tracks," {b.name} said.',
                ],
                "Neutral": [
                    f'"Alright," {b.name} said.',
                ],
            },

            "push_issue": {
                "Kind": [
                    f'"That feels harsher than it needed to be," {b.name} said.',
                ],
                "Loyal": [
                    f'"Then let’s not ignore it," {b.name} said.',
                ],
                "Moody": [
                    f'"Here we go…" {b.name} muttered.',
                ],
                "Suspicious": [
                    f'"That’s exactly what I was waiting for," {b.name} said.',
                ],
                "Ambitious": [
                    f'"Then let’s deal with it properly," {b.name} said.',
                ],
                "Clever": [
                    f'"That escalated things," {b.name} said.',
                ],
                "Neutral": [
                    f'"That changed the tone quickly," {b.name} said.',
                ],
            },
        },
    }

    mood_block = replies.get(convo_type, {})
    option_block = mood_block.get(option_id, {})
    choices = option_block.get(personality, option_block.get("Neutral", [f'"..." {b.name} said.']))

    return random.choice(choices)


def apply_conversation_choice(world, a, b, convo_type, option_id):
    result_text = ""
    player_line = get_player_response_line(a, b, convo_type, option_id)
    reply_line = ""

    a_mod = get_personality_conversation_modifiers(a)
    b_mod = get_personality_conversation_modifiers(b)

    both_adult_eligible = (a.role != "Dragonet" and b.role != "Dragonet")

    if convo_type == "repair":
        if option_id == "apologize":
            a.trust[b.id] = a.trust.get(b.id, 0) + 1
            b.trust[a.id] = b.trust.get(a.id, 0) + 1

            if a.id in b.resentment:
                b.resentment[a.id] = max(0, b.resentment[a.id] - 2)
            if b.id in a.resentment:
                a.resentment[b.id] = max(0, a.resentment[b.id] - 1)

            a.reputation["kind"] = a.reputation.get("kind", 0) + 1
            a.reputation["reliable"] = a.reputation.get("reliable", 0) + 1

            result_text = f"{a.name}'s apology softened some of the resentment between them."

        elif option_id == "explain":
            if b.id in a.resentment:
                a.resentment[b.id] = max(0, a.resentment[b.id] - 1)
            if a.id in b.resentment:
                b.resentment[a.id] = max(0, b.resentment[a.id] - 1)

            a.reputation["reliable"] = a.reputation.get("reliable", 0) + 1

            result_text = f"The explanation did not fix everything, but it made the wound less raw."

        elif option_id == "accuse":
            a.resentment[b.id] = a.resentment.get(b.id, 0) + 1
            b.resentment[a.id] = b.resentment.get(a.id, 0) + 2

            a.reputation["harsh"] = a.reputation.get("harsh", 0) + 1
            a.reputation["unpredictable"] = a.reputation.get("unpredictable", 0) + 1

            result_text = f"The accusation made things worse. Whatever trust remained between them was damaged."

        else:
            result_text = "The conversation ended without changing much."

        log_event(
            world,
            result_text,
            involved_ids=[a.id, b.id],
            event_type="repair_conversation",
            importance=4
        )

        if option_id == "apologize":
            openers = [
                f"{a.name} lowered their voice and tried to make things right.",
                f"{a.name} approached carefully, clearly trying to repair the damage.",
                f"{a.name} chose humility over pride in that moment.",
            ]

            replies = [
                f"{b.name} listened, some of the tension easing.",
                f"{b.name} hesitated, but did not shut them out.",
                f"{b.name} remained guarded, but less hostile than before.",
            ]

        elif option_id == "explain":
            openers = [
                f"{a.name} tried to explain their side of things.",
                f"{a.name} spoke carefully, choosing words with intent.",
                f"{a.name} laid out what had happened, hoping to be understood.",
            ]

            replies = [
                f"{b.name} listened, though uncertainty remained.",
                f"{b.name} considered the explanation, but did not fully relax.",
                f"{b.name} heard them out, even if doubts lingered.",
            ]

        elif option_id == "accuse":
            openers = [
                f"{a.name} stepped forward sharply, unwilling to hold back.",
                f"{a.name} let the frustration show without restraint.",
                f"{a.name} pushed the issue directly, refusing to soften it.",
            ]

            replies = [
                f"{b.name}'s expression hardened immediately.",
                f"{b.name} did not take it well.",
                f"{b.name} tensed, clearly reacting to the accusation.",
            ]

        else:
            openers = [
                f"{a.name} chose to address the tension directly.",
            ]

            replies = [
                f"{b.name} listened, though not easily.",
            ]

        success_chance = 0.0

        if option_id == "apologize":
            success_chance = 0.75
        elif option_id == "explain":
            success_chance = 0.5

        # modify by current resentment
        resentment = a.resentment.get(b.id, 0)

        if resentment >= 6:
            success_chance -= 0.2
        elif resentment <= 2:
            success_chance += 0.1

        success_chance += a.reputation.get("kind", 0) * 0.02
        success_chance += a.reputation.get("reliable", 0) * 0.01
        success_chance -= a.reputation.get("harsh", 0) * 0.02
        success_chance -= a.reputation.get("unpredictable", 0) * 0.01

        success_chance = max(0.05, min(0.95, success_chance))

        if random.random() < success_chance:
            cancel_scheduled_event(world, "possible_defection", a.id)

            log_event(
                world,
                f"The conversation seems to have prevented {a.name} from leaving the tribe.",
                involved_ids=[a.id, b.id],
                event_type="repair_success",
                importance=5
            )

            from core.sim.rumors import spread_rumor

            spread_rumor(world, a.id, a.id, effect=0.3)
        else:
            log_event(
                world,
                f"The conversation helped, but something still feels unresolved with {a.name}.",
                involved_ids=[a.id, b.id],
                event_type="repair_partial",
                importance=3
            )

        return (
            random.choice(openers),
            random.choice(replies),
            result_text
        )

        

    if convo_type == "friendly":
        if option_id == "open_up":
            a_gain = 2 + a_mod["open_up_bonus"] + a_mod["trust_bonus"]
            b_gain = 2 + b_mod["trust_bonus"]

            a.trust[b.id] = a.trust.get(b.id, 0) + a_gain
            b.trust[a.id] = b.trust.get(a.id, 0) + b_gain

            # reputation influence
            a.trust[b.id] += a.reputation.get("kind", 0) * 0.1
            a.trust[b.id] -= a.reputation.get("harsh", 0) * 0.1

            # perceived reputation influence (NEW)
            perception = b.perceived_reputation.get(a.id, 0)
            a.trust[b.id] += perception * 0.1

            if both_adult_eligible:
                if b.id not in a.friends:
                    a.friends.append(b.id)
                if a.id not in b.friends:
                    b.friends.append(a.id)

            reply_line = get_personality_reply_line(b, convo_type, option_id)
            
            result_text = f"{a.name} spoke openly, and the conversation left both dragons feeling closer."

        elif option_id == "stay_guarded":
            a_gain = 1 + a_mod["guarded_bonus"]
            b_gain = 1 + b_mod["guarded_bonus"]

            a.trust[b.id] = a.trust.get(b.id, 0) + a_gain
            b.trust[a.id] = b.trust.get(a.id, 0) + b_gain


            reply_line = get_personality_reply_line(b, convo_type, option_id)
            
            result_text = f"{a.name} kept some distance, but the conversation remained calm."

        elif option_id == "push_issue":
            a_loss = 1 + a_mod["push_bonus"] + a_mod["resentment_bonus"]
            b_loss = 1 + b_mod["resentment_bonus"]

            a.resentment[b.id] = a.resentment.get(b.id, 0) + a_loss
            b.resentment[a.id] = b.resentment.get(a.id, 0) + b_loss

            from core.sim.consequences import schedule_consequence

            if a.resentment.get(b.id, 0) >= 4:
                schedule_consequence(world, delay=3, data={
                    "type": "possible_defection",
                    "dragon_id": a.id,
                    "caused_by": b.id
                })

            reply_line = get_personality_reply_line(b, convo_type, option_id)
            
            result_text = f"{a.name} pushed the conversation too hard, souring what had begun as a peaceful exchange."

    elif convo_type == "tense":
        if option_id == "open_up":
            a_gain = 1 + a_mod["open_up_bonus"] + a_mod["trust_bonus"]
            b_gain = 1 + b_mod["trust_bonus"]

            a.trust[b.id] = a.trust.get(b.id, 0) + a_gain
            b.trust[a.id] = b.trust.get(a.id, 0) + b_gain

            # reputation influence
            a.trust[b.id] += a.reputation.get("kind", 0) * 0.1
            a.trust[b.id] -= a.reputation.get("harsh", 0) * 0.1

            # perceived reputation influence (NEW)
            perception = b.perceived_reputation.get(a.id, 0)
            a.trust[b.id] += perception * 0.1

            a.resentment[b.id] = max(0, a.resentment.get(b.id, 0) - 1)
            b.resentment[a.id] = max(0, b.resentment.get(a.id, 0) - 1)

            reply_line = get_personality_reply_line(b, convo_type, option_id)
            
            result_text = f"{a.name} tried honesty instead of anger, and some of the tension between them eased."

        elif option_id == "stay_guarded":
            a_gain = a_mod["guarded_bonus"]
            b_gain = b_mod["guarded_bonus"]

            if a_gain > 0:
                a.trust[b.id] = a.trust.get(b.id, 0) + a_gain
            if b_gain > 0:
                b.trust[a.id] = b.trust.get(a.id, 0) + b_gain

            reply_line = get_personality_reply_line(b, convo_type, option_id)
            
            result_text = f"The conversation remained careful and restrained. Neither dragon gave much away."

        elif option_id == "push_issue":
            a_loss = 2 + a_mod["push_bonus"] + a_mod["resentment_bonus"]
            b_loss = 2 + b_mod["resentment_bonus"]

            a.resentment[b.id] = a.resentment.get(b.id, 0) + a_loss
            b.resentment[a.id] = b.resentment.get(a.id, 0) + b_loss

            from core.sim.consequences import schedule_consequence

            if a.resentment.get(b.id, 0) >= 4:
                schedule_consequence(world, delay=3, data={
                    "type": "possible_defection",
                    "dragon_id": a.id,
                    "caused_by": b.id
                })

            if both_adult_eligible:
                if b.id not in a.rivals:
                    a.rivals.append(b.id)
                if a.id not in b.rivals:
                    b.rivals.append(a.id)

            reply_line = get_personality_reply_line(b, convo_type, option_id)
            
            result_text = f"{a.name} pressed the issue, and the conversation hardened into open bitterness."

    else:  # neutral
        if option_id == "open_up":
            a_gain = 1 + a_mod["open_up_bonus"] + a_mod["trust_bonus"]
            b_gain = 1 + b_mod["trust_bonus"]

            a.trust[b.id] = a.trust.get(b.id, 0) + a_gain
            b.trust[a.id] = b.trust.get(a.id, 0) + b_gain

            # reputation influence
            a.trust[b.id] += a.reputation.get("kind", 0) * 0.1
            a.trust[b.id] -= a.reputation.get("harsh", 0) * 0.1

            # perceived reputation influence (NEW)
            perception = b.perceived_reputation.get(a.id, 0)
            a.trust[b.id] += perception * 0.1

            reply_line = get_personality_reply_line(b, convo_type, option_id)
            
            result_text = f"{a.name} opened up a little, and the conversation brought a quiet sense of understanding."

        elif option_id == "stay_guarded":
            a_gain = a_mod["guarded_bonus"]
            b_gain = b_mod["guarded_bonus"]

            if a_gain > 0:
                a.trust[b.id] = a.trust.get(b.id, 0) + a_gain
            if b_gain > 0:
                b.trust[a.id] = b.trust.get(a.id, 0) + b_gain

            reply_line = get_personality_reply_line(b, convo_type, option_id)
            
            result_text = f"The conversation stayed polite, but neither dragon truly let the other in."

        elif option_id == "push_issue":
            a_loss = 1 + a_mod["push_bonus"] + a_mod["resentment_bonus"]
            b_loss = 1 + b_mod["resentment_bonus"]

            a.resentment[b.id] = a.resentment.get(b.id, 0) + a_loss
            b.resentment[a.id] = b.resentment.get(a.id, 0) + b_loss

            from core.sim.consequences import schedule_consequence

            if a.resentment.get(b.id, 0) >= 4:
                schedule_consequence(world, delay=3, data={
                    "type": "possible_defection",
                    "dragon_id": a.id,
                    "caused_by": b.id
                })

            reply_line = get_personality_reply_line(b, convo_type, option_id)
            
            result_text = f"{a.name} made the exchange more tense than it needed to be."

    log_event(
        world,
        f"{a.name} and {b.name} spoke. {player_line} {reply_line} {result_text}",
        involved_ids=[a.id, b.id],
        event_type="conversation",
        importance=2
    )

    return player_line, reply_line, result_text