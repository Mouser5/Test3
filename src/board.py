from typing import Dict, Tuple, Optional
from cards import TunnelCard, Direction


class GameBoard:
    def __init__(self):
        self.grid: Dict[Tuple[int, int], TunnelCard] = {}

    def place_card(self, x: int, y: int, card: TunnelCard):
        self.grid[(x, y)] = card

    def get_card(self, x: int, y: int) -> Optional[TunnelCard]:
        return self.grid.get((x, y))

    def is_move_valid(self, x: int, y: int, new_card: TunnelCard) -> bool:
        """
        Проверяет валидность хода согласно правилам Saboteur.
        [cite_start][cite: 58] Карточку туннеля следует выкладывать только стыкуя сторона к стороне.
        """
        if (x, y) in self.grid:
            print(f"Ошибка: Клетка ({x}, {y}) занята.")
            return False

        has_neighbor = False

        for direction in Direction:
            dx, dy = direction.value
            neighbor_pos = (x + dx, y + dy)
            neighbor_card = self.grid.get(neighbor_pos)

            if neighbor_card:
                has_neighbor = True

                # [cite_start]Проверка стыковки: Туннель к туннелю, стена к стене [cite: 59]
                my_opening = new_card.openings.get_opening(direction)

                opposite_dir = self._get_opposite_dir(direction)
                neighbor_opening = neighbor_card.openings.get_opening(opposite_dir)

                if my_opening != neighbor_opening:
                    # Для отладки можно раскомментировать print
                    # print(f"Несовпадение с соседом {direction.name}")
                    return False

        if not has_neighbor:
            # print("Карта должна касаться существующих карт.")
            return False

        return True

    def _get_opposite_dir(self, direction: Direction) -> Direction:
        if direction == Direction.UP: return Direction.DOWN
        if direction == Direction.DOWN: return Direction.UP
        if direction == Direction.LEFT: return Direction.RIGHT
        return Direction.LEFT