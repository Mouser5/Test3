import copy
import random
from typing import List, Dict, Tuple
from cards import TunnelCard, CardOpenings, ConsoleColor, Direction
from board import GameBoard


class Game:
    def __init__(self):
        self.board = GameBoard()
        self.players = [0, 1]
        self.current_player = 0

        self.start_positions = {0: (-1, 0), 1: (1, 0)}
        self.player_colors = {0: ConsoleColor.BLUE, 1: ConsoleColor.GREEN}

        self.deck = self._create_deck()
        self.gold_deck = self._create_gold_deck()
        self.hands: Dict[int, List[TunnelCard]] = {0: [], 1: []}

        start_blue = TunnelCard("Start Blue", CardOpenings(True, True, True, True), color=self.player_colors[0])
        self.board.place_card(*self.start_positions[0], start_blue)

        start_green = TunnelCard("Start Green", CardOpenings(True, True, True, True), color=self.player_colors[1])
        self.board.place_card(*self.start_positions[1], start_green)

        self._place_gold_cards()
        self._deal_initial_cards()

    def _create_gold_deck(self) -> List[TunnelCard]:
        deck = []
        values = [1, 1, 2, 2, 3, 3]
        for val in values:
            deck.append(TunnelCard(
                name=f"Gold_{val}",
                openings=CardOpenings(True, True, True, True),
                is_gold=True,
                gold_value=val,
                color=ConsoleColor.YELLOW
            ))
        random.shuffle(deck)
        return deck

    def _place_gold_cards(self, positions=None):
        if positions is None:
            positions = [(-2, -5), (0, -5), (2, -5), (-1, -7), (1, -7), (0, -9)]
        for i, (x, y) in enumerate(positions):
            gold_card = TunnelCard(
                f"Hidden_Gold_{i}",
                CardOpenings(True, True, True, True),
                is_gold=True,
                color=ConsoleColor.YELLOW
            )
            self.board.place_card(x, y, gold_card)

    def _create_deck(self) -> List[TunnelCard]:
        # (Название, Openings(U, D, L, R), Subnetworks, is_ladder, is_door, is_key, count)
        card_configs = [
            # (Название, Openings(U, D, L, R), Subnetworks, Количество)
            #("Ladder", (False, True, True, False), None, True, False, False, 4),
            ("Split T Vertical", (True, True, True, True), [{Direction.UP}, {Direction.DOWN, Direction.LEFT, Direction.RIGHT}],None, None, None, 10),
            # ("Split T Left", (True, True, True, True),
            #  [{Direction.LEFT}, {Direction.DOWN, Direction.UP, Direction.RIGHT}], 10),
            #("Bridge", (True, True, True, True), [{Direction.LEFT, Direction.RIGHT}, {Direction.DOWN, Direction.UP}], None, None, None, 10),

            # Перекрестки и туннели
            ("Crossroad", (True, True, True, True), None, None, False, False, 8),
            # ("T-Junction", (True, True, True, False), None, 10),
            # ("Straight Vertical", (True, True, False, False), None, 3),
            # ("Straight Horizontal", (False, False, True, True), None, 10),
            # ("Corner LD", (False, True, True, False), None, 10),
            # ("Corner UL", (True, False, True, False), None, 10),
            #
            # # Тупики
            # ("Dead End Up", (True, False, False, False), None, 10),
            # ("Dead End Left", (False, False, True, False), None, 10),

            # [NEW] Двери
            # Дверь - это прямой туннель (вертикальный или горизонтальный, зависит от поворота),
            # который блокирует проход. Сделаем их "прямыми" по умолчанию.
            # ("Door", (True, True, False, False), None, False, True, False, 4),

            # [NEW] Ключи
            # У ключа нет "выходов", это карта действия.
            # ("Key", (False, False, False, False), None, False, False, True, 2),
        ]

        deck = []
        for name, ops, subs, is_ladder, is_door, is_key, count in card_configs:
            openings = CardOpenings(up=ops[0], down=ops[1], left=ops[2], right=ops[3])
            card = TunnelCard(
                name=name, openings=openings, subnetworks=subs if subs else None,
                is_ladder=is_ladder, is_door=is_door, is_key=is_key, color=ConsoleColor.RESET
            )
            for _ in range(count):
                deck.append(card.copy() if hasattr(card, 'copy') else copy.deepcopy(card))

        random.shuffle(deck)
        return deck

    def _deal_initial_cards(self):
        for p in self.players:
            for _ in range(6):
                if self.deck: self.hands[p].append(self.deck.pop())

    def play_turn(self, card_idx: int, x: int, y: int, rotate_before_playing: bool = False):
        hand = self.hands[self.current_player]
        if card_idx < 0 or card_idx >= len(hand):
            print("Ошибка: Неверный индекс карты.")
            return

        card_to_play = hand[card_idx]
        current_color = self.player_colors[self.current_player]

        if rotate_before_playing and not card_to_play.is_key:
            card_to_play.rotate()

        if self.board.is_move_valid(x, y, card_to_play, self.start_positions[self.current_player], current_color):

            # ЛОГИКА КЛЮЧА
            if card_to_play.is_key:
                target_card = self.board.get_card(x, y)
                target_card.is_locked = False
                print(f"Игрок {self.current_player} открыл дверь ключом на ({x}, {y})!")
                hand.pop(card_idx)

            else:
                # ОБЫЧНАЯ КАРТА
                card_to_play.color = current_color
                self.board.place_card(x, y, card_to_play)
                hand.pop(card_idx)

                card_type = "ДВЕРЬ" if card_to_play.is_door else "карту"
                print(f"Игрок {self.current_player} поставил {card_type} {card_to_play.name} на ({x}, {y})")
                self._check_and_reveal_gold(x, y, card_to_play)

            if self.deck: hand.append(self.deck.pop())
            self.current_player = 1 - self.current_player
        else:
            print("Ошибка: Ход недопустим.")
            if rotate_before_playing and not card_to_play.is_key:
                card_to_play.rotate()

    def _check_and_reveal_gold(self, x: int, y: int, placed_card: TunnelCard):
        for direction in Direction:
            if not placed_card.openings.get_opening(direction):
                continue

            if placed_card.is_door and placed_card.is_locked:
                continue

            dx, dy = direction.value
            nx, ny = x + dx, y + dy
            neighbor = self.board.get_card(nx, ny)

            if neighbor and neighbor.is_gold and neighbor.gold_value == 0:
                if self.gold_deck:
                    real_gold_card = self.gold_deck.pop()
                    real_gold_card.color = self.player_colors[self.current_player]
                    self.board.place_card(nx, ny, real_gold_card)
                    print(f"✨ ЗОЛОТО НАЙДЕНО! В сундуке {real_gold_card.gold_value} слитков! ✨")
                else:
                    print("Золото кончилось :(")

    def get_possible_moves_at(self, x: int, y: int) -> List[Tuple[int, TunnelCard, bool]]:
        hand = self.hands[self.current_player]
        possible_moves = []
        start_pos = self.start_positions[self.current_player]
        current_color = self.player_colors[self.current_player]

        existing_card = self.board.get_card(x, y)

        for idx, card in enumerate(hand):
            if card.is_key:
                if existing_card and existing_card.is_door:
                    if self.board.is_move_valid(x, y, card, start_pos, current_color):
                        possible_moves.append((idx, card, False))
                continue

            if existing_card: continue

            temp_color = card.color
            card.color = current_color

            if self.board.is_move_valid(x, y, card, start_pos, current_color):
                possible_moves.append((idx, card, False))

            rotated_copy = card.get_rotated_copy()
            rotated_copy.color = current_color

            if rotated_copy.openings != card.openings or rotated_copy.subnetworks != card.subnetworks:
                if self.board.is_move_valid(x, y, rotated_copy, start_pos, current_color):
                    possible_moves.append((idx, rotated_copy, True))

            card.color = temp_color

        return possible_moves

    def print_state(self):
        print("\nПоле:")
        min_x, max_x = -3, 3
        min_y, max_y = -10, 1

        keys = self.board.grid.keys()
        if keys:
            xs, ys = [k[0] for k in keys], [k[1] for k in keys]
            min_x, max_x = min(min_x, min(xs) - 1), max(max_x, max(xs) + 1)
            min_y, max_y = min(min_y, min(ys) - 1), max(max_y, max(ys) + 1)

        header = "    "
        for x in range(min_x, max_x + 1):
            if len(str(x)) == 1:
                header += f"{x:^5}"
            else:
                header += f"{x:^4} "
        print(header)
        print("    " + "_" * (len(header) - 4))

        for y in range(max_y, min_y - 1, -1):
            if len(str(y)) <= 2:
                line = f"{y:2} |"
            else:
                line = f"{y:2}|"
            for x in range(min_x, max_x + 1):
                card = self.board.get_card(x, y)
                if card:
                    line += f" {str(card)} "
                else:
                    line += "  .  "
            print(line)
        print("\n")