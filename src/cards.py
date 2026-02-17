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

    # [NEW] Список групп связанных направлений.
    # По умолчанию None означает, что все открытые выходы связаны (стандартная карта).
    # Пример спецкарты: [{Direction.UP}, {Direction.DOWN, Direction.LEFT, Direction.RIGHT}]
    subnetworks: Optional[List[Set[Direction]]] = None

    def get_exits(self, entry_from: Optional[Direction]) -> Set[Direction]:
        """
        Возвращает доступные выходы, если мы вошли в карту со стороны entry_from.
        entry_from - это направление ОТКУДА мы пришли (например, если пришли снизу, то entry_from=UP, т.к. вход снизу это UP).
        Нет, стоп. В board.py логика: entry_from - это сторона самой карты.
        Если мы идем с клетки (0,0) ВВЕРХ на (0,1), то мы входим в (0,1) через DOWN.
        """
        # Сначала собираем все открытые стороны
        all_open = {d for d in Direction if self.openings.get_opening(d)}

        # Если подсети не заданы, все открытые выходы связаны
        if self.subnetworks is None:
            return all_open

        # Если заданы подсети, ищем ту, в которую мы вошли
        # Если entry_from is None (мы стартуем с этой карты), возвращаем все возможные
        if entry_from is None:
            # Объединяем все подсети
            result = set()
            for net in self.subnetworks:
                result.update(net)
            return result & all_open

        for net in self.subnetworks:
            if entry_from in net:
                # Мы попали в эту подсеть. Можем выйти в любую сторону этой подсети,
                # которая физически открыта.
                return net & all_open

        # Если вход недоступен (по идее невозможно, если проверки пройдены)
        return set()

    def rotate(self):
        self.openings.rotate()
        # [NEW] Ротация подсетей
        if self.subnetworks:
            new_subnetworks = []
            for net in self.subnetworks:
                new_net = set()
                for d in net:
                    if d == Direction.UP:
                        new_net.add(Direction.DOWN)
                    elif d == Direction.DOWN:
                        new_net.add(Direction.UP)
                    elif d == Direction.LEFT:
                        new_net.add(Direction.RIGHT)
                    elif d == Direction.RIGHT:
                        new_net.add(Direction.LEFT)
                new_subnetworks.append(new_net)
            self.subnetworks = new_subnetworks

    def get_rotated_copy(self) -> 'TunnelCard':
        new_card = copy.deepcopy(self)
        new_card.rotate()
        new_card.name = f"{self.name} (180°)"
        return new_card

    def __str__(self):
        if self.is_gold:
            if self.gold_value > 0:
                return f"{self.color}${ConsoleColor.YELLOW}{self.gold_value}{self.color}${ConsoleColor.RESET}"
            return f"{self.color} ? {ConsoleColor.RESET}"

        # [NEW] Визуализация спецкарты (если есть подсети)
        if self.subnetworks and len(self.subnetworks) > 1:
            # Это упрощенная визуализация для T-split карты
            # Если это наша карта (Верх отдельно, Т-низ отдельно)
            # Проверяем маску, чтобы понять ориентацию
            if self.openings.up and self.openings.down and self.openings.left:
                return f"{self.color} ∓ {ConsoleColor.RESET}"  # Примерный символ

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