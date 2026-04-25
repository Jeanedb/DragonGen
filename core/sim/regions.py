import random


def normalize_region_tribe_name(tribe):
    if not tribe:
        return tribe

    mapping = {
        "MudWing": "MudWings",
        "SandWing": "SandWings",
        "SkyWing": "SkyWings",
        "SeaWing": "SeaWings",
        "RainWing": "RainWings",
        "IceWing": "IceWings",
        "NightWing": "NightWings",
    }

    return mapping.get(tribe, tribe)


def get_regions_for_tribe(world, tribe):
    tribe = normalize_region_tribe_name(tribe)
    return [
        r for r, owner in world.territory_control.items()
        if owner == tribe
    ]


def get_random_region(world, tribe):
    tribe = normalize_region_tribe_name(tribe)
    regions = get_regions_for_tribe(world, tribe)

    if not regions:
        return "unknown region"

    weights = []
    for region in regions:
        activity = world.region_activity.get(region, 0)
        weight = 1.0 + (activity * 0.25)
        weights.append(weight)

    return random.choices(regions, weights=weights, k=1)[0]


def get_random_landmark(world, region):
    landmarks = world.region_landmarks.get(region, [])
    return random.choice(landmarks) if landmarks else "unknown landmark"


def record_region_activity(world, region, amount=1):
    if not region or region == "unknown region":
        return

    if region not in world.region_activity:
        world.region_activity[region] = 0

    world.region_activity[region] += amount


def get_region_intensity(world, region):
    if not region:
        return 0.0

    activity = world.region_activity.get(region, 0)

    if activity >= 6:
        return 0.25
    elif activity >= 3:
        return 0.15
    elif activity >= 1:
        return 0.05
    else:
        return 0.0


def get_top_active_regions(world, limit=3):
    items = sorted(
        world.region_activity.items(),
        key=lambda x: x[1],
        reverse=True
    )
    return items[:limit]