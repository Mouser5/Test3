from typing import Dict, Tuple, Optional, Set
from cards import TunnelCard, Direction


class GameBoard:
    def __init__(self):
        self.grid: Dict[Tuple[int, int], TunnelCard] = {}

    def place_card(self, x: int, y: int, card: TunnelCard):
        self.grid[(x, y)] = card

    def remove_card(self, x: int, y:int):
        self.grid.pop((x,y))

    def get_card(self, x: int, y: int) -> Optional[TunnelCard]:
        return self.grid.get((x, y))

    def _get_opposite_dir(self, direction: Direction) -> Direction:
        if direction == Direction.UP: return Direction.DOWN
        if direction == Direction.DOWN: return Direction.UP
        if direction == Direction.LEFT: return Direction.RIGHT
        return Direction.LEFT

    def is_move_valid(self, x: int, y: int, new_card: TunnelCard, player_start_pos: Tuple[int, int],
                      player_color: str) -> bool:
        """
        Обрабатывает два сценария:
        1. Размещение карты туннеля/двери/лестницы на пустую клетку.
        2. Использование КЛЮЧА на клетку с чужой закрытой ДВЕРЬЮ.
        """

        # СЦЕНАРИЙ 2: Использование ключа
        if new_card.is_key:
            target_card = self.grid.get((x, y))
            if not target_card or not target_card.is_door:
                return False

            # Ключом можно открыть только чужую закрытую дверь
            if target_card.color == player_color or not target_card.is_locked:
                return False

                # Проверяем, есть ли к двери путь (BFS должен дойти до координат двери)
            return self._check_path_connectivity(x, y, player_start_pos, player_color)

        if new_card.is_rockfall:
            target_card=self.grid.get((x,y))
            if not target_card or target_card.name.__contains__("Start"):
                # print("Нельзя ломать начальную точку")
                return False
            return True

        # СЦЕНАРИЙ 1: Обычная установка (клетка должна быть пустой)
        if (x, y) in self.grid:
            return False

        has_neighbor = False
        has_tunnel_connection = False
        valid_geometry = True

        self.grid[(x, y)] = new_card

        # 1. Проверка соседей (Geometry check)
        for direction in Direction:
            dx, dy = direction.value
            neighbor_pos = (x + dx, y + dy)
            neighbor_card = self.grid.get(neighbor_pos)

            if neighbor_card:
                has_neighbor = True

                # Правило лестницы: нельзя рядом с золотом/стартом
                if new_card.is_ladder and (neighbor_card.is_gold or neighbor_card.name.__contains__("Start ")):
                    valid_geometry = False
                    break

                my_opening = new_card.openings.get_opening(direction)
                opposite_dir = self._get_opposite_dir(direction)
                neighbor_opening = neighbor_card.openings.get_opening(opposite_dir)

                if not (neighbor_card.is_gold and neighbor_card.gold_value == 0):
                    if my_opening != neighbor_opening:
                        valid_geometry = False
                        break

                # Фикс: карта должна соединяться именно туннелем, а не просто "глухими стенами"
                if my_opening and neighbor_opening:
                    has_tunnel_connection = True

        # Откатываем сетку, если геометрия невалидна или карта вообще ни с чем не стыкуется туннелями
        if not has_neighbor or not valid_geometry or not has_tunnel_connection:
            del self.grid[(x, y)]
            return False

        # 2. Проверка пути (Connectivity check)
        if new_card.is_ladder:
            # Лестнице не нужен непрерывный путь от старта, она сама становится стартом
            del self.grid[(x, y)]
            return True

        is_connected = self._check_path_connectivity(x, y, player_start_pos, player_color)

        del self.grid[(x, y)]
        return is_connected

    def _check_path_connectivity(self, target_x: int, target_y: int, player_start_pos: Tuple[int, int],
                                 player_color: str) -> bool:
        start_nodes = {player_start_pos}
        for pos, card in self.grid.items():
            if card.is_ladder and card.color == player_color and pos != (target_x, target_y):
                start_nodes.add(pos)

        reachable_states = self._bfs_reachable_states(start_nodes, player_color)

        for (rx, ry, _) in reachable_states:
            if rx == target_x and ry == target_y:
                return True

        return False

    def _bfs_reachable_states(self, start_nodes: Set[Tuple[int, int]], player_color: str) -> Set[
        Tuple[int, int, Optional[Direction]]]:
        visited = set()
        queue = []

        for start_pos in start_nodes:
            if start_pos in self.grid:
                state = (start_pos[0], start_pos[1], None)
                visited.add(state)
                queue.append(state)

        while queue:
            curr_x, curr_y, entry_dir = queue.pop(0)
            curr_card = self.grid.get((curr_x, curr_y))
            if not curr_card: continue

            allowed_exits = curr_card.get_exits(entry_dir)

            # [NEW] Логика Дверей
            # Если мы зашли в чужую закрытую дверь, мы обнуляем доступные выходы из неё.
            # Мы можем на неё "встать" (чтобы применить ключ), но пройти сквозь неё дальше нельзя.
            if curr_card.is_door and curr_card.color != player_color and curr_card.is_locked:
                allowed_exits = set()

            for direction in allowed_exits:
                dx, dy = direction.value
                neighbor_pos = (curr_x + dx, curr_y + dy)

                if neighbor_pos in self.grid:
                    neighbor_card = self.grid[neighbor_pos]
                    arrival_side = self._get_opposite_dir(direction)

                    if neighbor_card.openings.get_opening(arrival_side):
                        new_state = (neighbor_pos[0], neighbor_pos[1], arrival_side)
                        if new_state not in visited:
                            visited.add(new_state)
                            queue.append(new_state)
        return visited