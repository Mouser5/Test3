from dataclasses import dataclass
from enum import Enum
import copy


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
    gold_value: int = 0  # [NEW] Количество золота (0 если не золото или закрыто)
    color: str = ConsoleColor.RESET

    def rotate(self):
        self.openings.rotate()

    def get_rotated_copy(self) -> 'TunnelCard':
        new_card = copy.deepcopy(self)
        new_card.rotate()
        new_card.name = f"{self.name} (180°)"
        # new_card.color = self.color
        # new_card.gold_value = self.gold_value
        # new_card.is_gold = self.is_gold
        return new_card

    def __str__(self):
        # Если карта золотая
        if self.is_gold:
            # Если это уже открытое золото (есть значение)
            if self.gold_value > 0:
                # Формат $X$: знаки доллара цветом игрока, число - желтым
                return f"{self.color}${ConsoleColor.YELLOW}{self.gold_value}{self.color}${ConsoleColor.RESET}"

            # Если это закрытое золото (заглушка)
            return f"{self.color} ? {ConsoleColor.RESET}"

        # ... (далее код для обычных туннелей без изменений)
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