from core.sim.regions import (
    get_random_region,
    get_random_landmark,
    record_region_activity,
)

from core.sim.politics import get_random_foreign_tribe

def create_border_sighting_event(world):
    tribe = get_random_foreign_tribe(world)
    if not tribe:
        return False

    region = get_random_region(world, tribe)
    landmark = get_random_landmark(world, region)

    record_region_activity(world, region)

    prompt_text = (
        f"A patrol from the {tribe}s has been spotted near {landmark} in {region}. "
        f"They appear to be watching your territory."
    )

    options = [
        {"id": "observe", "text": "Observe them from a distance"},
        {"id": "approach", "text": "Approach and question them"},
        {"id": "drive_off", "text": "Drive them away immediately"},
    ]

    world.pending_choice = {
        "type": "border_sighting",
        "tribe": tribe,
        "region": region,
        "landmark": landmark,
        "text": prompt_text,
        "options": options,
    }
    return True

def create_border_violation_event(world):
    tribe = get_random_foreign_tribe(world)
    if not tribe:
        return False

    region = get_random_region(world, tribe)
    landmark = get_random_landmark(world, region)

    record_region_activity(world, region)

    prompt_text = (
        f"Tracks from the {tribe}s have been discovered near {landmark} in {region}. "
        f"They may have crossed into your territory."
    )

    options = [
        {"id": "ignore_tracks", "text": "Ignore it for now"},
        {"id": "investigate_tracks", "text": "Investigate further"},
        {"id": "respond_forcefully", "text": "Prepare a response"},
    ]

    world.pending_choice = {
        "type": "border_violation",
        "tribe": tribe,
        "region": region,
        "landmark": landmark,
        "text": prompt_text,
        "options": options,
    }

    return True

def create_aid_delivery_event(world):
    tribe = get_random_foreign_tribe(world)
    if not tribe:
        return False

    region = get_random_region(world, tribe)
    landmark = get_random_landmark(world, region)

    record_region_activity(world, region)

    prompt_text = (
        f"A small group of {tribe}s is delivering supplies near {landmark} in {region}. "
        f"They request safe passage through your lands."
    )

    options = [
        {"id": "allow_aid", "text": "Allow the aid to pass"},
        {"id": "inspect_aid", "text": "Inspect the supplies"},
        {"id": "deny_aid", "text": "Deny passage"},
    ]

    world.pending_choice = {
        "type": "aid_delivery",
        "tribe": tribe,
        "region": region,
        "landmark": landmark,
        "text": prompt_text,
        "options": options,
    }

    return True