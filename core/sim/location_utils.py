def get_dragons_here_text(world, loc_id):
    dragons_here = [
        d for d in world.dragons
        if d.status == "Alive" and getattr(d, "location", None) == loc_id
    ]

    if not dragons_here:
        return "No dragons are currently here."

    return "\n".join(
        f"- {d.name} ({d.role})"
        for d in dragons_here
    )