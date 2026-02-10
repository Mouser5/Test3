import random
from typing import List, Dict, Tuple
from cards import TunnelCard, CardOpenings, ConsoleColor
from board import GameBoard


class Game:
    def __init__(self):
        self.board = GameBoard()
        self.players = [0, 1]
        self.current_player = 0

        # Координаты стартов как на картинке:
        # Синий (слева) примерно (-4, 0), Зеленый (справа) примерно (4, 0)
        self.start_positions = {
            0: (-4, 0),
            1: (4, 0)
        }

        # Цвета игроков
        self.player_colors = {
            0: ConsoleColor.BLUE,
            1: ConsoleColor.GREEN
        }

        self.deck = self._create_deck()
        self.hands: Dict[int, List[TunnelCard]] = {0: [], 1: []}

        # Стартовая карта Синего (Игрок 0)
        start_blue = TunnelCard("Start Blue", CardOpenings(True, True, True, True), color=self.player_colors[0])
        self.board.place_card(*self.start_positions[0], start_blue)

        # Стартовая карта Зеленого (Игрок 1)
        start_green = TunnelCard("Start Green", CardOpenings(True, True, True, True), color=self.player_colors[1])
        self.board.place_card(*self.start_positions[1], start_green)

        self._place_gold_cards()
        self._deal_initial_cards()

    def _place_gold_cards(self):
        # Золото расположено внизу, ряд y = -3, через одну клетку
        gold_xs = [-5, -3, -1, 1, 3, 5]
        y_pos = -3

        for i, x in enumerate(gold_xs):
            # Золото по умолчанию желтое
            gold_card = TunnelCard(f"Gold_{i}", CardOpenings(True, True, True, True), is_gold=True,
                                   color=ConsoleColor.YELLOW)
            self.board.place_card(x, y_pos, gold_card)

    def _create_deck(self) -> List[TunnelCard]:
        deck = []
        # Стандартный набор карт
        for _ in range(10): deck.append(TunnelCard("Vertical", CardOpenings(up=True, down=True)))
        for _ in range(10): deck.append(TunnelCard("Horizontal", CardOpenings(left=True, right=True)))
        for _ in range(10): deck.append(TunnelCard("Turn L-D", CardOpenings(left=True, down=True)))
        for _ in range(10): deck.append(TunnelCard("Turn U-L", CardOpenings(up=True, left=True)))
        for _ in range(5): deck.append(TunnelCard("Cross", CardOpenings(True, True, True, True)))
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
            # Присваиваем карте цвет текущего игрока перед установкой
            card_to_play.color = self.player_colors[self.current_player]

            self.board.place_card(x, y, card_to_play)
            hand.pop(card_idx)

            print(f"Игрок {self.current_player} поставил {card_to_play.name} на ({x}, {y})")

            if self.deck:
                hand.append(self.deck.pop())

            self.current_player = 1 - self.current_player
        else:
            print("Ошибка: Ход недопустим.")
            if rotate_before_playing:
                card_to_play.rotate()

    def get_possible_moves_at(self, x: int, y: int) -> List[Tuple[int, TunnelCard, bool]]:
        hand = self.hands[self.current_player]
        possible_moves = []
        start_pos = self.start_positions[self.current_player]

        for idx, card in enumerate(hand):
            # Для проверки хода временно даем карте цвет игрока (чтобы логика не ломалась, если она зависит от цвета, хотя пока не зависит)
            temp_color = card.color
            card.color = self.player_colors[self.current_player]

            if self.board.is_move_valid(x, y, card, start_pos):
                possible_moves.append((idx, card, False))

            rotated_copy = card.get_rotated_copy()
            rotated_copy.color = self.player_colors[self.current_player]

            if rotated_copy.openings != card.openings:
                if self.board.is_move_valid(x, y, rotated_copy, start_pos):
                    possible_moves.append((idx, rotated_copy, True))

            # Возвращаем исходный цвет (обычно Reset) карте в руке
            card.color = temp_color

        return possible_moves

    def print_state(self):
        print("\nПоле:")

        # Определяем границы отрисовки
        # На картинке от -6 до 6 по X, и от 2 до -4 по Y
        min_x, max_x = -6, 6
        min_y, max_y = -4, 2

        # Заголовок оси X
        header = "    "
        for x in range(min_x, max_x + 1):
            if len(x.__str__())==1:
                header += f"{x:^5}"
            else:
                header += f"{x:^4} "  # Выравнивание по центру в блоке из 5 символов
        print(header)

        # Разделительная линия
        print("    " + "_" * (len(header) - 4))

        # Отрисовка рядов (сверху вниз, поэтому range идет в обратном порядке)
        for y in range(max_y, min_y - 1, -1):
            line = f"{y:2} |"  # Ось Y слева
            for x in range(min_x, max_x + 1):
                card = self.board.get_card(x, y)
                if card:
                    # Карта уже содержит ANSI-цвет в своем __str__
                    line += f" {str(card)} "
                else:
                    # Пустая клетка (точка по центру)
                    line += "  .  "
            print(line)
        print("\n")