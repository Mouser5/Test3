from dataclasses import dataclass
from enum import Enum

class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

@dataclass
class CardOpenings:
    """Определяет, где у карты есть проходы."""
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

@dataclass
class Card:
    name: str

@dataclass
class TunnelCard(Card):
    openings: CardOpenings

    def __str__(self):
        # Битовая маска: Up(8) Down(4) Left(2) Right(1)
        mask = 0
        if self.openings.up: mask += 8
        if self.openings.down: mask += 4
        if self.openings.left: mask += 2
        if self.openings.right: mask += 1

        # Символы псевдографики
        symbols = {
            0: " ? ",
            1: " ╺ ", 2: " ╸ ", 3: " ═ ",
            4: " ╻ ", 5: " ┏ ", 6: " ┓ ", 7: " ┳ ",
            8: " ╹ ", 9: " ┗ ", 10: " ┛ ", 11: " ┻ ",
            12: " ║ ", 13: " ┣ ", 14: " ┫ ", 15: " ╬ ",
        }
        return symbols.get(mask, " ? ")