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
        if (x, y) in self.grid:
            return False

        has_neighbor = False
        connected_to_valid_path = False

        # Временно помещаем карту на поле для проверки пути
        self.grid[(x, y)] = new_card

        neighbors_to_check = []

        # 1. Проверка физической стыковки (Geometry check)
        valid_geometry = True
        for direction in Direction:
            dx, dy = direction.value
            neighbor_pos = (x + dx, y + dy)
            neighbor_card = self.grid.get(neighbor_pos)

            if neighbor_card:
                has_neighbor = True
                my_opening = new_card.openings.get_opening(direction)
                opposite_dir = self._get_opposite_dir(direction)
                neighbor_opening = neighbor_card.openings.get_opening(opposite_dir)

                if not (neighbor_card.is_gold and neighbor_card.gold_value == 0):
                    if my_opening != neighbor_opening:
                        valid_geometry = False
                        break  # Сбой стыковки

                # Если физически соединились туннелями
                if my_opening and neighbor_opening:
                    neighbors_to_check.append(neighbor_pos)

        if not has_neighbor or not valid_geometry:
            del self.grid[(x, y)]  # Убираем карту
            return False

        # 2. Проверка пути (Connectivity check)
        # Мы проверяем, доходит ли путь от старта до ЛЮБОГО ВНУТРЕННЕГО ВХОДА новой карты.

        reachable_states = self._bfs_reachable_states(player_start_pos)

        # reachable_states содержит кортежи (x, y, entry_direction)
        # Нам нужно узнать, достигли ли мы карты (x,y)

        for (rx, ry, entry_dir) in reachable_states:
            if rx == x and ry == y:
                connected_to_valid_path = True
                break

        del self.grid[(x, y)]  # Убираем карту после проверки

        if not connected_to_valid_path:
            # print("Нет пути от старта")
            return False

        return True

    def _bfs_reachable_states(self, start_pos: Tuple[int, int]) -> Set[Tuple[int, int, Optional[Direction]]]:
        """
        Возвращает множество состояний (x, y, entry_direction), доступных от старта.
        entry_direction - сторона, через которую мы ВОШЛИ в клетку (x,y).
        Для старта это None.
        """
        if start_pos not in self.grid:
            return set()

        # State: (x, y, entry_side_of_this_card)
        visited = set()
        queue = [(start_pos[0], start_pos[1], None)]
        visited.add((start_pos[0], start_pos[1], None))

        while queue:
            curr_x, curr_y, entry_dir = queue.pop(0)
            curr_card = self.grid.get((curr_x, curr_y))
            if not curr_card: continue

            # Получаем направления, куда можно выйти с учетом того, откуда вошли
            allowed_exits = curr_card.get_exits(entry_dir)

            for direction in allowed_exits:
                dx, dy = direction.value
                neighbor_pos = (curr_x + dx, curr_y + dy)

                if neighbor_pos in self.grid:
                    neighbor_card = self.grid[neighbor_pos]

                    # Сторона соседа, в которую мы стучимся
                    arrival_side = self._get_opposite_dir(direction)

                    # Проверяем, пускает ли сосед (физически открыт ли вход)
                    if neighbor_card.openings.get_opening(arrival_side):
                        new_state = (neighbor_pos[0], neighbor_pos[1], arrival_side)

                        if new_state not in visited:
                            visited.add(new_state)
                            queue.append(new_state)

        return visited

    def _bfs_reachable_nodes(self, start_pos):
        # Обертка для старого кода (если где-то используется),
        # возвращает просто координаты
        states = self._bfs_reachable_states(start_pos)
        return {(s[0], s[1]) for s in states}