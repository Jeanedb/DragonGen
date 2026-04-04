from dataclasses import dataclass, field
from typing import List, Optional


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
    parents: List[int] = field(default_factory=list)
    dragonets: List[int] = field(default_factory=list)
    friends: List[int] = field(default_factory=list)
    rivals: List[int] = field(default_factory=list)
    trust: dict = field(default_factory=dict)
    resentment: dict = field(default_factory=dict)
    memory_flags: list = field(default_factory=list)