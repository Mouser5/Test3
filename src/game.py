import copy
import random
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Set
from cards import (Card, PathCard, TunnelCard, StartCard, DoorCard, GoldCard, ActionCard,
                   ActionType, EquipmentType, CardOpenings, Direction, LadderCard)
from board import GameBoard


@dataclass
class TurnResult:
    success: bool
    message: str
    revealed_gold: Optional[int] = None


class Game:
    def __init__(self):
        self.board = GameBoard()
        self.players = [0, 1]
        self.current_player = 0

        self.start_positions = {0: (-1, 0), 1: (1, 0)}

        # Состояние инвентаря: какие предметы сломаны у каждого игрока
        self.broken_equipments: Dict[int, Set[EquipmentType]] = {0: set(), 1: set()}

        self.deck = self._create_deck()
        self.gold_deck = self._create_gold_deck()
        self.hands: Dict[int, List[Card]] = {0: [], 1: []}

        start_blue = StartCard("Start Blue", owner_id=0, openings=CardOpenings(True, True, True, True))
        self.board.place_card(*self.start_positions[0], start_blue)

        start_green = StartCard("Start Green", owner_id=1, openings=CardOpenings(True, True, True, True))
        self.board.place_card(*self.start_positions[1], start_green)

        self._place_gold_cards()
        self._deal_initial_cards()

    def _create_gold_deck(self) -> List[GoldCard]:
        deck = []
        for val in [1, 1, 2, 2, 3, 3]:
            deck.append(GoldCard(name=f"Gold_{val}", openings=CardOpenings(True, True, True, True), gold_value=val))
        random.shuffle(deck)
        return deck

    def _place_gold_cards(self, positions=None):
        if positions is None:
            positions = [(-2, -5), (0, -5), (2, -5), (-1, -7), (1, -7), (0, -9)]
        for i, (x, y) in enumerate(positions):
            self.board.place_card(x, y, GoldCard(f"Hidden_Gold_{i}", CardOpenings(True, True, True, True)))

    def _create_deck(self) -> List[Card]:
        deck = []

        # --- 1. ОБЫЧНЫЕ ТУННЕЛИ (TunnelCard) ---
        # Формат: (Название, (Up, Down, Left, Right), Количество)
        tunnel_configs = [
            ("Crossroad", (True, True, True, True), 10),
            ("T-Junction", (True, True, True, False), 10),
            ("Straight Vertical", (True, True, False, False), 4),
            ("Straight Horizontal", (False, False, True, True), 4),
            ("Corner LD", (False, True, True, False), 5),
            ("Corner UL", (True, False, True, False), 5),

            ("Dead End Up", (True, False, False, False), 4),
            ("Dead End Cross", (True, True, True, True), 2)  # Перекресток, который не соединяется (тупик)
        ]

        for name, ops, count in tunnel_configs:
            for _ in range(count):
                deck.append(TunnelCard(
                    name=name,
                    openings=CardOpenings(up=ops[0], down=ops[1], left=ops[2], right=ops[3])
                ))

        # --- 2. СЛОЖНЫЕ ТУННЕЛИ (С подсетями / subnetworks) ---
        # Мост: Вертикальный и горизонтальный пути не пересекаются
        subnetwork_configs = [
            ("Bridge", (True, True, True, True),[{Direction.UP, Direction.DOWN}, {Direction.LEFT, Direction.RIGHT}], 4),
            ("Double Corner", (True, True, True, True),[{Direction.UP, Direction.LEFT}, {Direction.DOWN, Direction.RIGHT}], 4),
            ("Split T Vertical", (True, True, True, True),[{Direction.UP}, {Direction.DOWN, Direction.LEFT, Direction.RIGHT}], 4),
            ("Split T Left", (True, True, True, True),[{Direction.LEFT}, {Direction.DOWN, Direction.UP, Direction.RIGHT}], 4),

        ]
        for name, ops, subs, count in subnetwork_configs:
            for _ in range(count):
                deck.append(TunnelCard(
                    name=name,
                    openings=CardOpenings(up=ops[0], down=ops[1], left=ops[2], right=ops[3]),
                    subnetworks=subs
                ))

        # --- 3. ДВЕРИ (DoorCard) ---
        # 3 синие и 3 зеленые двери. Представляют собой прямой туннель.
        for _ in range(3):
            deck.append(DoorCard("Blue Door", CardOpenings(True, True, False, False), door_owner_id=0))
            deck.append(DoorCard("Green Door", CardOpenings(True, True, False, False), door_owner_id=1))

        # --- 4. ЛЕСТНИЦЫ (LadderCard) ---
        for _ in range(4):
            deck.append(LadderCard("Ladder", CardOpenings(False, True, True, False)))

        # --- 5. КАРТЫ ДЕЙСТВИЙ (ActionCard) ---
        # Обвалы и Ключи
        for _ in range(3): deck.append(ActionCard("Boom", action_type=ActionType.ROCKFALL))
        for _ in range(3): deck.append(ActionCard("Key", action_type=ActionType.KEY))

        # Карты поломки и починки инвентаря
        for eq_type in EquipmentType:
            for _ in range(3):
                deck.append(
                    ActionCard(f"Сломать: {eq_type.value}", action_type=ActionType.SABOTAGE, equipment_type=eq_type))
            for _ in range(3):
                deck.append(
                    ActionCard(f"Починить: {eq_type.value}", action_type=ActionType.REPAIR, equipment_type=eq_type))

        random.shuffle(deck)
        return deck

    def _deal_initial_cards(self):
        for p in self.players:
            for _ in range(6):
                if self.deck: self.hands[p].append(self.deck.pop())

    def play_turn(self, card_idx: int, x: Optional[int] = None, y: Optional[int] = None,
                  target_player: Optional[int] = None, rotate_before_playing: bool = False) -> TurnResult:
        hand = self.hands[self.current_player]
        if card_idx < 0 or card_idx >= len(hand): return TurnResult(False, "Неверный индекс карты.")

        card_to_play = hand[card_idx]
        revealed_gold = None
        msg = ""

        # --- ОБРАБОТКА КАРТ ТУННЕЛЕЙ ---
        if isinstance(card_to_play, PathCard):
            if x is None or y is None: return TurnResult(False, "Нужны координаты для туннеля.")

            # ВАЖНО: Проверка на сломанный инвентарь
            if self.broken_equipments[self.current_player]:
                return TurnResult(False, "Нельзя строить туннели, пока ваш инвентарь сломан!")

            if rotate_before_playing: card_to_play.rotate()

            if not self.board.is_move_valid(x, y, card_to_play, self.start_positions[self.current_player],
                                            self.current_player):
                if rotate_before_playing: card_to_play.rotate()
                return TurnResult(False, "Ход недопустим по правилам геометрии.")

            card_to_play.owner_id = self.current_player
            self.board.place_card(x, y, card_to_play)
            hand.pop(card_idx)
            revealed_gold = self._check_and_reveal_gold(x, y, card_to_play)
            msg = f"Игрок {self.current_player} построил туннель на ({x}, {y})"

        # --- ОБРАБОТКА КАРТ ДЕЙСТВИЙ ---
        elif isinstance(card_to_play, ActionCard):
            # Карты на поле (Ключ, Обвал)
            if card_to_play.action_type in [ActionType.KEY, ActionType.ROCKFALL]:
                if x is None or y is None: return TurnResult(False, "Укажите координаты на поле.")
                if not self.board.is_move_valid(x, y, card_to_play, self.start_positions[self.current_player],
                                                self.current_player):
                    return TurnResult(False, "Недопустимое применение карты действия к полю.")

                if card_to_play.action_type == ActionType.KEY:
                    self.board.get_card(x, y).is_locked = False
                    msg = f"Игрок {self.current_player} открыл дверь ключом на ({x}, {y})!"
                elif card_to_play.action_type == ActionType.ROCKFALL:
                    self.board.remove_card(x, y)
                    msg = f"Игрок {self.current_player} устроил обвал на ({x}, {y})!"
                hand.pop(card_idx)

            # Карты на игроков (Поломка, Починка)
            elif card_to_play.action_type in [ActionType.SABOTAGE, ActionType.REPAIR]:
                if target_player is None: return TurnResult(False, "Нужно указать цель (игрока).")

                eq = card_to_play.equipment_type
                if card_to_play.action_type == ActionType.SABOTAGE:
                    if eq in self.broken_equipments[target_player]:
                        return TurnResult(False, f"У игрока {target_player} уже сломан(а) {eq.value}.")
                    self.broken_equipments[target_player].add(eq)
                    msg = f"Игрок {self.current_player} сломал {eq.value} игроку {target_player}!"

                elif card_to_play.action_type == ActionType.REPAIR:
                    if eq not in self.broken_equipments[target_player]:
                        return TurnResult(False, f"У игрока {target_player} не сломан(а) {eq.value}.")
                    self.broken_equipments[target_player].remove(eq)
                    msg = f"Игрок {self.current_player} починил {eq.value} игроку {target_player}!"
                hand.pop(card_idx)

        # Добор карты и смена хода
        if self.deck: hand.append(self.deck.pop())
        self.current_player = 1 - self.current_player
        return TurnResult(True, msg, revealed_gold)

    def discard_cards(self, player_idx: int, card_indices: List[int]) -> TurnResult:
        hand = self.hands[player_idx]
        if not (1 <= len(card_indices) <= 2):
            return TurnResult(False, "Можно сбросить только 1 или 2 карты.")

        for idx in sorted(card_indices, reverse=True):
            if 0 <= idx < len(hand): hand.pop(idx)

        while len(hand) < 6 and self.deck:
            hand.append(self.deck.pop())

        self.current_player = 1 - self.current_player
        return TurnResult(True, f"Сброшено карт: {len(card_indices)}.")

    def discard_two_to_repair(self, player_idx: int, card_indices: List[int], equip_type: EquipmentType) -> TurnResult:
        if len(card_indices) != 2:
            return TurnResult(False, "Для экстренной починки нужно ровно 2 карты.")
        if equip_type not in self.broken_equipments[player_idx]:
            return TurnResult(False, "Этот предмет не сломан.")

        hand = self.hands[player_idx]
        for idx in sorted(card_indices, reverse=True):
            hand.pop(idx)

        # Починка
        self.broken_equipments[player_idx].remove(equip_type)

        # Важно: по правилам после сброса 2 карт для починки берется только 1
        if self.deck: hand.append(self.deck.pop())

        self.current_player = 1 - self.current_player
        return TurnResult(True, f"Игрок пожертвовал 2 картами и починил {equip_type.value}.")

    def _check_and_reveal_gold(self, x: int, y: int, placed_card: PathCard) -> Optional[int]:
        revealed_amount = None
        for direction in Direction:
            if not placed_card.openings.get_opening(direction): continue
            if isinstance(placed_card, DoorCard) and placed_card.is_locked: continue

            dx, dy = direction.value
            nx, ny = x + dx, y + dy
            neighbor = self.board.get_card(nx, ny)

            if neighbor and isinstance(neighbor, GoldCard) and not neighbor.is_revealed:
                if self.gold_deck:
                    real_gold_card = self.gold_deck.pop()
                    real_gold_card.owner_id = self.current_player
                    real_gold_card.is_revealed = True
                    self.board.place_card(nx, ny, real_gold_card)
                    revealed_amount = real_gold_card.gold_value
        return revealed_amount

    def is_game_over(self) -> bool:
        if not self.gold_deck: return True
        if not self.deck and not self.hands[0] and not self.hands[1]: return True
        return False

    def calculate_scores(self) -> Dict[int, int]:
        scores = {0: 0, 1: 0}
        for (x, y), card in self.board.grid.items():
            if isinstance(card, GoldCard) and card.is_revealed and card.owner_id is not None:
                scores[card.owner_id] += card.gold_value
        return scores