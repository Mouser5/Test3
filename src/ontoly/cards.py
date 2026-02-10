from enum import Enum
from pydantic import BaseModel, ConfigDict
from typing import Optional


class Direction(str, Enum):  # Из онтологии, с добавлением vector и opposite
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"

    @property
    def vector(self) -> tuple[int, int]:
        return {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}[self.value]

    @property
    def opposite(self) -> 'Direction':
        return {"UP": Direction.DOWN, "DOWN": Direction.UP, "LEFT": Direction.RIGHT, "RIGHT": Direction.LEFT}[
            self.value]


class CardOpenings(BaseModel):  # Из онтологии
    model_config = ConfigDict(frozen=True)
    up: bool = False
    down: bool = False
    left: bool = False
    right: bool = False

    def get_opening(self, direction: Direction) -> bool:  # Переименовано в get_opening для совместимости
        return self.get(direction)

    def rotate(self):  # Для совместимости со старым кодом
        return self.rotate_180()


class TunnelCard(BaseModel):  # Из онтологии, с адаптацией __str__
    model_config = ConfigDict(frozen=True)
    name: str
    openings: CardOpenings

    def rotate(self) -> 'TunnelCard':
        return super().rotate()  # Используем метод из онтологии

    def get_rotated_copy(self) -> 'TunnelCard':
        return self.rotate()

    def __str__(self):  # Сохраняем старый __str__ для печати
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
        return symbols.get(mask, " ? ")