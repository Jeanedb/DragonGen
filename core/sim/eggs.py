import random


def create_egg(parent1, parent2):
    return {
        "mother": parent1.name,
        "father": parent2.name,
        "age": 0,
        "hatch_time": random.randint(3, 6),
        "size": random.choice(["small", "heavy", "large", "round"]),
        "shell_color": random.choice(["blood-red", "dark blue", "pale gold", "ash-gray", "speckled"]),
        "movement": random.choice(["rocks often", "barely moves", "twitches sharply", "rolls gently"]),
        "condition": random.choice(["healthy", "warm", "weak", "restless"]),
        "caretaker": None,
    }