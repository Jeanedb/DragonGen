
import random

from dataclasses import dataclass, field


@dataclass
class Memory:
    type: str
    moon: int
    other_id: int | None = None
    importance: int = 1
    reflection_weight: float = 1.0
    last_reflected_moon: int | None = None
    tags: list[str] = field(default_factory=list)

def current_moon(world):
    return getattr(world, "moon", 0)


def add_memory(dragon, memory):
    if not hasattr(dragon, "memories") or dragon.memories is None:
        dragon.memories = []

    for existing in dragon.memories:
        same_memory = (
            existing.type == memory.type
            and existing.other_id == memory.other_id
            and existing.moon == memory.moon
        )

        if not same_memory:
            continue

        existing.importance = min(
            10,
            existing.importance + 1
        )

        existing.reflection_weight = max(
            existing.reflection_weight,
            memory.reflection_weight
        )

        for tag in memory.tags:
            if tag not in existing.tags:
                existing.tags.append(tag)

        memory.importance = existing.importance
        memory.reflection_weight = existing.reflection_weight
        memory.tags = list(existing.tags)

        return existing

    dragon.memories.append(memory)
    return memory


def has_memory(dragon, memory_type):
    return any(
        getattr(memory, "type", None) == memory_type
        for memory in getattr(dragon, "memories", [])
    )


def get_memories(dragon, memory_type):
    return [
        memory for memory in getattr(dragon, "memories", [])
        if getattr(memory, "type", None) == memory_type
    ]

def choose_memory_to_reflect(dragon, moon=None, cooldown=3):

    memories = getattr(dragon, "memories", [])

    if not memories:
        return None

    eligible_memories = [
        memory for memory in memories
        if (
            moon is None
            or getattr(memory, "last_reflected_moon", None) is None
            or moon - memory.last_reflected_moon >= cooldown
        )
    ]

    if not eligible_memories:
        return None

    weights = [
        max(0.1, memory.importance * memory.reflection_weight)
        for memory in eligible_memories
    ]

    return random.choices(
        eligible_memories,
        weights=weights,
        k=1
    )[0]