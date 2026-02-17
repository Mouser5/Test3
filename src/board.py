from typing import Dict, Tuple, Optional, Set, List
from cards import TunnelCard, Direction, ConsoleColor


class GameBoard:
    def __init__(self):
        self.grid: Dict[Tuple[int, int], TunnelCard] = {}  #

    def place_card(self, x: int, y: int, card: TunnelCard):
        self.grid[(x, y)] = card

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
        Обновленная валидация:
        1. Клетка свободна.
        2. Стыковка с соседями.
        3. Лестница: НЕЛЬЗЯ рядом с золотом, МОЖНО без пути к старту (если есть любой сосед).
        4. Обычная карта: МОЖНО, если есть путь от (Старта ИЛИ Любой Лестницы игрока).
        """
        if (x, y) in self.grid:
            return False

        has_neighbor = False
        connected_to_valid_path = False

        # Временно ставим карту для проверки
        self.grid[(x, y)] = new_card

        neighbors_to_check = []
        valid_geometry = True

        # 1. Проверка соседей (Geometry check + Gold check for Ladder)
        for direction in Direction:
            dx, dy = direction.value
            neighbor_pos = (x + dx, y + dy)
            neighbor_card = self.grid.get(neighbor_pos)

            if neighbor_card:
                has_neighbor = True

                # [NEW] ПРАВИЛО ЛЕСТНИЦЫ: Нельзя ставить рядом с золотом (открытым или закрытым)
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

                if my_opening and neighbor_opening:
                    neighbors_to_check.append(neighbor_pos)

        if not has_neighbor or not valid_geometry:
            del self.grid[(x, y)]
            return False

        # 2. Проверка пути (Connectivity check)

        # Если это лестница, и она имеет соседа (has_neighbor True и geometry валидна),
        # то ей не нужно проверять путь до старта. Она сама становится стартом.
        if new_card.is_ladder:
            del self.grid[(x, y)]
            return True

        # Если обычная карта - ищем путь от Старта ИЛИ от Лестниц игрока
        start_nodes = {player_start_pos}

        # [NEW] Добавляем все существующие лестницы этого игрока как стартовые точки
        for pos, card in self.grid.items():
            # Проверяем, что это лестница И она принадлежит текущему игроку (по цвету)
            # Примечание: предполагается, что цвет карты совпадает с цветом игрока
            if card.is_ladder and card.color == player_color and pos != (x, y):
                start_nodes.add(pos)

        # Запускаем BFS от всех стартовых точек (Multi-source BFS)
        reachable_states = self._bfs_reachable_states(start_nodes)

        # Проверяем, достигли ли мы новой карты
        # reachable_states содержит (x, y, entry_direction)
        for (rx, ry, _) in reachable_states:
            if rx == x and ry == y:
                connected_to_valid_path = True
                break

        del self.grid[(x, y)]

        return connected_to_valid_path

    def _bfs_reachable_states(self, start_nodes: Set[Tuple[int, int]]) -> Set[Tuple[int, int, Optional[Direction]]]:
        """
        BFS с поддержкой множества стартовых точек.
        start_nodes: множество координат (x, y), откуда начинается путь (Старт + Лестницы).
        """
        visited = set()
        queue = []

        # Инициализация очереди
        for start_pos in start_nodes:
            if start_pos in self.grid:
                # Начальное состояние: мы "внутри" карты, entry_dir=None
                state = (start_pos[0], start_pos[1], None)
                visited.add(state)
                queue.append(state)

        while queue:
            curr_x, curr_y, entry_dir = queue.pop(0)
            curr_card = self.grid.get((curr_x, curr_y))
            if not curr_card: continue

            allowed_exits = curr_card.get_exits(entry_dir)

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

    def _bfs_reachable_nodes(self, start_pos):
        # Обертка для совместимости (если нужна)
        states = self._bfs_reachable_states({start_pos})
        return {(s[0], s[1]) for s in states}