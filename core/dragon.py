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

    earned_titles: list[str] = field(default_factory=list)
    legend_flags: dict[str, int] = field(default_factory=dict)  

    combat_skill: int = 0
    combat_wins: int = 0
    combat_losses: int = 0
    hardship_survived: int = 0
    peace_actions: int = 0
    watchful_actions: int = 0

    trust: dict[int, float] = field(default_factory=dict)
    resentment: dict[int, float] = field(default_factory=dict)
    grief_level: int = 0
    leadership_pressure: int = 0
    rivalry_levels: dict = field(default_factory=dict)
    memory_flags: list[tuple[str, int] | tuple[str, int, int]] = field(default_factory=list)

    personality_traits: list[str] = field(default_factory=list)
    behavior_type: str = ""

    height: float = 0.0
    eye_color: str = ""
    horn_type: str = ""
    head_type: str = ""
    snout_type: str = ""
    eye_style: str = ""
    tail_type: str = ""
    leg_type: str = ""
    wing_type: str = ""
    body_type: str = ""
    marking_type: str = ""
    scale_palette: str = ""
    special_visual_traits: list[str] = field(default_factory=list)

    hobbies: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    scars: list[str] = field(default_factory=list)
    random_fact: str = ""

    cause_of_death: str = ""