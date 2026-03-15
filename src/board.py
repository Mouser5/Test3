from collections import deque
from typing import Dict, Tuple, Optional, Set
from cards import (PathCardTemplate, DoorCardTemplate, Direction)
from state import PlacedCard
from registry import TemplateRegistry


class BoardEngine:
    # Предкомпилированный маппинг направлений для максимальной скорости
    # (избавляет от медленного Enum.value в горячем цикле)
    DIR_OFFSETS = {
        Direction.UP: (0, 1),
        Direction.DOWN: (0, -1),
        Direction.LEFT: (-1, 0),
        Direction.RIGHT: (1, 0)
    }

    def __init__(self, registry: TemplateRegistry):
        self.registry = registry
        # Сохраняем прямую ссылку на словарь шаблонов для O(1) доступа без вызова функций
        self.templates = registry.templates

    @staticmethod
    def get_opposite_dir(direction: Direction) -> Direction:
        if direction == Direction.UP: return Direction.DOWN
        if direction == Direction.DOWN: return Direction.UP
        if direction == Direction.LEFT: return Direction.RIGHT
        return Direction.LEFT

    def _get_effective_opening(self, template: PathCardTemplate, direction: Direction, is_rotated: bool) -> bool:
        check_dir = self.get_opposite_dir(direction) if is_rotated else direction
        return template.openings.get_opening(check_dir)

    def _get_effective_exits(self, template: PathCardTemplate, entry_from: Optional[Direction],
                             is_rotated: bool) -> frozenset:
        # Корректируем точку входа, если карта повернута
        eff_entry = self.get_opposite_dir(entry_from) if (is_rotated and entry_from) else entry_from
        base_exits = template.get_exits(eff_entry)

        if not is_rotated:
            return base_exits

        # Если карта повернута на 180 градусов, выходы инвертируются
        rotated_exits = set()
        for ext in base_exits:
            rotated_exits.add(self.get_opposite_dir(ext))
        return frozenset(rotated_exits)

    def get_player_frontier(self, start_pos: Tuple[int, int], player_id: int,
                            board_state: Dict[Tuple[int, int], PlacedCard],
                            ladders: Set[Tuple[int, int]]) -> Set[Tuple[int, int]]:
        """
        Возвращает координаты пустых клеток (frontier), куда игрок `player_id` может выложить туннель.
        Вся работа ведется ИСКЛЮЧИТЕЛЬНО с кортежами (int, int).
        """
        frontier = set()
        visited = set()

        # Стартуем поиск от начальной позиции И от всех лестниц, которые есть у игрока
        queue = deque()
        start_nodes = [start_pos] + list(ladders)
        for sp in start_nodes:
            if sp in board_state:
                queue.append((sp[0], sp[1], None))

        while queue:
            curr_x, curr_y, entry_dir = queue.popleft()
            curr_pos = (curr_x, curr_y)

            if curr_pos not in board_state:
                frontier.add(curr_pos)
                continue

            curr_placed = board_state[curr_pos]
            # МИКРО-ОПТИМИЗАЦИЯ: Прямое чтение из словаря (без .get())
            curr_template = self.templates[curr_placed.template_id]

            if not isinstance(curr_template, PathCardTemplate):
                continue

            # Проверка закрытых дверей оппонента
            if isinstance(curr_template,
                          DoorCardTemplate) and curr_template.door_owner_id != player_id and curr_placed.is_locked:
                continue

            allowed_exits = self._get_effective_exits(curr_template, entry_dir, curr_placed.is_rotated_180)

            for direction in allowed_exits:
                # МИКРО-ОПТИМИЗАЦИЯ: Доступ к кортежам смещений напрямую
                dx, dy = self.DIR_OFFSETS[direction]
                nx, ny = curr_x + dx, curr_y + dy
                neighbor_pos = (nx, ny)

                if neighbor_pos not in board_state:
                    frontier.add(neighbor_pos)
                else:
                    neighbor_placed = board_state[neighbor_pos]
                    # МИКРО-ОПТИМИЗАЦИЯ: Прямое чтение из словаря
                    neighbor_template = self.templates[neighbor_placed.template_id]

                    if isinstance(neighbor_template, PathCardTemplate):
                        arrival_side = self.get_opposite_dir(direction)
                        if self._get_effective_opening(neighbor_template, arrival_side, neighbor_placed.is_rotated_180):
                            new_state = (nx, ny, arrival_side)
                            if new_state not in visited:
                                visited.add(new_state)
                                queue.append(new_state)

        return frontier

    def is_move_valid(self, x: int, y: int, template_id: str, is_rotated_180: bool, start_pos: Tuple[int, int],
                      player_id: int, board_state: Dict[Tuple[int, int], PlacedCard],
                      ladders: Set[Tuple[int, int]], skip_path_check: bool = False) -> bool:

        target_pos = (x, y)
        if target_pos in board_state:
            return False

        template = self.templates[template_id]
        if not isinstance(template, PathCardTemplate):
            return False

        has_any_neighbor = False

        # ОПТИМИЗАЦИЯ: избегаем создания итератора Enum
        for direction in (Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT):
            dx, dy = self.DIR_OFFSETS[direction]
            nx, ny = x + dx, y + dy
            neighbor_pos = (nx, ny)

            if neighbor_pos in board_state:
                neighbor_placed = board_state[neighbor_pos]
                neighbor_template = self.templates[neighbor_placed.template_id]

                if not isinstance(neighbor_template, PathCardTemplate):
                    continue

                has_any_neighbor = True

                my_opening = self._get_effective_opening(template, direction, is_rotated_180)
                arrival_side = self.get_opposite_dir(direction)
                their_opening = self._get_effective_opening(neighbor_template, arrival_side,
                                                            neighbor_placed.is_rotated_180)

                if my_opening != their_opening:
                    return False

        if not has_any_neighbor:
            return False

        if skip_path_check:
            return True

        frontier = self.get_player_frontier(start_pos, player_id, board_state, ladders)
        return target_pos in frontier

    def check_path_connectivity(self, target_x: int, target_y: int, start_pos: Tuple[int, int],
                                player_id: int, board_state: Dict[Tuple[int, int], PlacedCard],
                                ladders: Set[Tuple[int, int]]) -> bool:
        """
        Проверяет, есть ли непрерывный путь от стартовой карты до целевой координаты.
        Используется для проверки того, может ли игрок открыть дверь ключом.
        """
        visited = set()
        queue = deque()

        start_nodes = [start_pos] + list(ladders)
        for sp in start_nodes:
            if sp in board_state:
                queue.append((sp[0], sp[1], None))

        while queue:
            curr_x, curr_y, entry_dir = queue.popleft()
            curr_pos = (curr_x, curr_y)

            if curr_pos == (target_x, target_y):
                return True

            if curr_pos not in board_state:
                continue

            curr_placed = board_state[curr_pos]
            # МИКРО-ОПТИМИЗАЦИЯ
            curr_template = self.templates[curr_placed.template_id]

            if not isinstance(curr_template, PathCardTemplate):
                continue

            # Двери оппонента блокируют путь
            if curr_pos != (target_x, target_y) and isinstance(curr_template, DoorCardTemplate):
                if curr_template.door_owner_id != player_id and curr_placed.is_locked:
                    continue

            allowed_exits = self._get_effective_exits(curr_template, entry_dir, curr_placed.is_rotated_180)

            for direction in allowed_exits:
                # МИКРО-ОПТИМИЗАЦИЯ
                dx, dy = self.DIR_OFFSETS[direction]
                nx, ny = curr_x + dx, curr_y + dy
                neighbor_pos = (nx, ny)

                if neighbor_pos in board_state:
                    neighbor_placed = board_state[neighbor_pos]
                    neighbor_template = self.templates[neighbor_placed.template_id]

                    if isinstance(neighbor_template, PathCardTemplate):
                        arrival_side = self.get_opposite_dir(direction)
                        if self._get_effective_opening(neighbor_template, arrival_side, neighbor_placed.is_rotated_180):
                            new_state = (nx, ny, arrival_side)
                            if new_state not in visited:
                                visited.add(new_state)
                                queue.append(new_state)

        return False