from collections import deque
from typing import Dict, Tuple, Optional, Set, Union
from cards import (
    PathCardTemplate,
    StartCardTemplate,
    GoldCardTemplate,
    LadderCardTemplate,
    DoorCardTemplate,
    ActionCardTemplate,
    ActionType,
    Direction,
)
from state import PlacedCard
from registry import TemplateRegistry


class BoardEngine:
    def __init__(self, registry: TemplateRegistry):
        self.registry = registry

    @staticmethod
    def coord_to_str(x: int, y: int) -> str:
        return f"{x},{y}"

    @staticmethod
    def str_to_coord(coord_str: str) -> Tuple[int, int]:
        p = coord_str.split(",")
        return int(p[0]), int(p[1])

    @staticmethod
    def get_opposite_dir(direction: Direction) -> Direction:
        if direction == Direction.UP:
            return Direction.DOWN
        if direction == Direction.DOWN:
            return Direction.UP
        if direction == Direction.LEFT:
            return Direction.RIGHT
        return Direction.LEFT

    def _get_effective_opening(
        self, template: PathCardTemplate, direction: Direction, is_rotated: bool
    ) -> bool:
        check_dir = self.get_opposite_dir(direction) if is_rotated else direction
        return template.openings.get_opening(check_dir)

    def _get_effective_exits(
        self,
        template: PathCardTemplate,
        entry_from: Optional[Direction],
        is_rotated: bool,
    ) -> Set[Direction]:
        effective_entry = (
            self.get_opposite_dir(entry_from)
            if (is_rotated and entry_from)
            else entry_from
        )
        exits = template.get_exits(effective_entry)
        if is_rotated:
            return {self.get_opposite_dir(d) for d in exits}
        return set(exits)

    def is_move_valid(
        self,
        x: int,
        y: int,
        placed_card: PlacedCard,
        player_start_pos: Tuple[int, int],
        player_id: int,
        board_state: Dict[str, PlacedCard],
        player_ladders: Set[str],
        skip_path_check: bool = False,
    ) -> bool:
        template = self.registry.get(placed_card.template_id)
        coord_key = self.coord_to_str(x, y)

        if isinstance(template, ActionCardTemplate):
            target_placed = board_state.get(coord_key)
            if not target_placed:
                return False
            target_template = self.registry.get(target_placed.template_id)

            if template.action_type == ActionType.KEY:
                if not isinstance(target_template, DoorCardTemplate):
                    return False
                if (
                    target_template.door_owner_id == player_id
                    or not target_placed.is_locked
                ):
                    return False
                # Ключ применяется на поле, тут всё равно нужен BFS, чтобы проверить,
                # дошел ли игрок до двери (если это не вызов с фронтира)
                if skip_path_check:
                    return True
                return self.check_path_connectivity(
                    x, y, player_start_pos, player_id, board_state, player_ladders
                )

            if template.action_type == ActionType.ROCKFALL:
                if isinstance(target_template, (StartCardTemplate, GoldCardTemplate)):
                    return False
                return True
            return False

        if not isinstance(template, PathCardTemplate) or coord_key in board_state:
            return False

        has_neighbor = False
        has_tunnel_connection = False
        valid_geometry = True

        for direction in Direction:
            dx, dy = direction.value
            nx, ny = x + dx, y + dy
            neighbor_key = self.coord_to_str(nx, ny)
            neighbor_placed = board_state.get(neighbor_key)

            if neighbor_placed:
                neighbor_template = self.registry.get(neighbor_placed.template_id)
                if isinstance(neighbor_template, PathCardTemplate):
                    has_neighbor = True

                    if isinstance(template, LadderCardTemplate) and isinstance(
                        neighbor_template, (GoldCardTemplate, StartCardTemplate)
                    ):
                        valid_geometry = False
                        break

                    my_opening = self._get_effective_opening(
                        template, direction, placed_card.is_rotated_180
                    )
                    opposite_dir = self.get_opposite_dir(direction)
                    neighbor_opening = self._get_effective_opening(
                        neighbor_template, opposite_dir, neighbor_placed.is_rotated_180
                    )

                    is_hidden_gold = (
                        isinstance(neighbor_template, GoldCardTemplate)
                        and not neighbor_placed.is_revealed
                    )

                    if not is_hidden_gold:
                        if my_opening != neighbor_opening:
                            valid_geometry = False
                            break

                    if my_opening and neighbor_opening:
                        has_tunnel_connection = True

        if not has_neighbor or not valid_geometry or not has_tunnel_connection:
            return False

        # --- ИСПРАВЛЕНИЕ: Ранний выход за O(1) ---
        if isinstance(template, LadderCardTemplate) or skip_path_check:
            return True

        return self.check_path_connectivity(
            target_x=x,
            target_y=y,
            player_start_pos=player_start_pos,
            player_id=player_id,
            board_state=board_state,
            player_ladders=player_ladders,
            hypo_pos=(x, y),
            hypo_card=placed_card,
        )

    def check_path_connectivity(
        self,
        target_x: int,
        target_y: int,
        player_start_pos: Tuple[int, int],
        player_id: int,
        board_state: Dict[str, PlacedCard],
        player_ladders: Set[str],
        hypo_pos: Optional[Tuple[int, int]] = None,
        hypo_card: Optional[PlacedCard] = None,
    ) -> bool:
        start_nodes = {player_start_pos}

        # ИСПРАВЛЕНИЕ O(N): Извлекаем лестницы за O(1)
        for pos_str in player_ladders:
            nx, ny = self.str_to_coord(pos_str)
            if (nx, ny) != (target_x, target_y):
                start_nodes.add((nx, ny))

        # Если гипотетический ход - это лестница, добавляем её!
        if hypo_pos and hypo_card:
            hypo_tpl = self.registry.get(hypo_card.template_id)
            if (
                isinstance(hypo_tpl, LadderCardTemplate)
                and hypo_card.owner_id == player_id
            ):
                if hypo_pos != (target_x, target_y):
                    start_nodes.add(hypo_pos)

        reachable = self.bfs_reachable_states(
            start_nodes,
            player_id,
            board_state,
            hypo_pos=hypo_pos,
            hypo_card=hypo_card,
            target_coord=(target_x, target_y),
        )

        if reachable is True:
            return True
        for rx, ry, _ in reachable:
            if rx == target_x and ry == target_y:
                return True
        return False

    def bfs_reachable_states(
        self,
        start_nodes: Set[Tuple[int, int]],
        player_id: int,
        board_state: Dict[str, PlacedCard],
        hypo_pos: Optional[Tuple[int, int]] = None,
        hypo_card: Optional[PlacedCard] = None,
        target_coord: Optional[Tuple[int, int]] = None,
    ) -> Union[Set[Tuple[int, int, Optional[Direction]]], bool]:
        visited = set()
        queue = deque()

        for sx, sy in start_nodes:
            if self.coord_to_str(sx, sy) in board_state or (
                hypo_pos and (sx, sy) == hypo_pos
            ):
                state = (sx, sy, None)
                visited.add(state)
                queue.append(state)

        while queue:
            curr_x, curr_y, entry_dir = queue.popleft()

            if target_coord and (curr_x, curr_y) == target_coord:
                return True

            if hypo_pos and (curr_x, curr_y) == hypo_pos:
                curr_placed = hypo_card
            else:
                curr_placed = board_state.get(self.coord_to_str(curr_x, curr_y))

            if not curr_placed:
                continue

            curr_template = self.registry.get(curr_placed.template_id)
            if not isinstance(curr_template, PathCardTemplate):
                continue

            if isinstance(curr_template, DoorCardTemplate):
                if curr_template.door_owner_id != player_id and curr_placed.is_locked:
                    continue

            allowed_exits = self._get_effective_exits(
                curr_template, entry_dir, curr_placed.is_rotated_180
            )

            for direction in allowed_exits:
                dx, dy = direction.value
                nx, ny = curr_x + dx, curr_y + dy

                if hypo_pos and (nx, ny) == hypo_pos:
                    neighbor_placed = hypo_card
                else:
                    neighbor_placed = board_state.get(self.coord_to_str(nx, ny))

                if neighbor_placed:
                    neighbor_template = self.registry.get(neighbor_placed.template_id)
                    if isinstance(neighbor_template, PathCardTemplate):
                        arrival_side = self.get_opposite_dir(direction)
                        if self._get_effective_opening(
                            neighbor_template,
                            arrival_side,
                            neighbor_placed.is_rotated_180,
                        ):
                            new_state = (nx, ny, arrival_side)
                            if new_state not in visited:
                                visited.add(new_state)
                                queue.append(new_state)
        return visited

    def get_player_frontier(
        self,
        player_start_pos: Tuple[int, int],
        player_id: int,
        board_state: Dict[str, PlacedCard],
        player_ladders: Set[str],
    ) -> Set[Tuple[int, int]]:
        """
        Возвращает фронтир: множество пустых координат, смежных с открытыми выходами сети игрока.
        Один вызов этого метода заменяет сотни проверок is_move_valid.
        """
        frontier = set()
        start_nodes = {player_start_pos}
        for pos_str in player_ladders:
            start_nodes.add(self.str_to_coord(pos_str))

        visited = set()
        queue = deque()

        for sx, sy in start_nodes:
            if self.coord_to_str(sx, sy) in board_state:
                state = (sx, sy, None)
                visited.add(state)
                queue.append(state)

        while queue:
            curr_x, curr_y, entry_dir = queue.popleft()
            curr_placed = board_state.get(self.coord_to_str(curr_x, curr_y))
            if not curr_placed:
                continue

            curr_template = self.registry.get(curr_placed.template_id)
            if not isinstance(curr_template, PathCardTemplate):
                continue
            if (
                isinstance(curr_template, DoorCardTemplate)
                and curr_template.door_owner_id != player_id
                and curr_placed.is_locked
            ):
                continue

            allowed_exits = self._get_effective_exits(
                curr_template, entry_dir, curr_placed.is_rotated_180
            )

            for direction in allowed_exits:
                dx, dy = direction.value
                nx, ny = curr_x + dx, curr_y + dy
                neighbor_key = self.coord_to_str(nx, ny)

                if neighbor_key not in board_state:
                    # Клетка пуста и физически доступна из сети игрока!
                    frontier.add((nx, ny))
                else:
                    neighbor_placed = board_state[neighbor_key]
                    neighbor_template = self.registry.get(neighbor_placed.template_id)
                    if isinstance(neighbor_template, PathCardTemplate):
                        arrival_side = self.get_opposite_dir(direction)
                        if self._get_effective_opening(
                            neighbor_template,
                            arrival_side,
                            neighbor_placed.is_rotated_180,
                        ):
                            new_state = (nx, ny, arrival_side)
                            if new_state not in visited:
                                visited.add(new_state)
                                queue.append(new_state)
        return frontier
