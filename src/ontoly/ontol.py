from enum import Enum
from typing import Dict, List, Tuple, Optional, Set
from pydantic import BaseModel, Field, ConfigDict, field_validator

# --- 1. Базовые типы и Координаты ---

Coordinates = Tuple[int, int]


class Direction(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"

    @property
    def vector(self) -> Coordinates:
        return {
            "UP": (0, -1), "DOWN": (0, 1),
            "LEFT": (-1, 0), "RIGHT": (1, 0)
        }[self.value]

    @property
    def opposite(self) -> 'Direction':
        return {
            "UP": "DOWN", "DOWN": "UP",
            "LEFT": "RIGHT", "RIGHT": "LEFT"
        }[self.value]


def add_coords(c1: Coordinates, c2: Coordinates) -> Coordinates:
    return c1[0] + c2[0], c1[1] + c2[1]


# --- 2. Карты (Неизменяемые) ---

class CardOpenings(BaseModel):
    model_config = ConfigDict(frozen=True)  # Хешируемый и неизменяемый

    up: bool = False
    down: bool = False
    left: bool = False
    right: bool = False

    def get(self, direction: Direction) -> bool:
        """Возвращает наличие прохода в указанном направлении."""
        return getattr(self, direction.lower())

    def rotate_180(self) -> 'CardOpenings':
        """Возвращает новые выходы после поворота на 180 градусов."""
        return CardOpenings(
            up=self.down, down=self.up,
            left=self.right, right=self.left
        )


class TunnelCard(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    openings: CardOpenings
    is_gold: bool = False
    is_start: bool = False

    def rotate(self) -> 'TunnelCard':
        """Возвращает повернутую копию карты."""
        suffix = " (Rotated)" if "(Rotated)" not in self.name else ""
        return self.model_copy(update={
            "name": self.name + suffix,
            "openings": self.openings.rotate_180()
        })

    def __repr__(self):
        return f"Card({self.name})"

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


# --- 3. Ход (Действие) ---

class GameMove(BaseModel):
    model_config = ConfigDict(frozen=True)

    x: int
    y: int
    card_idx: int  # Индекс карты в руке
    rotate: bool = False


# --- 4. Состояние Игры (Мир) ---

class PlayerState(BaseModel):
    model_config = ConfigDict(frozen=True)  # Игрок тоже неизменяем
    id: int
    hand: Tuple[TunnelCard, ...] = Field(default_factory=tuple)  # Tuple вместо List для immutability
    score: int = 0


class GameState(BaseModel):
    model_config = ConfigDict(frozen=True)

    grid: Dict[Coordinates, TunnelCard] = Field(default_factory=dict)
    players: Dict[int, PlayerState]
    current_player_id: int
    deck_count: int  # Робот знает только количество карт, а не сами карты

    # Скрытая информация (для движка, но не для логики принятия решений)
    # В реальном AI мы бы вынесли это в отдельный класс "ServerState",
    # но для локальной симуляции оставим здесь, пометив как "hidden".
    deck: List[TunnelCard] = Field(default_factory=list, exclude=True)

    @property
    def current_player(self) -> PlayerState:
        return self.players[self.current_player_id]

    def get_card(self, x: int, y: int) -> Optional[TunnelCard]:
        return self.grid.get((x, y))

    # --- ЛОГИКА ВАЛИДАЦИИ (Перенесена из board.py) ---

    def is_move_valid(self, move: GameMove) -> bool:
        """
        Проверяет валидность хода согласно правилам Saboteur.
        Карточку туннеля следует выкладывать только стыкуя сторона к стороне.
        """
        # 1. Индекс карты валиден?
        hand = self.current_player.hand
        if move.card_idx < 0 or move.card_idx >= len(hand):
            return False

        # 2. Клетка занята?
        if (move.x, move.y) in self.grid:
            return False

        # 3. Подготовка карты (поворот если надо)
        card_to_place = hand[move.card_idx]
        if move.rotate:
            card_to_place = card_to_place.rotate()

        # 4. Проверка соседей
        has_neighbor = False

        for direction in Direction:
            neighbor_pos = add_coords((move.x, move.y), direction.vector)
            neighbor_card = self.grid.get(neighbor_pos)

            if neighbor_card:
                has_neighbor = True

                # Мой выход в эту сторону
                my_opening = card_to_place.openings.get(direction)

                # Выход соседа в мою сторону (обратное направление)
                neighbor_opening = neighbor_card.openings.get(direction.opposite)

                # Правило стыковки: туннель к туннелю, стена к стене
                if my_opening != neighbor_opening:
                    return False

        # 5. Карта должна касаться хотя бы одной существующей карты
        if not has_neighbor:
            return False

        return True

    # --- ЛОГИКА ПЕРЕХОДА (State Transition) ---

    def apply_move(self, move: GameMove) -> 'GameState':
        """
        Возвращает НОВОЕ состояние после хода. Не мутирует текущее.
        """
        if not self.is_move_valid(move):
            raise ValueError(f"Invalid move: {move}")

        # Получаем данные
        player = self.current_player
        card_to_place = player.hand[move.card_idx]
        if move.rotate:
            card_to_place = card_to_place.rotate()

        # 1. Обновляем сетку
        new_grid = self.grid.copy()
        new_grid[(move.x, move.y)] = card_to_place

        # 2. Обновляем руку игрока (удаляем карту)
        # Используем срезы для кортежей
        new_hand_list = list(player.hand)
        new_hand_list.pop(move.card_idx)

        # (Опционально) Взять карту из колоды, если это симуляция движка
        # Для чистого AI-поиска (MCTS) мы обычно не берем случайную карту,
        # а работаем с тем что есть, или "предполагаем" карту.
        # Но для простоты здесь просто уменьшим счетчик колоды.
        new_deck_count = self.deck_count
        if new_deck_count > 0:
            # В реальной игре здесь была бы логика взятия карты.
            # Для онтологии просто помечаем факт.
            new_deck_count -= 1

        new_player = player.model_copy(update={"hand": tuple(new_hand_list)})

        new_players = self.players.copy()
        new_players[self.current_player_id] = new_player

        # 3. Переход хода
        next_player_id = 1 - self.current_player_id

        return self.model_copy(update={
            "grid": new_grid,
            "players": new_players,
            "current_player_id": next_player_id,
            "deck_count": new_deck_count
        })


