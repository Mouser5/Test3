from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, FrozenSet

class Direction(Enum):
    UP = (0, 1)
    DOWN = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

@dataclass(slots=True, frozen=True)
class CardOpenings:
    up: bool = False
    down: bool = False
    left: bool = False
    right: bool = False

    def get_opening(self, direction: Direction) -> bool:
        if direction == Direction.UP: return self.up
        if direction == Direction.DOWN: return self.down
        if direction == Direction.LEFT: return self.left
        if direction == Direction.RIGHT: return self.right
        return False

# --- БАЗОВЫЙ ШАБЛОН ---
@dataclass(slots=True, frozen=True)
class CardTemplate:
    id: str
    name: str

# --- ШАБЛОНЫ ПУТЕЙ ---
@dataclass(slots=True, frozen=True)
class PathCardTemplate(CardTemplate):
    openings: CardOpenings = field(default_factory=CardOpenings)
    subnetworks: Optional[List[FrozenSet[Direction]]] = None

    def get_exits(self, entry_from: Optional[Direction]) -> FrozenSet[Direction]:
        # Оптимизация: генератор заменен на прямой список для скорости
        all_open = frozenset(d for d in (Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT) if self.openings.get_opening(d))
        if self.subnetworks is None:
            return all_open

        if entry_from is None:
            result = set()
            for net in self.subnetworks: result.update(net)
            return frozenset(result & set(all_open))

        for net in self.subnetworks:
            if entry_from in net: return frozenset(net & set(all_open))
        return frozenset()

@dataclass(slots=True, frozen=True)
class TunnelCardTemplate(PathCardTemplate):
    pass

@dataclass(slots=True, frozen=True)
class StartCardTemplate(PathCardTemplate):
    pass

@dataclass(slots=True, frozen=True)
class DoorCardTemplate(PathCardTemplate):
    door_owner_id: int = 0

@dataclass(slots=True, frozen=True)
class LadderCardTemplate(PathCardTemplate):
    pass

@dataclass(slots=True, frozen=True)
class GoldCardTemplate(PathCardTemplate):
    gold_value: int = 0

# --- ШАБЛОНЫ ДЕЙСТВИЙ ---
class EquipmentType(Enum):
    LAMP = "Лампа"
    CART = "Вагонетка"
    PICKAXE = "Кирка"

class ActionType(Enum):
    KEY = "key"
    ROCKFALL = "rockfall"
    SABOTAGE = "sabotage"
    REPAIR = "repair"
    MAP = "map"

@dataclass(slots=True, frozen=True)
class ActionCardTemplate(CardTemplate):
    action_type: ActionType
    equipment_type: Optional[EquipmentType] = None