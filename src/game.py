import random
from typing import Tuple, Optional, Dict, List
from itertools import combinations

from cards import (TunnelCardTemplate, StartCardTemplate, DoorCardTemplate,
                   LadderCardTemplate, GoldCardTemplate, ActionCardTemplate,
                   ActionType, Direction)
from actions import AgentAction, ActionBuild, ActionPlayBoardUtility, ActionPlayPlayerUtility, ActionDiscard, ActionPass
from state import MatchState, PlayerState, PlacedCard, ObservableMatchState, ObservablePlayerState
from registry import REGISTRY, setup_global_registry
from board import BoardEngine


class Game:
    def __init__(self):
        # Строгая инициализация глобального справочника (1 раз за всю работу программы)
        setup_global_registry()

        self.board_engine = BoardEngine(REGISTRY)
        self.state = MatchState()

        # Инициализируем игроков
        self.state.players[0] = PlayerState(player_id=0)
        self.state.players[1] = PlayerState(player_id=1)
        self.start_positions = {0: (-1, 0), 1: (1, 0)}

        self._build_decks()
        self._setup_board()
        self._deal_initial_cards()

    def _build_decks(self):
        """Быстрая сборка колод из ID-строк (без глубокого копирования объектов)."""
        deck = []
        counts = {
            "tunnel_cross": 10, "tunnel_t": 10, "tunnel_straight": 8, "tunnel_corner": 10, "tunnel_deadend": 4,
            "tunnel_bridge": 4, "tunnel_double_corner": 4, "tunnel_split_t_up": 4, "tunnel_split_t_l": 4,
            "door_blue": 3, "door_green": 3, "ladder": 4,
            "act_boom": 3, "act_key": 3, "act_map": 4
        }

        # Используем названия из enum напрямую, чтобы избежать циклического импорта
        for eq_name in ["LAMP", "CART", "PICKAXE"]:
            counts[f"brk_{eq_name}"] = 3
            counts[f"rep_{eq_name}"] = 3

        for t_id, count in counts.items():
            deck.extend([t_id] * count)

        gold_deck = []
        for val in [1, 1, 2, 2, 3, 3]:  # В дуэльной версии по 2 карты каждого номинала
            gold_deck.append(f"gold_val_{val}")

        random.shuffle(deck)
        random.shuffle(gold_deck)
        self.state.deck = deck
        self.state.gold_deck = gold_deck

    def _setup_board(self):
        """Установка стартовых входов и скрытого золота. ИСПОЛЬЗУЕМ КОРТЕЖИ (int, int)."""
        self.state.board[self.start_positions[0]] = PlacedCard(template_id="start_blue", owner_id=0)
        self.state.board[self.start_positions[1]] = PlacedCard(template_id="start_green", owner_id=1)

        gold_positions = [(-2, -5), (0, -5), (2, -5), (-1, -7), (1, -7), (0, -9)]
        for pos in gold_positions:
            if self.state.gold_deck:
                g_id = self.state.gold_deck.pop()
                self.state.board[pos] = PlacedCard(template_id=g_id, owner_id=None)

        # СИГНАЛ: Первичная настройка доски завершена
        self.state.board_update_count += 1

    def _deal_initial_cards(self):
        for p_id in [0, 1]:
            for _ in range(6):
                if self.state.deck:
                    self.state.players[p_id].hand.append(self.state.deck.pop())

    def _end_turn(self):
        self.state.current_player_id = 1 - self.state.current_player_id
        self.state.turn_number += 1

    def step(self, action: AgentAction) -> Tuple[bool, str, Optional[int]]:
        """Единая точка входа изменения состояния."""
        current_p = self.state.players[self.state.current_player_id]
        if self.is_game_over():
            return False, "Игра уже окончена.", None

        # ОБРАБОТКА ПАСА
        if isinstance(action, ActionPass):
            if current_p.hand:
                return False, "Нельзя пасовать, если в руке есть карты!", None
            self._end_turn()
            return True, "Ход пропущен (нет карт).", None

        if isinstance(action, ActionBuild):
            success, msg, rev_gold = self._handle_build(action)
        elif isinstance(action, ActionPlayBoardUtility):
            success, msg, rev_gold = self._handle_board_utility(action)
        elif isinstance(action, ActionPlayPlayerUtility):
            success, msg, rev_gold = self._handle_player_utility(action)
        elif isinstance(action, ActionDiscard):
            success, msg, rev_gold = self._handle_discard(action)
        else:
            return False, "Неизвестный тип действия.", None

        if success:
            self._end_turn()

        return success, msg, rev_gold

    def _handle_build(self, action: ActionBuild) -> Tuple[bool, str, Optional[int]]:
        p_id = self.state.current_player_id
        player_state = self.state.players[p_id]

        if action.template_id not in player_state.hand:
            return False, "Такой карты нет в руке.", None

        template = REGISTRY.get(action.template_id)

        if not isinstance(template, (TunnelCardTemplate, DoorCardTemplate, LadderCardTemplate)):
            return False, "Нельзя строить эту карту.", None

        if player_state.broken_equipments:
            return False, "Инвентарь сломан!", None

        placed = PlacedCard(template_id=action.template_id, owner_id=p_id, is_rotated_180=action.is_rotated_180)
        if isinstance(template, DoorCardTemplate):
            placed.is_locked = True

        coord_key = (action.x, action.y)

        # Полная валидация движком перед постановкой
        if not self.board_engine.is_move_valid(action.x, action.y, action.template_id, action.is_rotated_180,
                                               self.start_positions[p_id], p_id,
                                               self.state.board, player_state.ladders):
            return False, "Ход недопустим.", None

        self.state.board[coord_key] = placed
        if isinstance(template, LadderCardTemplate):
            player_state.ladders.add(coord_key)

        player_state.hand.remove(action.template_id)

        # СИГНАЛ: Игрок построил карту, доска изменилась
        self.state.board_update_count += 1

        revealed_gold = self._check_and_reveal_gold(action.x, action.y, placed)
        if self.state.deck:
            player_state.hand.append(self.state.deck.pop())

        return True, f"Игрок {p_id} построил на {coord_key}.", revealed_gold

    def _handle_board_utility(self, action: ActionPlayBoardUtility) -> Tuple[bool, str, Optional[int]]:
        p_id = self.state.current_player_id
        player_state = self.state.players[p_id]

        if action.template_id not in player_state.hand:
            return False, "Такой карты нет в руке.", None

        template = REGISTRY.get(action.template_id)
        coord_key = (action.x, action.y)
        target_placed = self.state.board.get(coord_key)

        if not target_placed:
            return False, "Клетка пуста.", None

        msg = ""
        if template.action_type == ActionType.KEY:
            target_tpl = REGISTRY.get(target_placed.template_id)
            if not isinstance(target_tpl, DoorCardTemplate) or not target_placed.is_locked:
                return False, "Здесь нет закрытой двери.", None
            target_placed.is_locked = False

            # Дверь открыта - доска изменилась (пути стали доступны)
            self.state.board_update_count += 1
            msg = f"Игрок {p_id} открыл дверь на {coord_key}."

        elif template.action_type == ActionType.ROCKFALL:
            if not self.board_engine.is_move_valid(action.x, action.y, action.template_id, False,
                                                   self.start_positions[p_id], p_id, self.state.board,
                                                   player_state.ladders):
                return False, "Нельзя обвалить.", None

            obval_tpl = REGISTRY.get(target_placed.template_id)
            if isinstance(obval_tpl, LadderCardTemplate) and target_placed.owner_id in self.state.players:
                self.state.players[target_placed.owner_id].ladders.discard(coord_key)

            del self.state.board[coord_key]

            # СИГНАЛ: Карту обвалили, доска изменилась
            self.state.board_update_count += 1
            msg = f"Обвал на {coord_key}!"

        elif template.action_type == ActionType.MAP:
            target_tpl = REGISTRY.get(target_placed.template_id)
            if not isinstance(target_tpl, GoldCardTemplate) or target_placed.is_revealed:
                return False, "Здесь нет скрытого золота.", None

            player_state.known_secrets.add(coord_key)  # known_secrets теперь тоже хранит кортежи
            msg = f"[СЕКРЕТ] Под {coord_key} спрятано {target_tpl.gold_value} слитков!"

        player_state.hand.remove(action.template_id)
        if self.state.deck:
            player_state.hand.append(self.state.deck.pop())

        return True, msg, None

    def _handle_player_utility(self, action: ActionPlayPlayerUtility) -> Tuple[bool, str, Optional[int]]:
        p_id = self.state.current_player_id
        player_state = self.state.players[p_id]

        if action.template_id not in player_state.hand:
            return False, "Такой карты нет в руке.", None

        template = REGISTRY.get(action.template_id)
        target_state = self.state.players[action.target_player_id]
        eq = template.equipment_type
        msg = ""

        if template.action_type == ActionType.SABOTAGE:
            if eq in target_state.broken_equipments:
                return False, "Уже сломано.", None
            target_state.broken_equipments.add(eq)
            msg = f"Игрок {p_id} сломал {eq.value} игроку {action.target_player_id}."

        elif template.action_type == ActionType.REPAIR:
            if eq not in target_state.broken_equipments:
                return False, "Не сломано.", None
            target_state.broken_equipments.remove(eq)
            msg = f"Игрок {p_id} починил {eq.value} игроку {action.target_player_id}."

        player_state.hand.remove(action.template_id)
        if self.state.deck:
            player_state.hand.append(self.state.deck.pop())

        return True, msg, None

    def _handle_discard(self, action: ActionDiscard) -> Tuple[bool, str, Optional[int]]:
        p_id = self.state.current_player_id
        state = self.state.players[p_id]

        if action.repair_equipment:
            if len(action.templates) != 2:
                return False, "Нужно 2 карты для экстренной починки.", None
            if action.repair_equipment not in state.broken_equipments:
                return False, "Предмет не сломан.", None
            state.broken_equipments.remove(action.repair_equipment)
            msg = f"Экстренная починка {action.repair_equipment.value}."
        else:
            msg = f"Сброшено карт: {len(action.templates)}."

        for tpl in action.templates:
            if tpl in state.hand:
                state.hand.remove(tpl)
            else:
                return False, f"Карты {tpl} нет в руке.", None

        cards_to_draw = 1 if action.repair_equipment else len(action.templates)
        for _ in range(cards_to_draw):
            if self.state.deck:
                state.hand.append(self.state.deck.pop())

        return True, msg, None

    def _check_and_reveal_gold(self, x: int, y: int, placed_card: PlacedCard) -> Optional[int]:
        revealed_amount = 0
        found_gold = False
        template = REGISTRY.get(placed_card.template_id)

        for direction in Direction:
            if not self.board_engine._get_effective_opening(template, direction, placed_card.is_rotated_180):
                continue

            dx, dy = direction.value
            nx, ny = x + dx, y + dy
            neighbor_key = (nx, ny)
            neighbor_placed = self.state.board.get(neighbor_key)

            if neighbor_placed and not neighbor_placed.is_revealed:
                n_tpl = REGISTRY.get(neighbor_placed.template_id)
                if isinstance(n_tpl, GoldCardTemplate):
                    neighbor_placed.is_revealed = True
                    neighbor_placed.owner_id = self.state.current_player_id
                    revealed_amount += n_tpl.gold_value
                    found_gold = True

        return revealed_amount if found_gold else None

    def get_legal_actions(self) -> List[AgentAction]:
        if self.is_game_over():
            return []

        current_p = self.state.players[self.state.current_player_id]
        if not current_p.hand:
            return [ActionPass()]

        legal_actions: List[AgentAction] = []
        p_id = self.state.current_player_id
        player_state = self.state.players[p_id]

        unique_hand = set(player_state.hand)
        for tpl in unique_hand:
            legal_actions.append(ActionDiscard(templates=(tpl,)))

        for tpl_tuple in set(combinations(sorted(player_state.hand), 2)):
            legal_actions.append(ActionDiscard(templates=tuple(tpl_tuple)))
            for eq in player_state.broken_equipments:
                legal_actions.append(ActionDiscard(templates=tuple(tpl_tuple), repair_equipment=eq))

        # === ИСПОЛЬЗУЕМ КЭШ ФРОНТИРА ===
        cached_version, cached_frontier = self.state.cached_frontiers[p_id]
        if cached_version == self.state.board_update_count:
            frontier_coords = cached_frontier  # O(1) извлечение
        else:
            # Пересчитываем только если доска изменилась (или это первый вызов)
            frontier_coords = self.board_engine.get_player_frontier(
                self.start_positions[p_id], p_id, self.state.board, player_state.ladders
            )
            self.state.cached_frontiers[p_id] = (self.state.board_update_count, frontier_coords)
        # ================================

        for t_id in unique_hand:
            template = REGISTRY.get(t_id)

            if isinstance(template, (TunnelCardTemplate, DoorCardTemplate, LadderCardTemplate)):
                if not player_state.broken_equipments:
                    for x, y in frontier_coords:
                        for is_rot in [False, True]:
                            if self.board_engine.is_move_valid(
                                    x, y, t_id, is_rot, self.start_positions[p_id], p_id,
                                    self.state.board, player_state.ladders, skip_path_check=True
                            ):
                                legal_actions.append(ActionBuild(template_id=t_id, x=x, y=y, is_rotated_180=is_rot))

            elif isinstance(template, ActionCardTemplate) and template.action_type in [ActionType.KEY,
                                                                                       ActionType.ROCKFALL,
                                                                                       ActionType.MAP]:
                for coord_key, target_placed in self.state.board.items():
                    tx, ty = coord_key  # Быстрая распаковка кортежа
                    target_tpl = REGISTRY.get(target_placed.template_id)

                    if template.action_type == ActionType.KEY:
                        if isinstance(target_tpl,
                                      DoorCardTemplate) and target_placed.is_locked and target_tpl.door_owner_id != p_id:
                            if self.board_engine.check_path_connectivity(tx, ty, self.start_positions[p_id], p_id,
                                                                         self.state.board, player_state.ladders):
                                legal_actions.append(ActionPlayBoardUtility(template_id=t_id, x=tx, y=ty))

                    elif template.action_type == ActionType.ROCKFALL:
                        if self.board_engine.is_move_valid(tx, ty, t_id, False,
                                                           self.start_positions[p_id], p_id, self.state.board,
                                                           player_state.ladders):
                            legal_actions.append(ActionPlayBoardUtility(template_id=t_id, x=tx, y=ty))

                    elif template.action_type == ActionType.MAP:
                        if isinstance(target_tpl, GoldCardTemplate) and not target_placed.is_revealed:
                            legal_actions.append(ActionPlayBoardUtility(template_id=t_id, x=tx, y=ty))

            elif isinstance(template, ActionCardTemplate) and template.action_type in [ActionType.SABOTAGE,
                                                                                       ActionType.REPAIR]:
                eq = template.equipment_type
                for target_p_id, target_state in self.state.players.items():
                    if template.action_type == ActionType.SABOTAGE and eq not in target_state.broken_equipments:
                        legal_actions.append(ActionPlayPlayerUtility(template_id=t_id, target_player_id=target_p_id))
                    elif template.action_type == ActionType.REPAIR and eq in target_state.broken_equipments:
                        legal_actions.append(ActionPlayPlayerUtility(template_id=t_id, target_player_id=target_p_id))

        return legal_actions

    def get_observation(self, target_player_id: int) -> ObservableMatchState:
        """Сензурирует состояние игры для конкретного агента, скрывая закрытое золото и чужие руки."""
        obs_board = {}
        player_secrets = self.state.players[target_player_id].known_secrets

        for coord_key, placed_card in self.state.board.items():
            tpl = REGISTRY.get(placed_card.template_id)
            if isinstance(tpl, GoldCardTemplate) and not placed_card.is_revealed:
                if coord_key not in player_secrets:
                    # ИСПРАВЛЕНИЕ: Pydantic удален. Делаем клон и ручную замену поля
                    masked_card = placed_card.clone()
                    masked_card.template_id = "hidden_gold"
                    obs_board[coord_key] = masked_card
                    continue

            obs_board[coord_key] = placed_card.clone()

        obs_players = {}
        for p_id, p_state in self.state.players.items():
            obs_players[p_id] = ObservablePlayerState(
                player_id=p_id,
                hand=p_state.hand.copy() if p_id == target_player_id else None,
                hand_size=len(p_state.hand),
                broken_equipments=p_state.broken_equipments.copy()
            )

        return ObservableMatchState(
            board=obs_board, players=obs_players, current_player_id=self.state.current_player_id,
            deck_size=len(self.state.deck), gold_deck_size=len(self.state.gold_deck),
            is_game_over=self.is_game_over(), turn_number=self.state.turn_number
        )

    def is_game_over(self) -> bool:
        unrevealed_gold = sum(1 for p in self.state.board.values() if
                              isinstance(REGISTRY.get(p.template_id), GoldCardTemplate) and not p.is_revealed)
        if unrevealed_gold == 0: return True
        if not self.state.deck and not self.state.players[0].hand and not self.state.players[1].hand: return True
        return False

    def calculate_scores(self) -> Dict[int, int]:
        scores = {0: 0, 1: 0}
        for p_card in self.state.board.values():
            tpl = REGISTRY.get(p_card.template_id)
            if isinstance(tpl, GoldCardTemplate) and p_card.is_revealed and p_card.owner_id is not None:
                scores[p_card.owner_id] += tpl.gold_value
        return scores