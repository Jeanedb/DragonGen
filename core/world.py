from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from core.dragon import Dragon


@dataclass
class World:
    tribe_name: str
    moon: int = 0
    dragons: list[Dragon] = field(default_factory=list)
    event_log: list[dict] = field(default_factory=list)
    pending_choice: dict | None = None
    tension: float = 0.0

    leader_id: int | None = None
    deputy_id: int | None = None

    direction: str | None = None
    direction_timer: int = 0

    tribal_relations: dict[str, int] = field(default_factory=dict)
    tribal_incidents: dict[str, list] = field(default_factory=dict)   
    tribal_leaders: dict[str, str] = field(default_factory=dict) 
    diplomacy_cooldowns: dict[str, int] = field(default_factory=dict)
    tribal_traits: dict[str, str] = field(default_factory=dict)

    tribe_titles: list[str] = field(default_factory=list)
    world_flags: dict[str, int] = field(default_factory=dict)

    territory_control: dict[str, str] = field(default_factory=dict)
    region_landmarks: dict[str, list] = field(default_factory=dict)