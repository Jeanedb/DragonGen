from core.generator import generate_starting_world
from core.simulation import advance_moon

def print_world(world):
    print(f"\n=== {world.tribe_name} | Moon {world.moon} ===")
    print("\nDragons:")
    for d in world.dragons:
        print(
            f"ID {d.id} | {d.name} | {d.tribe} | Age {d.age_moons} | "
            f"{d.role} | {d.personality} | Health: {d.health} | Status: {d.status}"
        )

    print("\nRecent Events:")
    for event in world.event_log[-10:]:
        print(f"- {event}")

world = generate_starting_world()
print_world(world)

for _ in range(3):
    input("\nPress Enter to advance one moon...")
    advance_moon(world)
    print_world(world)