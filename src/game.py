import random
from typing import List, Dict, Tuple, Optional

from cards import (TunnelCardTemplate, StartCardTemplate, DoorCardTemplate,
                   LadderCardTemplate, GoldCardTemplate, ActionCardTemplate,
                   ActionType, EquipmentType, CardOpenings, Direction)
from state import MatchState, PlayerState, PlacedCard
from registry import REGISTRY
from board import BoardEngine


class Game:
    def __init__(self):
        self.board_engine = BoardEngine(REGISTRY)
        self.state = MatchState()

        # Инициализируем игроков
        self.state.players[0] = PlayerState(player_id=0)
        self.state.players[1] = PlayerState(player_id=1)
        self.start_positions = {0: (-1, 0), 1: (1, 0)}

        self._init_registry_and_decks()
        self._setup_board()
        self._deal_initial_cards()

    def _init_registry_and_decks(self):
        """Единожды регистрируем все шаблоны и собираем стартовые колоды."""
        deck_templates = []

        # 1. Обычные туннели
        tunnel_configs = [
            ("tunnel_cross", "Crossroad", (True, True, True, True), 10),
            ("tunnel_t", "T-Junction", (True, True, True, False), 10),
            ("tunnel_straight_vert", "Straight", (True, True, False, False), 4),
            ("tunnel_straight_hor","Straight Horizontal", (False, False, True, True), 4),
            ("tunnel_corner_ld", "Corner LD", (False, True, True, False), 10),
            ("tunnel_corner_lu","Corner LU", (True, False, True, False), 5),
            ("tunnel_deadened_up", "Dead End Up", (True, False, False, False), 4),
            ("tunnel_deadened_left", "Dead End Left", (False, False, True, False), 4),
            ("tunnel_deadened_cross","Dead End Cross", (True, True, True, True), 2)
        ]
        for t_id, name, ops, count in tunnel_configs:
            tpl = TunnelCardTemplate(id=t_id, name=name,
                                     openings=CardOpenings(up=ops[0], down=ops[1], left=ops[2], right=ops[3]))
            REGISTRY.register(tpl)
            deck_templates.extend([t_id] * count)

        subnetwork_configs = [
            ("tunnel_bridge", "Bridge", (True, True, True, True), [frozenset({Direction.UP, Direction.DOWN}), frozenset({Direction.LEFT, Direction.RIGHT})], 4),
            ("tunnel_double_corner", "Double Corner", (True, True, True, True),[frozenset({Direction.UP, Direction.LEFT}),frozenset ({Direction.DOWN, Direction.RIGHT})], 4),
            ("tunnel_split_t_up", "Split T Vertical", (True, True, True, True),[frozenset({Direction.UP}), frozenset({Direction.DOWN, Direction.LEFT, Direction.RIGHT})], 4),
            ("tunnel_split_t_l", "Split T Left", (True, True, True, True),[frozenset({Direction.LEFT}),frozenset( {Direction.DOWN, Direction.UP, Direction.RIGHT})], 4),
        ]

        for t_id, name, ops, subs, count in subnetwork_configs:
            tpl = TunnelCardTemplate(id=t_id, name=name,
                                     openings=CardOpenings(up=ops[0], down=ops[1], left=ops[2], right=ops[3]), subnetworks=subs)
            REGISTRY.register(tpl)
            deck_templates.extend([t_id] * count)

        # 3. Стартовые карты, Двери и Лестницы
        REGISTRY.register(StartCardTemplate(id="start_blue", name="Start Blue",
                                            openings=CardOpenings(up=True, down=True, left=True, right=True)))
        REGISTRY.register(StartCardTemplate(id="start_green", name="Start Green",
                                            openings=CardOpenings(up=True, down=True, left=True, right=True)))

        door_b = DoorCardTemplate(id="door_blue", name="Blue Door",
                                  openings=CardOpenings(up=True, down=True, left=False, right=False), door_owner_id=0)
        door_g = DoorCardTemplate(id="door_green", name="Green Door",
                                  openings=CardOpenings(up=True, down=True, left=False, right=False), door_owner_id=1)
        REGISTRY.register(door_b)
        REGISTRY.register(door_g)
        deck_templates.extend(["door_blue"] * 3 + ["door_green"] * 3)

        ladder = LadderCardTemplate(id="ladder", name="Ladder",
                                    openings=CardOpenings(up=False, down=True, left=True, right=False))
        REGISTRY.register(ladder)
        deck_templates.extend(["ladder"] * 4)

        # 4. Карты действий
        REGISTRY.register(ActionCardTemplate(id="act_boom", name="Boom", action_type=ActionType.ROCKFALL))
        REGISTRY.register(ActionCardTemplate(id="act_key", name="Key", action_type=ActionType.KEY))
        REGISTRY.register(ActionCardTemplate(id="act_map", name="Map", action_type=ActionType.MAP))
        deck_templates.extend(["act_boom"] * 3 + ["act_key"] * 3 + ["act_map"] * 4)

        for eq in EquipmentType:
            brk_id, rep_id = f"brk_{eq.name}", f"rep_{eq.name}"
            REGISTRY.register(ActionCardTemplate(id=brk_id, name=f"Break {eq.value}", action_type=ActionType.SABOTAGE,
                                                 equipment_type=eq))
            REGISTRY.register(ActionCardTemplate(id=rep_id, name=f"Repair {eq.value}", action_type=ActionType.REPAIR,
                                                 equipment_type=eq))
            deck_templates.extend([brk_id] * 3 + [rep_id] * 3)

        # 5. Золото (отдельная колода)
        gold_values = [1, 1, 2, 2, 3, 3]
        gold_deck = []
        for i, val in enumerate(gold_values):
            g_id = f"gold_val_{val}_{i}"
            REGISTRY.register(GoldCardTemplate(id=g_id, name=f"Gold {val}",
                                               openings=CardOpenings(up=True, down=True, left=True, right=True),
                                               gold_value=val))
            gold_deck.append(g_id)

        random.shuffle(deck_templates)
        random.shuffle(gold_deck)
        self.state.deck = deck_templates
        self.state.gold_deck = gold_deck

    def _setup_board(self):
        # Ставим стартовые карты
        self.state.board[BoardEngine.coord_to_str(*self.start_positions[0])] = PlacedCard(template_id="start_blue",
                                                                                          owner_id=0)
        self.state.board[BoardEngine.coord_to_str(*self.start_positions[1])] = PlacedCard(template_id="start_green",
                                                                                          owner_id=1)

        # Расставляем скрытое золото (берем из gold_deck, но кладем рубашкой вверх)
        gold_positions = [(-2, -5), (0, -5), (2, -5), (-1, -7), (1, -7), (0, -9)]
        for pos in gold_positions:
            if self.state.gold_deck:
                g_id = self.state.gold_deck.pop()
                # is_revealed = False по умолчанию в PlacedCard
                self.state.board[BoardEngine.coord_to_str(*pos)] = PlacedCard(template_id=g_id, owner_id=None)

    def _deal_initial_cards(self):
        for p_id in [0, 1]:
            for _ in range(6):
                if self.state.deck:
                    self.state.players[p_id].hand.append(self.state.deck.pop())

    def play_turn(self, card_idx: int, x: Optional[int] = None, y: Optional[int] = None,
                  target_player: Optional[int] = None, is_rotated: bool = False) -> Tuple[bool, str, Optional[int]]:

        curr_p_id = self.state.current_player_id
        player_state = self.state.players[curr_p_id]

        if card_idx < 0 or card_idx >= len(player_state.hand):
            return False, "Неверный индекс карты.", None

        t_id = player_state.hand[card_idx]
        template = REGISTRY.get(t_id)
        msg, revealed_gold = "", None

        if isinstance(template, TunnelCardTemplate) or isinstance(template, DoorCardTemplate) or isinstance(template,
                                                                                                            LadderCardTemplate):
            if x is None or y is None: return False, "Нужны координаты.", None
            if player_state.broken_equipments: return False, "Инвентарь сломан!", None

            placed = PlacedCard(template_id=t_id, owner_id=curr_p_id, is_rotated_180=is_rotated)
            # Для дверей инициализируем статус "закрыта"
            if isinstance(template, DoorCardTemplate): placed.is_locked = True

            if not self.board_engine.is_move_valid(x, y, placed, self.start_positions[curr_p_id], curr_p_id,
                                                   self.state.board):
                return False, "Ход недопустим по геометрии или пути.", None

            self.state.board[BoardEngine.coord_to_str(x, y)] = placed
            player_state.hand.pop(card_idx)
            revealed_gold = self._check_and_reveal_gold(x, y, placed)
            msg = f"Игрок {curr_p_id} построил туннель на ({x}, {y})."

        elif isinstance(template, ActionCardTemplate):
            if template.action_type in [ActionType.KEY, ActionType.ROCKFALL, ActionType.MAP]:
                if x is None or y is None: return False, "Укажите координаты на поле.", None
                coord_key = BoardEngine.coord_to_str(x, y)
                target_placed = self.state.board.get(coord_key)

                if not target_placed: return False, "Пустая клетка.", None

                if template.action_type == ActionType.KEY:
                    target_tpl = REGISTRY.get(target_placed.template_id)
                    if not isinstance(target_tpl, DoorCardTemplate) or not target_placed.is_locked:
                        return False, "Здесь нет закрытой двери.", None
                    target_placed.is_locked = False
                    msg = f"Игрок {curr_p_id} открыл дверь на ({x}, {y})."

                elif template.action_type == ActionType.ROCKFALL:
                    # Валидация уже есть в board_engine
                    if not self.board_engine.is_move_valid(x, y, PlacedCard(template_id=t_id),
                                                           self.start_positions[curr_p_id], curr_p_id,
                                                           self.state.board):
                        return False, "Нельзя обвалить эту карту.", None
                    del self.state.board[coord_key]
                    msg = f"Обвал на ({x}, {y})!"

                elif template.action_type == ActionType.MAP:
                    target_tpl = REGISTRY.get(target_placed.template_id)
                    if not isinstance(target_tpl, GoldCardTemplate) or target_placed.is_revealed:
                        return False, "Здесь нет скрытого золота.", None
                    msg = f"[СЕКРЕТ] Под картой ({x}, {y}) спрятано {target_tpl.gold_value} слитков!"

                player_state.hand.pop(card_idx)

            elif template.action_type in [ActionType.SABOTAGE, ActionType.REPAIR]:
                if target_player is None or target_player not in self.state.players:
                    return False, "Укажите валидную цель.", None

                target_state = self.state.players[target_player]
                eq = template.equipment_type

                if template.action_type == ActionType.SABOTAGE:
                    if eq in target_state.broken_equipments: return False, "Уже сломано.", None
                    target_state.broken_equipments.add(eq)
                    msg = f"Игрок {curr_p_id} сломал {eq.value} игроку {target_player}."
                elif template.action_type == ActionType.REPAIR:
                    if eq not in target_state.broken_equipments: return False, "Не сломано.", None
                    target_state.broken_equipments.remove(eq)
                    msg = f"Игрок {curr_p_id} починил {eq.value} игроку {target_player}."

                player_state.hand.pop(card_idx)

        # Добор карты и смена хода
        if self.state.deck: player_state.hand.append(self.state.deck.pop())
        self.state.current_player_id = 1 - self.state.current_player_id
        self.state.turn_number += 1

        return True, msg, revealed_gold

    def discard_cards(self, card_indices: List[int]) -> Tuple[bool, str]:
        p_id = self.state.current_player_id
        hand = self.state.players[p_id].hand
        if not (1 <= len(card_indices) <= 2): return False, "Сброс 1 или 2 карт."

        for idx in sorted(card_indices, reverse=True):
            if 0 <= idx < len(hand): hand.pop(idx)

        while len(hand) < 6 and self.state.deck:
            hand.append(self.state.deck.pop())

        self.state.current_player_id = 1 - self.state.current_player_id
        self.state.turn_number += 1
        return True, f"Сброшено карт: {len(card_indices)}."

    def discard_two_to_repair(self, card_indices: List[int], equip_type: EquipmentType) -> Tuple[bool, str]:
        p_id = self.state.current_player_id
        state = self.state.players[p_id]

        if len(card_indices) != 2: return False, "Нужно ровно 2 карты."
        if equip_type not in state.broken_equipments: return False, "Предмет не сломан."

        for idx in sorted(card_indices, reverse=True):
            if 0 <= idx < len(state.hand): state.hand.pop(idx)

        state.broken_equipments.remove(equip_type)
        if self.state.deck: state.hand.append(self.state.deck.pop())

        self.state.current_player_id = 1 - self.state.current_player_id
        self.state.turn_number += 1
        return True, f"Экстренная починка {equip_type.value} выполнена."

    def _check_and_reveal_gold(self, x: int, y: int, placed_card: PlacedCard) -> Optional[int]:
        revealed_amount = None
        template = REGISTRY.get(placed_card.template_id)

        for direction in Direction:
            if not self.board_engine._get_effective_opening(template, direction, placed_card.is_rotated_180): continue

            dx, dy = direction.value
            nx, ny = x + dx, y + dy
            neighbor_key = BoardEngine.coord_to_str(nx, ny)
            neighbor_placed = self.state.board.get(neighbor_key)

            if neighbor_placed and not neighbor_placed.is_revealed:
                n_tpl = REGISTRY.get(neighbor_placed.template_id)
                if isinstance(n_tpl, GoldCardTemplate):
                    neighbor_placed.is_revealed = True
                    neighbor_placed.owner_id = self.state.current_player_id
                    revealed_amount = n_tpl.gold_value
        return revealed_amount

    def is_game_over(self) -> bool:
        # Проверка, открыты ли все золотые карты
        unrevealed_gold = sum(1 for p in self.state.board.values() if
                              isinstance(REGISTRY.get(p.template_id), GoldCardTemplate) and not p.is_revealed)
        if unrevealed_gold == 0: return True

        # Проверка на пустые руки и колоду
        if not self.state.deck and not self.state.players[0].hand and not self.state.players[1].hand: return True
        return False

    def calculate_scores(self) -> Dict[int, int]:
        scores = {0: 0, 1: 0}
        for coord_key, p_card in self.state.board.items():
            tpl = REGISTRY.get(p_card.template_id)
            if isinstance(tpl, GoldCardTemplate) and p_card.is_revealed and p_card.owner_id is not None:
                x, y = BoardEngine.str_to_coord(coord_key)
                if self.board_engine.check_path_connectivity(x, y, self.start_positions[p_card.owner_id],
                                                             p_card.owner_id, self.state.board):
                    scores[p_card.owner_id] += tpl.gold_value
        return scores