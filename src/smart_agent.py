import random
import logging
from typing import Optional, List, Dict, Tuple, Set

from game import Game
from actions import (
    AgentAction, ActionBuild, ActionPlayBoardUtility, ActionPlayPlayerUtility, ActionDiscard
)
from cards import (
    ActionType, EquipmentType, GoldCardTemplate,
    TunnelCardTemplate, DoorCardTemplate, LadderCardTemplate, Direction
)
from registry import REGISTRY
from board import BoardEngine


class SmartAgent:
    def __init__(self, player_id: int):
        self.player_id = player_id
        self.logger = logging.getLogger(f"{__name__}_{player_id}")

    def _equipment_priority(self, equipment: EquipmentType) -> int:
        return {
            EquipmentType.LAMP: 3,
            EquipmentType.CART: 2,
            EquipmentType.PICKAXE: 1,
        }.get(equipment, 0)

    def _count_openings(self, tpl) -> int:
        if hasattr(tpl, "openings"):
            return sum([tpl.openings.up, tpl.openings.down, tpl.openings.left, tpl.openings.right])
        return 0

    def _get_unrevealed_gold(self, game: Game) -> List[Dict[str, object]]:
        player_state = game.state.players[self.player_id]
        gold_targets = []
        for coord_key, placed in game.state.board.items():
            tpl = REGISTRY.get(placed.template_id)
            if isinstance(tpl, GoldCardTemplate) and not placed.is_revealed:
                gx, gy = BoardEngine.str_to_coord(coord_key)
                gold_targets.append({
                    "coord": (gx, gy),
                    "value": tpl.gold_value,
                    "known": coord_key in player_state.known_secrets,
                    "coord_key": coord_key,
                })
        return gold_targets

    def _get_frontier(self, game: Game) -> Set[Tuple[int, int]]:
        player_state = game.state.players[self.player_id]
        return game.board_engine.get_player_frontier(
            game.start_positions[self.player_id], self.player_id, game.state.board, player_state.ladders
        )

    def _is_winning_build(self, game: Game, action: ActionBuild, gold_targets: List[Dict]) -> bool:
        """Проверяет, является ли этот ход последним шагом к открытию золота."""
        player_state = game.state.players[self.player_id]
        t_id = player_state.card_id_to_template.get(action.template_id)
        if not t_id: return False
        tpl = REGISTRY.get(t_id)

        for target in gold_targets:
            gx, gy = target["coord"]
            dx, dy = gx - action.x, gy - action.y

            # Если карта ставится вплотную к золоту (дистанция Манхэттена = 1)
            if abs(dx) + abs(dy) == 1:
                # Определяем, с какой стороны золото от устанавливаемой карты
                direction = None
                if dx == 0 and dy == 1:
                    direction = Direction.UP
                elif dx == 0 and dy == -1:
                    direction = Direction.DOWN
                elif dx == -1 and dy == 0:
                    direction = Direction.LEFT
                elif dx == 1 and dy == 0:
                    direction = Direction.RIGHT

                # Проверяем, есть ли выход в эту сторону у нашей карты
                if direction and game.board_engine._get_effective_opening(tpl, direction, action.is_rotated_180):
                    return True
        return False

    def choose_action(self, game: Game) -> Optional[AgentAction]:
        legal_actions = game.get_legal_actions()
        if not legal_actions:
            return None

        opponent_id = 1 - self.player_id
        player_state = game.state.players[self.player_id]
        opponent_state = game.state.players[opponent_id]

        def _get_tpl(card_id):
            t_id = player_state.card_id_to_template.get(card_id)
            return REGISTRY.get(t_id) if t_id else None

        # ==========================================
        # ПРИОРИТЕТ 1: РЕМОНТ (Если сломан, строить нельзя)
        # ==========================================
        if player_state.broken_equipments:
            repair_actions = [
                a for a in legal_actions
                if isinstance(a, ActionPlayPlayerUtility) and a.target_player_id == self.player_id
                   and getattr(_get_tpl(a.template_id), "action_type", None) == ActionType.REPAIR
            ]
            if repair_actions:
                return random.choice(repair_actions)

        # ==========================================
        # ПРИОРИТЕТ 2: ФАТАЛИТИ (Один шаг до золота)
        # ==========================================
        build_actions = [a for a in legal_actions if isinstance(a, ActionBuild)]
        gold_targets = self._get_unrevealed_gold(game)

        winning_builds = [a for a in build_actions if self._is_winning_build(game, a, gold_targets)]
        if winning_builds:
            return winning_builds[0]  # Моментально забираем победу

        # ==========================================
        # ПРИОРИТЕТ 3: РАЗВЕДКА И КЛЮЧИ
        # ==========================================
        map_actions = [
            a for a in legal_actions
            if isinstance(a, ActionPlayBoardUtility)
               and getattr(_get_tpl(a.template_id), "action_type", None) == ActionType.MAP
        ]
        if map_actions:
            best_map = self._choose_best_map_action(game, map_actions)
            if best_map: return best_map

        key_actions = [
            a for a in legal_actions
            if isinstance(a, ActionPlayBoardUtility)
               and getattr(_get_tpl(a.template_id), "action_type", None) == ActionType.KEY
        ]
        if key_actions:
            return random.choice(key_actions)

        # ==========================================
        # ПРИОРИТЕТ 4: ЦЕЛЕУСТРЕМЛЕННОЕ СТРОИТЕЛЬСТВО
        # ==========================================
        if build_actions:
            best_build = self._choose_best_build_action(game, build_actions, gold_targets)
            if best_build: return best_build

        # ==========================================
        # ПРИОРИТЕТ 5: САБОТАЖ И ОБВАЛЫ
        # ==========================================
        sabotage_actions = [
            a for a in legal_actions
            if isinstance(a, ActionPlayPlayerUtility) and a.target_player_id == opponent_id
               and getattr(_get_tpl(a.template_id), "action_type", None) == ActionType.SABOTAGE
        ]
        if sabotage_actions:
            return self._pick_best_sabotage(sabotage_actions, game)

        rockfall_actions = [
            a for a in legal_actions
            if isinstance(a, ActionPlayBoardUtility)
               and getattr(_get_tpl(a.template_id), "action_type", None) == ActionType.ROCKFALL
        ]
        if rockfall_actions:
            best_rockfall = self._choose_best_rockfall(game, rockfall_actions, opponent_id)
            if best_rockfall: return best_rockfall

        # ==========================================
        # ПРИОРИТЕТ 6: СБРОС И ВРЕДНАЯ ПОЧИНКА
        # ==========================================
        harmful_repair = [
            a for a in legal_actions
            if isinstance(a, ActionPlayPlayerUtility) and a.target_player_id == opponent_id
               and getattr(_get_tpl(a.template_id), "action_type", None) == ActionType.REPAIR
               and getattr(_get_tpl(a.template_id), "equipment_type", None) in opponent_state.broken_equipments
        ]
        if harmful_repair:
            return random.choice(harmful_repair)

        discard_actions = [a for a in legal_actions if isinstance(a, ActionDiscard)]
        if discard_actions:
            return self._choose_best_discard(game, discard_actions)

        return random.choice(legal_actions)

    def _choose_best_build_action(self, game: Game, build_actions: List[ActionBuild], gold_targets: List[Dict]) -> \
    Optional[ActionBuild]:
        best_action = None
        best_score = -50.0

        base_frontier = self._get_frontier(game)
        if not base_frontier or not gold_targets:
            return None

        # --- ЗАХВАТ ЦЕЛИ (Target Lock) ---
        # Ищем золото, которое физически ближе всего к нашему фронтиру
        closest_gold = None
        min_dist_to_gold = float('inf')

        for target in gold_targets:
            gx, gy = target["coord"]
            # Считаем минимальное расстояние от текущего фронтира до этого золота
            dist = min(abs(gx - fx) + abs(gy - fy) for fx, fy in base_frontier)

            # Если мы знаем, что там 1 слиток - игнорируем его, если есть другие варианты
            if target["known"] and target["value"] == 1 and len(gold_targets) > 1:
                continue

            if dist < min_dist_to_gold:
                min_dist_to_gold = dist
                closest_gold = target

        if not closest_gold:
            closest_gold = gold_targets[0]  # Резерв

        gx, gy = closest_gold["coord"]
        player_state = game.state.players[self.player_id]

        # --- ОЦЕНКА ХОДОВ ---
        for action in build_actions:
            t_id = player_state.card_id_to_template.get(action.template_id)
            if not t_id: continue
            tpl = REGISTRY.get(t_id)
            score = 0.0

            # Насколько НОВАЯ карта близка к захваченной цели?
            dist_from_new_card = abs(gx - action.x) + abs(gy - action.y)

            if dist_from_new_card < min_dist_to_gold:
                score += 50 + (20 - dist_from_new_card) * 2  # Мы стали ближе к цели!
            elif dist_from_new_card > min_dist_to_gold:
                score -= 50  # Уходим в сторону от цели
            else:
                score += 5  # Строим вбок (полезно для обхода препятствий)

            # Наказываем за тупики
            if self._count_openings(tpl) == 1:
                score -= 40

            # Бонус, если выход направлен вниз (к золоту)
            has_down = tpl.openings.up if action.is_rotated_180 else tpl.openings.down
            if has_down:
                score += 10

            if score > best_score:
                best_score = score
                best_action = action

        return best_action

    def _choose_best_map_action(self, game: Game, map_actions: List[ActionPlayBoardUtility]) -> Optional[
        ActionPlayBoardUtility]:
        best_action = None
        best_val = -1
        known = game.state.players[self.player_id].known_secrets

        for action in map_actions:
            coord_key = BoardEngine.coord_to_str(action.x, action.y)
            if coord_key in known: continue

            placed = game.state.board.get(coord_key)
            if placed:
                tpl = REGISTRY.get(placed.template_id)
                if isinstance(tpl, GoldCardTemplate) and tpl.gold_value > best_val:
                    best_val = tpl.gold_value
                    best_action = action

        return best_action

    def _pick_best_sabotage(self, sabotage_actions: List[ActionPlayPlayerUtility],
                            game: Game) -> ActionPlayPlayerUtility:
        best_action = None
        best_priority = -1
        player_state = game.state.players[self.player_id]

        for action in sabotage_actions:
            t_id = player_state.card_id_to_template.get(action.template_id)
            if not t_id: continue
            tpl = REGISTRY.get(t_id)
            priority = self._equipment_priority(tpl.equipment_type)
            if priority > best_priority:
                best_priority = priority
                best_action = action
        return best_action or random.choice(sabotage_actions)

    def _choose_best_rockfall(self, game: Game, rockfall_actions: List[ActionPlayBoardUtility], opponent_id: int) -> \
    Optional[ActionPlayBoardUtility]:
        best_action = None
        best_score = float("-inf")
        opp_start = game.start_positions[opponent_id]
        opponent_state = game.state.players[opponent_id]

        for action in rockfall_actions:
            coord_key = BoardEngine.coord_to_str(action.x, action.y)
            if coord_key not in game.state.board: continue

            score = 0
            # Бьем туда, где противнику больнее всего восстанавливать путь
            dist = abs(action.x - opp_start[0]) + abs(action.y - opp_start[1])
            score += max(0, 15 - dist)

            if coord_key in opponent_state.ladders:
                score += 30

                # Не ломаем рядом с золотом, чтобы не перекрыть путь себе
            for g_key, g_placed in game.state.board.items():
                tpl = REGISTRY.get(g_placed.template_id)
                if isinstance(tpl, GoldCardTemplate) and not g_placed.is_revealed:
                    gx, gy = BoardEngine.str_to_coord(g_key)
                    if abs(action.x - gx) + abs(action.y - gy) <= 2:
                        score -= 50

            if score > best_score:
                best_score = score
                best_action = action

        return best_action

    def _choose_best_discard(self, game: Game, discard_actions: List[ActionDiscard]) -> AgentAction:
        best_action = None
        best_score = float("-inf")
        player_state = game.state.players[self.player_id]

        for action in discard_actions:
            score = 0
            if action.repair_equipment:
                score += 100  # Экстренная починка - спасение игры!

            for t_id in action.templates:
                t_name = player_state.card_id_to_template.get(t_id)
                if not t_name: continue
                tpl = REGISTRY.get(t_name)

                if not player_state.broken_equipments:
                    if getattr(tpl, "action_type", None) == ActionType.REPAIR: score += 10
                    if self._count_openings(tpl) == 1: score += 15
                    if isinstance(tpl, DoorCardTemplate): score += 5
                else:
                    if isinstance(tpl, (TunnelCardTemplate, DoorCardTemplate, LadderCardTemplate)):
                        score += 15

            if len(action.templates) == 2:
                score += 5

            if score > best_score:
                best_score = score
                best_action = action

        return best_action if best_action else random.choice(discard_actions)