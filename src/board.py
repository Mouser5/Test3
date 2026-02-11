from typing import Dict, Tuple, Optional, Set, List
from cards import TunnelCard, Direction


class GameBoard:
    def __init__(self):
        self.grid: Dict[Tuple[int, int], TunnelCard] = {}

    def place_card(self, x: int, y: int, card: TunnelCard):
        self.grid[(x, y)] = card

    def get_card(self, x: int, y: int) -> Optional[TunnelCard]:
        return self.grid.get((x, y))

    def _get_opposite_dir(self, direction: Direction) -> Direction:
        if direction == Direction.UP: return Direction.DOWN
        if direction == Direction.DOWN: return Direction.UP
        if direction == Direction.LEFT: return Direction.RIGHT
        return Direction.LEFT

    def is_move_valid(self, x: int, y: int, new_card: TunnelCard, player_start_pos: Tuple[int, int]) -> bool:
        """
        Проверяет валидность хода:
        1. Клетка свободна.
        2. Стыковка с соседями (Saboteur rules).
        3. [NEW] Есть путь от старта игрока до этой новой карты.
        """
        if (x, y) in self.grid:
            # print(f"Ошибка: Клетка ({x}, {y}) занята.")
            return False

        has_neighbor = False
        connected_to_valid_path = False

        # 1. Проверка физической стыковки с соседями
        neighbors_to_check = []

        for direction in Direction:
            dx, dy = direction.value
            neighbor_pos = (x + dx, y + dy)
            neighbor_card = self.grid.get(neighbor_pos)

            if neighbor_card:
                has_neighbor = True
                my_opening = new_card.openings.get_opening(direction)
                opposite_dir = self._get_opposite_dir(direction)
                neighbor_opening = neighbor_card.openings.get_opening(opposite_dir)

                # Правило: туннель к туннелю, стена к стене
                if not (neighbor_card.is_gold and neighbor_card.gold_value==0):
                    if my_opening != neighbor_opening:
                        return False

                # Если мы соединились туннелем (True-True), запоминаем этого соседа для проверки пути
                if my_opening and neighbor_opening:
                    neighbors_to_check.append(neighbor_pos)

        if not has_neighbor:
            return False

        # 2. [NEW] Проверка пути до старта (Color connection logic)
        # Мы должны проверить, связан ли ХОТЯ БЫ ОДИН из соседей,
        # с которым мы соединились туннелем, со стартовой точкой игрока.

        # Получаем все координаты, доступные от старта игрока на текущий момент
        reachable_nodes = self._bfs_reachable_nodes(player_start_pos)

        for n_pos in neighbors_to_check:
            if n_pos in reachable_nodes:
                connected_to_valid_path = True
                break

        if not connected_to_valid_path:
            # print("Ошибка: Карта должна соединяться с туннелем вашего цвета (от вашего старта).")
            return False

        return True

    def _bfs_reachable_nodes(self, start_pos: Tuple[int, int]) -> Set[Tuple[int, int]]:
        """Возвращает множество координат, до которых можно добраться от start_pos по туннелям."""
        if start_pos not in self.grid:
            return set()

        visited = set()
        queue = [start_pos]
        visited.add(start_pos)

        while queue:
            curr_x, curr_y = queue.pop(0)
            curr_card = self.grid[(curr_x, curr_y)]

            for direction in Direction:
                # Есть ли выход в эту сторону у текущей карты?
                if not curr_card.openings.get_opening(direction):
                    continue

                dx, dy = direction.value
                neighbor_pos = (curr_x + dx, curr_y + dy)

                if neighbor_pos in self.grid and neighbor_pos not in visited:
                    neighbor_card = self.grid[neighbor_pos]
                    opposite_dir = self._get_opposite_dir(direction)

                    # Есть ли вход у соседа с обратной стороны?
                    if neighbor_card.openings.get_opening(opposite_dir):
                        visited.add(neighbor_pos)
                        queue.append(neighbor_pos)

        return visited