from typing import Dict, Tuple, Optional, Set
from cards import Card, PathCard, StartCard, GoldCard, LadderCard, DoorCard, ActionCard, ActionType, Direction

class GameBoard:
    def __init__(self):
        self.grid: Dict[Tuple[int, int], Card] = {}

    def place_card(self, x: int, y: int, card: Card):
        self.grid[(x, y)] = card

    def remove_card(self, x: int, y: int):
        self.grid.pop((x, y), None)

    def get_card(self, x: int, y: int) -> Optional[Card]:
        return self.grid.get((x, y))

    def _get_opposite_dir(self, direction: Direction) -> Direction:
        if direction == Direction.UP: return Direction.DOWN
        if direction == Direction.DOWN: return Direction.UP
        if direction == Direction.LEFT: return Direction.RIGHT
        return Direction.LEFT

    def is_move_valid(self, x: int, y: int, new_card: Card, player_start_pos: Tuple[int, int], player_id: int) -> bool:
        # СЦЕНАРИЙ: Карты действий (Ключ, Обвал)
        if isinstance(new_card, ActionCard):
            target_card = self.grid.get((x, y))
            if not target_card:
                return False

            if new_card.action_type == ActionType.KEY:
                if not isinstance(target_card, DoorCard): return False
                if target_card.door_owner_id == player_id or not target_card.is_locked: return False
                return self._check_path_connectivity(x, y, player_start_pos, player_id)

            if new_card.action_type == ActionType.ROCKFALL:
                if isinstance(target_card, StartCard) or isinstance(target_card, GoldCard): return False
                return True
            return False

        # СЦЕНАРИЙ: Установка туннелей (клетка должна быть пустой)
        if not isinstance(new_card, PathCard) or (x, y) in self.grid:
            return False

        has_neighbor = False
        has_tunnel_connection = False
        valid_geometry = True

        self.grid[(x, y)] = new_card

        # Проверка соседей (Geometry check)
        for direction in Direction:
            dx, dy = direction.value
            neighbor_pos = (x + dx, y + dy)
            neighbor_card = self.grid.get(neighbor_pos)

            if neighbor_card and isinstance(neighbor_card, PathCard):
                has_neighbor = True

                # Правило лестницы: нельзя рядом с золотом/стартом
                if isinstance(new_card, LadderCard) and (isinstance(neighbor_card, GoldCard) or isinstance(neighbor_card, StartCard)):
                    valid_geometry = False
                    break

                my_opening = new_card.openings.get_opening(direction)
                opposite_dir = self._get_opposite_dir(direction)
                neighbor_opening = neighbor_card.openings.get_opening(opposite_dir)

                if not (isinstance(neighbor_card, GoldCard) and not neighbor_card.is_revealed):
                    if my_opening != neighbor_opening:
                        valid_geometry = False
                        break

                if my_opening and neighbor_opening:
                    has_tunnel_connection = True

        if not has_neighbor or not valid_geometry or not has_tunnel_connection:
            del self.grid[(x, y)]
            return False

        # Проверка пути (Connectivity check)
        if isinstance(new_card, LadderCard):
            del self.grid[(x, y)]
            return True

        is_connected = self._check_path_connectivity(x, y, player_start_pos, player_id)
        del self.grid[(x, y)]
        return is_connected

    def _check_path_connectivity(self, target_x: int, target_y: int, player_start_pos: Tuple[int, int], player_id: int) -> bool:
        start_nodes = {player_start_pos}
        for pos, card in self.grid.items():
            if isinstance(card, LadderCard) and card.owner_id == player_id and pos != (target_x, target_y):
                start_nodes.add(pos)

        reachable_states = self._bfs_reachable_states(start_nodes, player_id)
        for (rx, ry, _) in reachable_states:
            if rx == target_x and ry == target_y:
                return True
        return False

    def _bfs_reachable_states(self, start_nodes: Set[Tuple[int, int]], player_id: int) -> Set[Tuple[int, int, Optional[Direction]]]:
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
            if not curr_card or not isinstance(curr_card, PathCard): continue

            allowed_exits = curr_card.get_exits(entry_dir)

            if isinstance(curr_card, DoorCard) and curr_card.door_owner_id != player_id and curr_card.is_locked:
                allowed_exits = set()

            for direction in allowed_exits:
                dx, dy = direction.value
                neighbor_pos = (curr_x + dx, curr_y + dy)

                if neighbor_pos in self.grid:
                    neighbor_card = self.grid[neighbor_pos]
                    if isinstance(neighbor_card, PathCard):
                        arrival_side = self._get_opposite_dir(direction)
                        if neighbor_card.openings.get_opening(arrival_side):
                            new_state = (neighbor_pos[0], neighbor_pos[1], arrival_side)
                            if new_state not in visited:
                                visited.add(new_state)
                                queue.append(new_state)
        return visited