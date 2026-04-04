import random
from typing import Tuple, Optional, Dict, List
from itertools import combinations

from cards import (
    TunnelCardTemplate, StartCardTemplate, DoorCardTemplate,
    LadderCardTemplate, GoldCardTemplate, ActionCardTemplate,
    ActionType, Direction, EquipmentType
)
from actions import (
    AgentAction, ActionBuild, ActionPlayBoardUtility,
    ActionPlayPlayerUtility, ActionDiscard, ActionPass
)
from state import MatchState, PlayerState, PlacedCard, ObservableMatchState, ObservablePlayerState
from registry import REGISTRY, setup_global_registry
from board import BoardEngine


class Game:
    """Основной класс игры."""

    def __init__(self):
        # ⬇️ ОДИН РАЗ инициализируем глобальный реестр
        setup_global_registry()

        self.board_engine = BoardEngine(REGISTRY)
        self.state = MatchState()

        # Инициализируем игроков
        self.state.players[0] = PlayerState(player_id=0)
        self.state.players[1] = PlayerState(player_id=1)

        # ⬇️ Стартовые позиции как КОРТЕЖИ
        self.start_positions = {0: (-1, 0), 1: (1, 0)}

        # Запускаем игру
        self._build_decks()
        self._setup_board()
        self._deal_initial_cards()

    def _build_decks(self):
        """Сборка колод из ID-строк."""
        deck = []
        counts = {
            "tunnel_cross": 10, "tunnel_t": 10, "tunnel_straight": 8, "tunnel_corner": 10,
            "tunnel_deadend": 4, "tunnel_bridge": 4, "tunnel_double_corner": 4,
            "tunnel_split_t_up": 4, "tunnel_split_t_l": 4,
            "door_blue": 3, "door_green": 3, "ladder": 4,
            "act_boom": 3, "act_key": 3, "act_map": 4
        }

        # ⬇️ Карты поломки и починки для всех инструментов
        for eq in EquipmentType:
            counts[f"brk_{eq.name}"] = 3
            counts[f"rep_{eq.name}"] = 3

        for t_id, count in counts.items():
            deck.extend([t_id] * count)

        # ⬇️ ИЗМЕНЕНИЕ: золото теперь обобщённое (gold_val_1/2/3)
        gold_deck = []
        for val in [1, 1, 2, 2, 3, 3]:  # По 2 карты каждого номинала
            gold_deck.append(f"gold_val_{val}")

        random.shuffle(deck)
        random.shuffle(gold_deck)
        self.state.deck = deck
        self.state.gold_deck = gold_deck

    def _setup_board(self):
        """Установка стартовых входов и скрытого золота."""
        # ⬇️ ИЗМЕНЕНИЕ: используем КОРТЕЖИ как ключи
        self.state.board[self.start_positions[0]] = PlacedCard(
            template_id="start_blue", owner_id=0
        )
        self.state.board[self.start_positions[1]] = PlacedCard(
            template_id="start_green", owner_id=1
        )

        # ⬇️ Разместим золото на фиксированных позициях
        gold_positions = [(-2, -5), (0, -5), (2, -5), (-1, -7), (1, -7), (0, -9)]
        for pos in gold_positions:
            if self.state.gold_deck:
                g_id = self.state.gold_deck.pop()
                self.state.board[pos] = PlacedCard(
                    template_id=g_id, owner_id=None
                )

        # ⬇️ НОВОЕ: сигнал об изменении доски (для кэша фронтира)
        self.state.board_update_count += 1

    def _deal_initial_cards(self):
        """Раздача карт в начале игры."""
        second_player = 1 - self.state.first_player_in_round
        for p_id in [0, 1]:
            cards_count = 5 if p_id == second_player else 4
            for _ in range(cards_count):
                if self.state.deck:
                    self.state.players[p_id].hand.append(self.state.deck.pop())

    def _end_turn(self):
        """Завершить ход текущего игрока."""
        self.state.current_player_id = 1 - self.state.current_player_id
        self.state.turn_number += 1

    def step(self, action: AgentAction) -> Tuple[bool, str, Optional[int]]:
        """
        Выполнить действие. Возвращает (успех, сообщение, золото_найдено).

        ⬇️ НОВОЕ: поддержка ActionPass
        """
        current_p = self.state.players[self.state.current_player_id]

        if self.is_game_over():
            return False, "Игра уже окончена.", None

        # ⬇️ НОВОЕ: обработка пропуска хода
        if isinstance(action, ActionPass):
            if current_p.hand:
                return False, "Нельзя пасовать, если в руке есть карты!", None
            self._end_turn()
            return True, "Ход пропущен (нет карт).", None

        # ⬇️ Обработка остальных действий
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
        """Обработка постройки."""
        p_id = self.state.current_player_id
        player_state = self.state.players[p_id]

        if action.template_id not in player_state.hand:
            return False, "Такой карты нет в руке.", None

        template = REGISTRY.get(action.template_id)

        if not isinstance(
                template, (TunnelCardTemplate, DoorCardTemplate, LadderCardTemplate)
        ):
            return False, "Нельзя строить эту карту.", None

        if player_state.broken_equipments:
            return False, "Инвентарь сломан!", None

        placed = PlacedCard(
            template_id=action.template_id,
            owner_id=p_id,
            is_rotated_180=action.is_rotated_180,
        )
        if isinstance(template, DoorCardTemplate):
            placed.is_locked = True

        # ⬇️ ИЗМЕНЕНИЕ: используем кортеж как ключ
        coord_key = (action.x, action.y)

        # ⬇️ ИЗМЕНЕНИЕ: передаём template_id, не PlacedCard
        if not self.board_engine.is_move_valid(
                action.x, action.y, action.template_id, action.is_rotated_180,
                self.start_positions[p_id], p_id,
                self.state.board, player_state.ladders
        ):
            return False, "Ход недопустим.", None

        self.state.board[coord_key] = placed

        # ⬇️ НОВОЕ: добавляем лестницу в кэш
        if isinstance(template, LadderCardTemplate):
            player_state.ladders.add(coord_key)  # ⬇️ КОРТЕЖ!

        player_state.hand.remove(action.template_id)

        # ⬇️ НОВОЕ: сигнал об изменении доски
        self.state.board_update_count += 1

        revealed_gold = self._check_and_reveal_gold(action.x, action.y, placed)
        if self.state.deck:
            player_state.hand.append(self.state.deck.pop())

        return True, f"Игрок {p_id} построил на {coord_key}.", revealed_gold

    def _handle_board_utility(
            self, action: ActionPlayBoardUtility
    ) -> Tuple[bool, str, Optional[int]]:
        """Обработка действий на поле (ключ, обвал, карта сокровищ)."""
        p_id = self.state.current_player_id
        player_state = self.state.players[p_id]

        if action.template_id not in player_state.hand:
            return False, "Такой карты нет в руке.", None

        template = REGISTRY.get(action.template_id)
        # ⬇️ ИЗМЕНЕНИЕ: кортеж как ключ
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

            # ⬇️ НОВОЕ: сигнал об изменении (пути открыты)
            self.state.board_update_count += 1
            msg = f"Игрок {p_id} открыл дверь на {coord_key}."

        elif template.action_type == ActionType.ROCKFALL:
            # ⬇️ ИЗМЕНЕНИЕ: передаём template_id
            if not self.board_engine.is_move_valid(
                    action.x, action.y, action.template_id, False,
                    self.start_positions[p_id], p_id, self.state.board,
                    player_state.ladders
            ):
                return False, "Нельзя обвалить.", None

            obval_tpl = REGISTRY.get(target_placed.template_id)
            if isinstance(obval_tpl, LadderCardTemplate) and target_placed.owner_id in self.state.players:
                # ⬇️ Удаляем лестницу из кэша
                self.state.players[target_placed.owner_id].ladders.discard(coord_key)

            del self.state.board[coord_key]

            # ⬇️ НОВОЕ: сигнал об изменении доски
            self.state.board_update_count += 1
            msg = f"Обвал на {coord_key}!"

        elif template.action_type == ActionType.MAP:
            target_tpl = REGISTRY.get(target_placed.template_id)
            if not isinstance(target_tpl, GoldCardTemplate) or target_placed.is_revealed:
                return False, "Здесь нет скрытого золота.", None

            # ⬇️ ИЗМЕНЕНИЕ: сохраняем КОРТЕЖ
            player_state.known_secrets.add(coord_key)
            msg = f"[СЕКРЕТ] Под {coord_key} спрятано {target_tpl.gold_value} слитков!"

        player_state.hand.remove(action.template_id)
        if self.state.deck:
            player_state.hand.append(self.state.deck.pop())

        return True, msg, None

    def _handle_player_utility(
            self, action: ActionPlayPlayerUtility
    ) -> Tuple[bool, str, Optional[int]]:
        """Обработка действий на игрока (поломка, починка)."""
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
        """Обработка сброса карт."""
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

        # ⬇️ ИЗМЕНЕНИЕ: templates теперь кортеж
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

    def _handle_build(self, action: ActionBuild) -> Tuple[bool, str, Optional[int]]:
        """Обработка постройки."""
        p_id = self.state.current_player_id
        player_state = self.state.players[p_id]

        if action.template_id not in player_state.hand:
            return False, "Такой карты нет в руке.", None

        template = REGISTRY.get(action.template_id)

        if not isinstance(
                template, (TunnelCardTemplate, DoorCardTemplate, LadderCardTemplate)
        ):
            return False, "Нельзя строить эту карту.", None

        if player_state.broken_equipments:
            return False, "Инвентарь сломан!", None

        placed = PlacedCard(
            template_id=action.template_id,
            owner_id=p_id,
            is_rotated_180=action.is_rotated_180,
        )
        if isinstance(template, DoorCardTemplate):
            placed.is_locked = True

        # ⬇️ ИЗМЕНЕНИЕ: используем кортеж как ключ
        coord_key = (action.x, action.y)

        # ⬇️ ИЗМЕНЕНИЕ: передаём template_id, не PlacedCard
        if not self.board_engine.is_move_valid(
                action.x, action.y, action.template_id, action.is_rotated_180,
                self.start_positions[p_id], p_id,
                self.state.board, player_state.ladders
        ):
            return False, "Ход недопустим.", None

        self.state.board[coord_key] = placed

        # ⬇️ НОВОЕ: добавляем лестницу в кэш
        if isinstance(template, LadderCardTemplate):
            player_state.ladders.add(coord_key)  # ⬇️ КОРТЕЖ!

        player_state.hand.remove(action.template_id)

        # ⬇️ НОВОЕ: сигнал об изменении доски
        self.state.board_update_count += 1

        revealed_gold = self._check_and_reveal_gold(action.x, action.y, placed)
        if self.state.deck:
            player_state.hand.append(self.state.deck.pop())

        return True, f"Игрок {p_id} построил на {coord_key}.", revealed_gold

    def _handle_board_utility(
            self, action: ActionPlayBoardUtility
    ) -> Tuple[bool, str, Optional[int]]:
        """Обработка действий на поле (ключ, обвал, карта сокровищ)."""
        p_id = self.state.current_player_id
        player_state = self.state.players[p_id]

        if action.template_id not in player_state.hand:
            return False, "Такой карты нет в руке.", None

        template = REGISTRY.get(action.template_id)
        # ⬇️ ИЗМЕНЕНИЕ: кортеж как ключ
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

            # ⬇️ НОВОЕ: сигнал об изменении (пути открыты)
            self.state.board_update_count += 1
            msg = f"Игрок {p_id} открыл дверь на {coord_key}."

        elif template.action_type == ActionType.ROCKFALL:
            # ⬇️ ИЗМЕНЕНИЕ: передаём template_id
            if not self.board_engine.is_move_valid(
                    action.x, action.y, action.template_id, False,
                    self.start_positions[p_id], p_id, self.state.board,
                    player_state.ladders
            ):
                return False, "Нельзя обвалить.", None

            obval_tpl = REGISTRY.get(target_placed.template_id)
            if isinstance(obval_tpl, LadderCardTemplate) and target_placed.owner_id in self.state.players:
                # ⬇️ Удаляем лестницу из кэша
                self.state.players[target_placed.owner_id].ladders.discard(coord_key)

            del self.state.board[coord_key]

            # ⬇️ НОВОЕ: сигнал об изменении доски
            self.state.board_update_count += 1
            msg = f"Обвал на {coord_key}!"

        elif template.action_type == ActionType.MAP:
            target_tpl = REGISTRY.get(target_placed.template_id)
            if not isinstance(target_tpl, GoldCardTemplate) or target_placed.is_revealed:
                return False, "Здесь нет скрытого золота.", None

            # ⬇️ ИЗМЕНЕНИЕ: сохраняем КОРТЕЖ
            player_state.known_secrets.add(coord_key)
            msg = f"[СЕКРЕТ] Под {coord_key} спрятано {target_tpl.gold_value} слитков!"

        player_state.hand.remove(action.template_id)
        if self.state.deck:
            player_state.hand.append(self.state.deck.pop())

        return True, msg, None

    def _handle_player_utility(
            self, action: ActionPlayPlayerUtility
    ) -> Tuple[bool, str, Optional[int]]:
        """Обработка действий на игрока (поломка, починка)."""
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
        """Обработка сброса карт."""
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

        # ⬇️ ИЗМЕНЕНИЕ: templates теперь кортеж
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

    def _check_and_reveal_gold(
            self, x: int, y: int, placed_card: PlacedCard
    ) -> Optional[int]:
        """Проверяет и раскрывает золото соседних карт."""
        revealed_amount = 0
        found_gold = False
        template = REGISTRY.get(placed_card.template_id)

        for direction in Direction:
            if not self.board_engine._get_effective_opening(
                    template, direction, placed_card.is_rotated_180
            ):
                continue

            dx, dy = direction.value
            nx, ny = x + dx, y + dy
            # ⬇️ ИЗМЕНЕНИЕ: кортеж как ключ
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
        """
        Генерирует все легальные ходы для текущего игрока.

        ⬇️ НОВОЕ: использует кэширование фронтира!
        """
        if self.is_game_over():
            return []

        current_p = self.state.players[self.state.current_player_id]

        # ⬇️ НОВОЕ: если рука пуста, только пас
        if not current_p.hand:
            return [ActionPass()]

        legal_actions: List[AgentAction] = []
        p_id = self.state.current_player_id
        player_state = self.state.players[p_id]

        # === СБРОС КАРТ ===
        unique_hand = set(player_state.hand)

        # ⬇️ Сброс 1 карты
        for tpl in unique_hand:
            legal_actions.append(ActionDiscard(templates=(tpl,)))

        # ⬇️ Сброс 2 карт
        for tpl_tuple in set(combinations(sorted(player_state.hand), 2)):
            legal_actions.append(ActionDiscard(templates=tuple(tpl_tuple)))
            for eq in player_state.broken_equipments:
                legal_actions.append(
                    ActionDiscard(templates=tuple(tpl_tuple), repair_equipment=eq)
                )

        # === ИСПОЛЬЗОВАНИЕ КЭША ФРОНТИРА ===
        # ⬇️ НОВОЕ: проверяем версию кэша
        cached_version, cached_frontier = self.state.cached_frontiers[p_id]
        if cached_version == self.state.board_update_count:
            # ⬇️ Кэш актуален, используем его
            frontier_coords = cached_frontier
        else:
            # ⬇️ Кэш устарел, пересчитываем
            frontier_coords = self.board_engine.get_player_frontier(
                self.start_positions[p_id], p_id, self.state.board, player_state.ladders
            )
            # ⬇️ Сохраняем в кэш
            self.state.cached_frontiers[p_id] = (
                self.state.board_update_count, frontier_coords
            )

        # === ПОСТРОЙКИ ===
        for t_id in unique_hand:
            template = REGISTRY.get(t_id)

            if isinstance(
                    template, (TunnelCardTemplate, DoorCardTemplate, LadderCardTemplate)
            ):
                if not player_state.broken_equipments:
                    # ⬇️ Используем кэшированный фронтир
                    for x, y in frontier_coords:
                        for is_rot in [False, True]:
                            if self.board_engine.is_move_valid(
                                    x, y, t_id, is_rot, self.start_positions[p_id], p_id,
                                    self.state.board, player_state.ladders,
                                    skip_path_check=True
                            ):
                                legal_actions.append(
                                    ActionBuild(template_id=t_id, x=x, y=y, is_rotated_180=is_rot)
                                )

            # === ДЕЙСТВИЯ НА ПОЛЕ ===
            elif isinstance(template, ActionCardTemplate) and template.action_type in [
                ActionType.KEY, ActionType.ROCKFALL, ActionType.MAP
            ]:
                for coord_key, target_placed in self.state.board.items():
                    # ⬇️ ИЗМЕНЕНИЕ: распаковка кортежа
                    tx, ty = coord_key
                    target_tpl = REGISTRY.get(target_placed.template_id)

                    if template.action_type == ActionType.KEY:
                        if (isinstance(target_tpl, DoorCardTemplate) and
                                target_placed.is_locked and
                                target_tpl.door_owner_id != p_id):
                            if self.board_engine.check_path_connectivity(
                                    coord_key, self.start_positions[p_id], p_id,
                                    self.state.board, player_state.ladders
                            ):
                                legal_actions.append(
                                    ActionPlayBoardUtility(template_id=t_id, x=tx, y=ty)
                                )

                    elif template.action_type == ActionType.ROCKFALL:
                        if self.board_engine.is_move_valid(
                                tx, ty, t_id, False,
                                self.start_positions[p_id], p_id,
                                self.state.board, player_state.ladders
                        ):
                            legal_actions.append(
                                ActionPlayBoardUtility(template_id=t_id, x=tx, y=ty)
                            )

                    elif template.action_type == ActionType.MAP:
                        if isinstance(target_tpl, GoldCardTemplate) and not target_placed.is_revealed:
                            legal_actions.append(
                                ActionPlayBoardUtility(template_id=t_id, x=tx, y=ty)
                            )

            # === ДЕЙСТВИЯ НА ИГРОКА ===
            elif isinstance(template, ActionCardTemplate) and template.action_type in [
                ActionType.SABOTAGE, ActionType.REPAIR
            ]:
                eq = template.equipment_type
                for target_p_id, target_state in self.state.players.items():
                    if (template.action_type == ActionType.SABOTAGE and
                            eq not in target_state.broken_equipments):
                        legal_actions.append(
                            ActionPlayPlayerUtility(template_id=t_id, target_player_id=target_p_id)
                        )
                    elif (template.action_type == ActionType.REPAIR and
                          eq in target_state.broken_equipments):
                        legal_actions.append(
                            ActionPlayPlayerUtility(template_id=t_id, target_player_id=target_p_id)
                        )

        return legal_actions

    def get_observation(self, target_player_id: int) -> ObservableMatchState:
        """Сензурирует состояние для игрока (скрывает чужую руку и скрытое золото)."""
        obs_board = {}
        player_secrets = self.state.players[target_player_id].known_secrets

        for coord_key, placed_card in self.state.board.items():
            tpl = REGISTRY.get(placed_card.template_id)
            if isinstance(tpl, GoldCardTemplate) and not placed_card.is_revealed:
                if coord_key not in player_secrets:
                    # ⬇️ Маскируем золото
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
            is_game_over=self.is_game_over(), turn_number=self.state.turn_number,
            round_number=self.state.round_number, total_scores=self.state.total_scores.copy()
        )

    def is_game_over(self) -> bool:
        """Проверка конца игры."""
        unrevealed_gold = sum(
            1 for p in self.state.board.values()
            if isinstance(REGISTRY.get(p.template_id), GoldCardTemplate) and not p.is_revealed
        )
        if unrevealed_gold == 0:
            return True
        if not self.state.deck and not self.state.players[0].hand and not self.state.players[1].hand:
            return True
        return False

    def calculate_scores(self) -> Dict[int, int]:
        """Подсчёт текущих очков."""
        scores = {0: 0, 1: 0}
        for p_card in self.state.board.values():
            tpl = REGISTRY.get(p_card.template_id)
            if isinstance(tpl, GoldCardTemplate) and p_card.is_revealed and p_card.owner_id is not None:
                scores[p_card.owner_id] += tpl.gold_value
        return scores

    def is_round_over(self) -> bool:
        """Проверка конца раунда (самого раунда, не игры)."""
        unrevealed_gold = sum(
            1 for p in self.state.board.values()
            if isinstance(REGISTRY.get(p.template_id), GoldCardTemplate) and not p.is_revealed
        )
        if unrevealed_gold == 0:
            return True
        if not self.state.deck and not self.state.players[0].hand and not self.state.players[1].hand:
            return True
        return False

    def _start_new_round(self):
        """Начать новый раунд (пересчитать очки, очистить доску и руки)."""
        # Подсчитываем очки текущего раунда
        round_scores = self.calculate_scores()
        self.state.total_scores[0] += round_scores[0]
        self.state.total_scores[1] += round_scores[1]
        self.state.round_scores = round_scores

        # Переходим к следующему раунду
        self.state.round_number += 1

        # ⬇️ В вашей версии игра одноразовая, поэтому после раунда 1 заканчиваем
        if self.state.round_number > 1:
            self.state.is_game_over = True
            return

        # ⬇️ Если бы было 3 раунда (как в VKRtemp), здесь была бы логика переиграения
        # но у вас - одна игра, поэтому просто завершаем

    def check_round_end(self) -> Tuple[bool, Optional[Dict[int, int]]]:
        """
        Проверяет, закончился ли раунд.
        Возвращает (раунд_закончился, очки_раунда).
        """
        if self.is_round_over():
            self._start_new_round()
            return True, self.state.round_scores
        return False, None