import random
from typing import List, Dict, Tuple
from cards import TunnelCard, CardOpenings, ConsoleColor, Direction
from board import GameBoard


class Game:
    def __init__(self):
        self.board = GameBoard()
        self.players = [0, 1]
        self.current_player = 0

        self.start_positions = {
            0: (-1, 0),
            1: (1, 0)
        }

        self.player_colors = {
            0: ConsoleColor.BLUE,
            1: ConsoleColor.GREEN
        }

        self.deck = self._create_deck()
        # [NEW] Создаем колоду золота
        self.gold_deck = self._create_gold_deck()

        self.hands: Dict[int, List[TunnelCard]] = {0: [], 1: []}

        start_blue = TunnelCard("Start Blue", CardOpenings(True, True, True, True), color=self.player_colors[0])
        self.board.place_card(*self.start_positions[0], start_blue)

        start_green = TunnelCard("Start Green", CardOpenings(True, True, True, True), color=self.player_colors[1])
        self.board.place_card(*self.start_positions[1], start_green)

        self._place_gold_cards()
        self._deal_initial_cards()

    def _create_gold_deck(self) -> List[TunnelCard]:
        """[NEW] Создает колоду карт с золотом."""
        deck = []
        # Создаем 6 карт золота: две с 1, две с 2, две с 3 слитками
        # Используем форму перекрестка (все стороны открыты), чтобы золото всегда стыковалось
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
        deck = []
        # Стандартный набор карт
        for _ in range(3): deck.append(TunnelCard("", CardOpenings(up=True, down=True)))
        for _ in range(10): deck.append(TunnelCard("", CardOpenings(left=True, right=True)))
        for _ in range(10): deck.append(TunnelCard("", CardOpenings(left=True, down=True)))
        for _ in range(10): deck.append(TunnelCard("", CardOpenings(up=True, left=True)))
        for _ in range(10): deck.append(TunnelCard("", CardOpenings(True, True, True, True)))
        for _ in range(10): deck.append(TunnelCard("", CardOpenings(True, True, True)))
        for _ in range(10): deck.append(TunnelCard("",CardOpenings(up=True)))
        for _ in range(10): deck.append(TunnelCard("",CardOpenings(left=True)))
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

        if rotate_before_playing:
            card_to_play.rotate()

        start_pos = self.start_positions[self.current_player]

        if self.board.is_move_valid(x, y, card_to_play, start_pos):
            card_to_play.color = self.player_colors[self.current_player]

            self.board.place_card(x, y, card_to_play)
            hand.pop(card_idx)

            print(f"Игрок {self.current_player} поставил {card_to_play.name} на ({x}, {y})")

            # [NEW] Проверка, открыли ли мы золото этим ходом
            self._check_and_reveal_gold(x, y, card_to_play)

            if self.deck:
                hand.append(self.deck.pop())

            self.current_player = 1 - self.current_player
        else:
            print("Ошибка: Ход недопустим.")
            if rotate_before_playing:
                card_to_play.rotate()

    def _check_and_reveal_gold(self, x: int, y: int, placed_card: TunnelCard):
        """Проверяет соседей. Если сосед - закрытое золото, и мы к нему прокопали - открываем."""
        for direction in Direction:
            if not placed_card.openings.get_opening(direction):
                continue

            dx, dy = direction.value
            nx, ny = x + dx, y + dy

            neighbor = self.board.get_card(nx, ny)

            # Если сосед существует, является золотом, но еще не открыт
            if neighbor and neighbor.is_gold and neighbor.gold_value == 0:
                if self.gold_deck:
                    real_gold_card = self.gold_deck.pop()

                    # [ВАЖНО] Присваиваем карте цвет игрока, который её открыл
                    real_gold_card.color = self.player_colors[self.current_player]

                    self.board.place_card(nx, ny, real_gold_card)
                    print(f"✨ ЗОЛОТО НАЙДЕНО! В сундуке {real_gold_card.gold_value} слитков! ✨")
                else:
                    print("Золото кончилось :(")

    def get_possible_moves_at(self, x: int, y: int) -> List[Tuple[int, TunnelCard, bool]]:
        hand = self.hands[self.current_player]
        possible_moves = []
        start_pos = self.start_positions[self.current_player]

        for idx, card in enumerate(hand):
            temp_color = card.color
            card.color = self.player_colors[self.current_player]

            if self.board.is_move_valid(x, y, card, start_pos):
                possible_moves.append((idx, card, False))

            rotated_copy = card.get_rotated_copy()
            rotated_copy.color = self.player_colors[self.current_player]

            if rotated_copy.openings != card.openings:
                if self.board.is_move_valid(x, y, rotated_copy, start_pos):
                    possible_moves.append((idx, rotated_copy, True))

            card.color = temp_color

        return possible_moves

    def print_state(self):
        print("\nПоле:")
        min_x, max_x = -3, 3
        min_y, max_y = -10, 1

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