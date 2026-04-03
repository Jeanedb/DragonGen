from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from core.dragon import Dragon


@dataclass
class World:
    tribe_name: str
    moon: int = 0
    dragons: List[Dragon] = field(default_factory=list)
    event_log: List[Dict[str, Any]] = field(default_factory=list)
    pending_choice: Optional[Dict[str, Any]] = None