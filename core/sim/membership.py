"""Transitions for dragons who leave the player's tribe."""


def mark_departed(world, dragon):
    dragon.status = "Departed"
    dragon.location = "foreign_territory"
    dragon.assigned_healer_id = None
    for other in world.dragons:
        if other.id != dragon.id and (other.id == dragon.mate_id or other.mate_id == dragon.id):
            for member, former in ((dragon, other), (other, dragon)):
                flag = ("former_mate", former.id)
                if flag not in member.memory_flags:
                    member.memory_flags.append(flag)
            if other.mate_id == dragon.id:
                other.mate_id = None
    dragon.mate_id = None
