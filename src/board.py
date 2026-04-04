from collections import deque
from typing import Dict, Tuple, Optional, Set, Union
from cards import (
    PathCardTemplate, DoorCardTemplate, LadderCardTemplate,
    GoldCardTemplate, ActionCardTemplate, ActionType, Direction
)
from state import PlacedCard
from registry import TemplateRegistry


class BoardEngine:
    """Движок для работы с доской - валидация ходов и BFS."""

    # ⬇️ МИКРО-ОПТИМИЗАЦИЯ: предкомпилированные направления
    DIR_OFFSETS = {
        Direction.UP: (0, 1),
        Direction.DOWN: (0, -1),
        Direction.LEFT: (-1, 0),
        Direction.RIGHT: (1, 0)
    }

    def __init__(self, registry: TemplateRegistry):
        self.registry = registry
        # ⬇️ ПРЯМОЙ ДОСТУП к шаблонам (O(1) без вызова функции)
        self.templates = registry.templates

    # ⬇️ УДАЛЕНЫ coord_to_str и str_to_coord - не нужны!
    # Мы используем кортежи везде

    @staticmethod
    def get_opposite_dir(direction: Direction) -> Direction:
        """Возвращает противоположное направление."""
        if direction == Direction.UP: return Direction.DOWN
        if direction == Direction.DOWN: return Direction.UP
        if direction == Direction.LEFT: return Direction.RIGHT
        return Direction.LEFT

    def _get_effective_opening(self, template: PathCardTemplate,
                               direction: Direction, is_rotated: bool) -> bool:
        """Проверяет, есть ли отверстие в направлении (с учётом поворота)."""
        check_dir = self.get_opposite_dir(direction) if is_rotated else direction
        return template.openings.get_opening(check_dir)

    def _get_effective_exits(self, template: PathCardTemplate,
                             entry_from: Optional[Direction],
                             is_rotated: bool) -> frozenset:
        """Возвращает выходы из карты (с учётом входа и поворота)."""
        # ⬇️ Вычисляем эффективный вход (инвертируем при повороте)
        eff_entry = self.get_opposite_dir(entry_from) if (is_rotated and entry_from) else entry_from
        base_exits = template.get_exits(eff_entry)

        if not is_rotated:
            return base_exits

        # ⬇️ При повороте на 180° инвертируем все выходы
        rotated_exits = set()
        for ext in base_exits:
            rotated_exits.add(self.get_opposite_dir(ext))
        return frozenset(rotated_exits)

    # ⬇️ ГЛАВНОЕ ОТЛИЧИЕ: сигнатура методов

    def is_move_valid(
            self,
            x: int, y: int,  # Координаты (не кортеж!)
            template_id: str,  # ID шаблона (не PlacedCard!)
            is_rotated_180: bool,  # Поворот отдельно
            start_pos: Tuple[int, int],  # Стартовая позиция как кортеж
            player_id: int,  # ID игрока
            board_state: Dict[Tuple[int, int], PlacedCard],  # Доска с кортежами!
            player_ladders: Set[Tuple[int, int]],  # Лестницы как кортежи!
            skip_path_check: bool = False
    ) -> bool:
        """
        Проверяет, может ли игрок построить карту на позицию (x, y).

        Правила:
        1. На позиции не должно быть карты
        2. Должна быть соседняя карта (сосед по пути)
        3. Отверстия должны совпадать
        4. Путь должен быть доступен из стартовой позиции
        """
        target_pos = (x, y)

        # Проверка 1: позиция свободна?
        if target_pos in board_state:
            return False

        template = self.templates[template_id]

        # ⬇️ Проверка специальных типов (действия на поле)
        if isinstance(template, ActionCardTemplate):
            # Для действий на поле нужна целевая карта
            return self._validate_board_utility(
                x, y, template_id, player_id, board_state, player_ladders
            )

        # Проверка 2: это путь?
        if not isinstance(template, PathCardTemplate):
            return False

        has_neighbor = False

        # ⬇️ Проверяем всех 4 сос��дей
        for direction in [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]:
            dx, dy = self.DIR_OFFSETS[direction]
            nx, ny = x + dx, y + dy
            neighbor_pos = (nx, ny)

            if neighbor_pos in board_state:
                neighbor_placed = board_state[neighbor_pos]
                neighbor_template = self.templates[neighbor_placed.template_id]

                if not isinstance(neighbor_template, PathCardTemplate):
                    continue

                has_neighbor = True

                # ⬇️ Проверяем совпадение отверстий
                my_opening = self._get_effective_opening(template, direction, is_rotated_180)
                arrival_side = self.get_opposite_dir(direction)
                their_opening = self._get_effective_opening(
                    neighbor_template, arrival_side, neighbor_placed.is_rotated_180
                )

                if my_opening != their_opening:
                    return False

        # Проверка 3: есть ли сосед?
        if not has_neighbor:
            return False

        # Проверка 4: путь доступен?
        if skip_path_check:
            return True

        return self.check_path_connectivity(
            target_pos, start_pos, player_id, board_state, player_ladders,
            hypo_pos=target_pos, hypo_card=PlacedCard(template_id, owner_id=player_id, is_rotated_180=is_rotated_180)
        )

    def check_path_connectivity(
            self,
            target_pos: Tuple[int, int],
            start_pos: Tuple[int, int],
            player_id: int,
            board_state: Dict[Tuple[int, int], PlacedCard],
            player_ladders: Set[Tuple[int, int]],
            hypo_pos: Optional[Tuple[int, int]] = None,
            hypo_card: Optional[PlacedCard] = None
    ) -> bool:
        """
        Проверяет, есть ли путь от стартовой позиции до целевой.
        Поддерживает гипотетические карты (для MCTS симуляций).
        """
        # Стартовые узлы: стартовая позиция + все лестницы
        start_nodes = {start_pos}
        start_nodes.update(player_ladders)

        # ⬇️ Если гипотетический ход - лестница, добавляем её
        if hypo_pos and hypo_card:
            hypo_tpl = self.templates[hypo_card.template_id]
            if isinstance(hypo_tpl, LadderCardTemplate) and hypo_card.owner_id == player_id:
                if hypo_pos != target_pos:
                    start_nodes.add(hypo_pos)

        reachable = self.bfs_reachable(
            start_nodes, player_id, board_state, hypo_pos, hypo_card, target_pos
        )

        # ⬇️ Быстрая проверка: целевая позиция доступна?
        return target_pos in reachable

    def bfs_reachable(
            self,
            start_nodes: Set[Tuple[int, int]],
            player_id: int,
            board_state: Dict[Tuple[int, int], PlacedCard],
            hypo_pos: Optional[Tuple[int, int]] = None,
            hypo_card: Optional[PlacedCard] = None,
            target_coord: Optional[Tuple[int, int]] = None
    ) -> Set[Tuple[int, int]]:
        """
        BFS: находит все доступные позиции от стартовых узлов.
        Состояние: (x, y, entry_direction) - откуда пришли.
        """
        visited = set()
        queue = deque()

        # Инициализация: добавляем стартовые узлы
        for sx, sy in start_nodes:
            if (sx, sy) in board_state or (hypo_pos and (sx, sy) == hypo_pos):
                state = (sx, sy, None)
                visited.add(state)
                queue.append(state)

        reachable_coords = set()

        while queue:
            curr_x, curr_y, entry_dir = queue.popleft()
            curr_pos = (curr_x, curr_y)

            # ⬇️ Быстрый выход, если нашли цель
            if target_coord and curr_pos == target_coord:
                return {target_coord}  # Ранний выход

            reachable_coords.add(curr_pos)

            # ⬇️ Получаем карту (из доски или гипотезы)
            if hypo_pos and curr_pos == hypo_pos:
                curr_placed = hypo_card
            else:
                curr_placed = board_state.get(curr_pos)

            if not curr_placed:
                continue

            curr_template = self.templates[curr_placed.template_id]

            # ⬇️ Проверяем тип карты
            if not isinstance(curr_template, PathCardTemplate):
                continue

            # ⬇️ Проверяем закрытые двери
            if isinstance(curr_template, DoorCardTemplate):
                if curr_template.door_owner_id != player_id and curr_placed.is_locked:
                    continue

            allowed_exits = self._get_effective_exits(
                curr_template, entry_dir, curr_placed.is_rotated_180
            )

            # ⬇️ Проверяем всех соседей
            for direction in allowed_exits:
                dx, dy = self.DIR_OFFSETS[direction]
                nx, ny = curr_x + dx, curr_y + dy
                neighbor_pos = (nx, ny)

                # ⬇️ Получаем карту соседа
                if hypo_pos and neighbor_pos == hypo_pos:
                    neighbor_placed = hypo_card
                else:
                    neighbor_placed = board_state.get(neighbor_pos)

                if neighbor_placed:
                    neighbor_template = self.templates[neighbor_placed.template_id]
                    if isinstance(neighbor_template, PathCardTemplate):
                        arrival_side = self.get_opposite_dir(direction)
                        if self._get_effective_opening(
                                neighbor_template, arrival_side, neighbor_placed.is_rotated_180
                        ):
                            new_state = (nx, ny, arrival_side)
                            if new_state not in visited:
                                visited.add(new_state)
                                queue.append(new_state)

        return reachable_coords

    def get_player_frontier(
            self,
            start_pos: Tuple[int, int],
            player_id: int,
            board_state: Dict[Tuple[int, int], PlacedCard],
            ladders: Set[Tuple[int, int]]
    ) -> Set[Tuple[int, int]]:
        """
        Возвращает ФРОНТИР: множество пустых координат, где можно строить.

        Один вызов этого метода заменяет сотни проверок is_move_valid!
        Сложность: O(N) где N - размер доски.
        """
        frontier = set()
        visited = set()
        queue = deque()

        # Стартуем от стартовой позиции и всех лестниц
        start_nodes = {start_pos}
        start_nodes.update(ladders)

        for sx, sy in start_nodes:
            if (sx, sy) in board_state:
                state = (sx, sy, None)
                visited.add(state)
                queue.append(state)

        while queue:
            curr_x, curr_y, entry_dir = queue.popleft()
            curr_pos = (curr_x, curr_y)

            if curr_pos not in board_state:
                frontier.add(curr_pos)
                continue

            curr_placed = board_state[curr_pos]
            curr_template = self.templates[curr_placed.template_id]

            if not isinstance(curr_template, PathCardTemplate):
                continue

            # ⬇️ Закрытые двери блокируют путь
            if isinstance(curr_template, DoorCardTemplate):
                if curr_template.door_owner_id != player_id and curr_placed.is_locked:
                    continue

            allowed_exits = self._get_effective_exits(
                curr_template, entry_dir, curr_placed.is_rotated_180
            )

            for direction in allowed_exits:
                dx, dy = self.DIR_OFFSETS[direction]
                nx, ny = curr_x + dx, curr_y + dy
                neighbor_pos = (nx, ny)

                if neighbor_pos not in board_state:
                    frontier.add(neighbor_pos)
                else:
                    neighbor_placed = board_state[neighbor_pos]
                    neighbor_template = self.templates[neighbor_placed.template_id]

                    if isinstance(neighbor_template, PathCardTemplate):
                        arrival_side = self.get_opposite_dir(direction)
                        if self._get_effective_opening(
                                neighbor_template, arrival_side, neighbor_placed.is_rotated_180
                        ):
                            new_state = (nx, ny, arrival_side)
                            if new_state not in visited:
                                visited.add(new_state)
                                queue.append(new_state)

        return frontier

    def _validate_board_utility(self, x: int, y: int, template_id: str,
                                player_id: int, board_state: Dict[Tuple[int, int], PlacedCard],
                                player_ladders: Set[Tuple[int, int]]) -> bool:
        """Валидация действий на поле (ключ, обвал, карта сокровищ)."""
        # ... деталь реализации ...
        return True