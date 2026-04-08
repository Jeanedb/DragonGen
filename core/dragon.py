from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Dragon:
    id: int
    name: str
    tribe: str
    age_moons: int
    role: str
    personality: str

    rank: str = "None"
    health: str = "Healthy"
    status: str = "Alive"

    mate_id: Optional[int] = None

    parents: list[int] = field(default_factory=list)
    dragonets: list[int] = field(default_factory=list)
    friends: list[int] = field(default_factory=list)
    rivals: list[int] = field(default_factory=list)

    trust: dict[int, float] = field(default_factory=dict)
    resentment: dict[int, float] = field(default_factory=dict)
    memory_flags: list[tuple[str, int]] = field(default_factory=list)

    personality_traits: list[str] = field(default_factory=list)

    height: float = 0.0
    eye_color: str = ""
    hobbies: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    scars: list[str] = field(default_factory=list)
    random_fact: str = ""

    cause_of_death: str = ""