from dataclasses import dataclass, field
from enum import Enum
import copy
from typing import List, Set, Optional

class Direction(Enum):
    UP = (0, 1)
    DOWN = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

@dataclass
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

    def rotate(self):
        self.up, self.down = self.down, self.up
        self.left, self.right = self.right, self.left

@dataclass
class Card:
    name: str
    owner_id: Optional[int] = None

@dataclass
class PathCard(Card):
    openings: CardOpenings = field(default_factory=CardOpenings)
    subnetworks: Optional[List[Set[Direction]]] = None

    def get_exits(self, entry_from: Optional[Direction]) -> Set[Direction]:
        all_open = {d for d in Direction if self.openings.get_opening(d)}
        if self.subnetworks is None: return all_open
        if entry_from is None:
            result = set()
            for net in self.subnetworks: result.update(net)
            return result & all_open
        for net in self.subnetworks:
            if entry_from in net: return net & all_open
        return set()

    def rotate(self):
        self.openings.rotate()
        if self.subnetworks:
            new_subs = []
            for net in self.subnetworks:
                new_net = set()
                for d in net:
                    if d == Direction.UP: new_net.add(Direction.DOWN)
                    elif d == Direction.DOWN: new_net.add(Direction.UP)
                    elif d == Direction.LEFT: new_net.add(Direction.RIGHT)
                    elif d == Direction.RIGHT: new_net.add(Direction.LEFT)
                new_subs.append(new_net)
            self.subnetworks = new_subs

    def get_rotated_copy(self) -> 'PathCard':
        new_card = copy.deepcopy(self)
        new_card.rotate()
        new_card.name = f"{self.name} (180°)"
        return new_card

@dataclass
class TunnelCard(PathCard): pass

@dataclass
class StartCard(PathCard): pass

@dataclass
class DoorCard(PathCard):
    door_owner_id: int = 0
    is_locked: bool = True

@dataclass
class LadderCard(PathCard): pass

@dataclass
class GoldCard(PathCard):
    gold_value: int = 0
    is_revealed: bool = False

# --- НОВЫЕ ТИПЫ ДЛЯ ИНВЕНТАРЯ ---
class EquipmentType(Enum):
    LAMP = "Лампа"
    CART = "Вагонетка"
    PICKAXE = "Кирка"

class ActionType(Enum):
    KEY = "key"
    ROCKFALL = "rockfall"
    SABOTAGE = "sabotage" # Поломка
    REPAIR = "repair"     # Починка

@dataclass
class ActionCard(Card):
    action_type: ActionType = ActionType.KEY
    equipment_type: Optional[EquipmentType] = None  # Нужно только для SABOTAGE и REPAIR