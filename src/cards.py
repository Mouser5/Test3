from dataclasses import dataclass, field
from enum import Enum
import copy
from typing import List, Set, Optional


class Direction(Enum):
    UP = (0, 1)
    DOWN = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)


class ConsoleColor:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'     # Для заблокированных дверей
    CYAN = '\033[96m'    # Для ключей
    RESET = '\033[0m'


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


@dataclass
class TunnelCard(Card):
    openings: CardOpenings
    is_gold: bool = False
    gold_value: int = 0
    color: str = ConsoleColor.RESET

    is_ladder: bool = False
    subnetworks: Optional[List[Set[Direction]]] = None

    # [NEW] Новые механики дверей и ключей
    is_door: bool = False
    is_locked: bool = True  # По умолчанию дверь закрыта для соперника
    is_key: bool = False

    def get_exits(self, entry_from: Optional[Direction]) -> Set[Direction]:
        all_open = {d for d in Direction if self.openings.get_opening(d)}
        if self.subnetworks is None:
            return all_open
        if entry_from is None:
            result = set()
            for net in self.subnetworks:
                result.update(net)
            return result & all_open
        for net in self.subnetworks:
            if entry_from in net:
                return net & all_open
        return set()

    def rotate(self):
        # Ключи не вращаются (это предмет, а не туннель)
        if self.is_key:
            return

        self.openings.rotate()
        if self.subnetworks:
            new_subnetworks = []
            for net in self.subnetworks:
                new_net = set()
                for d in net:
                    if d == Direction.UP: new_net.add(Direction.DOWN)
                    elif d == Direction.DOWN: new_net.add(Direction.UP)
                    elif d == Direction.LEFT: new_net.add(Direction.RIGHT)
                    elif d == Direction.RIGHT: new_net.add(Direction.LEFT)
                new_subnetworks.append(new_net)
            self.subnetworks = new_subnetworks

    def get_rotated_copy(self) -> 'TunnelCard':
        new_card = copy.deepcopy(self)
        new_card.rotate()
        if not self.is_key:
            new_card.name = f"{self.name} (180°)"
        return new_card

    def __str__(self):
        if self.is_gold:
            if self.gold_value > 0:
                return f"{self.color}${ConsoleColor.YELLOW}{self.gold_value}{self.color}${ConsoleColor.RESET}"
            return f"{self.color} ? {ConsoleColor.RESET}"

        if self.is_key:
            return f"{ConsoleColor.CYAN} KEY {ConsoleColor.RESET}"

        # Отображение двери
        if self.is_door:
            if self.is_locked:
                return f"{self.color}▐█▌{ConsoleColor.RESET}" # Закрытая дверь
            else:
                return f"{self.color}▐ {ConsoleColor.RESET}▌{ConsoleColor.RESET}" # Открытая дверь

        if self.is_ladder:
            return f"{self.color} # {ConsoleColor.RESET}"

        if self.subnetworks and len(self.subnetworks) > 1:
            if self.openings.up and self.openings.down and self.openings.left:
                return f"{self.color} ∓ {ConsoleColor.RESET}"

        mask = 0
        if self.openings.up: mask += 8
        if self.openings.down: mask += 4
        if self.openings.left: mask += 2
        if self.openings.right: mask += 1

        symbols = {
            0: " ? ", 1: "  ╺", 2: "╸  ", 3: " ═ ",
            4: " ╻ ", 5: " ┏ ", 6: " ┓ ", 7: " ┳ ",
            8: " ╹ ", 9: " ┗ ", 10: " ┛ ", 11: " ┻ ",
            12: " ║ ", 13: " ┣ ", 14: " ┫ ", 15: " ╬ ",
        }
        symbol = symbols.get(mask, " ? ")
        return f"{self.color}{symbol}{ConsoleColor.RESET}"