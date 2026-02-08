import random
from typing import List, Dict
from cards import TunnelCard, CardOpenings
from board import GameBoard


class Game:
    def __init__(self):
        self.board = GameBoard()
        self.players = [0, 1]
        self.current_player = 0
        self.deck = self._create_deck()
        self.hands: Dict[int, List[TunnelCard]] = {0: [], 1: []}

        # [cite_start]Инициализация стартовых карт (Входы) [cite: 25]
        start1 = TunnelCard("Start1", CardOpenings(True, True, True, True))
        self.board.place_card(0, 0, start1)

        start2 = TunnelCard("Start2", CardOpenings(True, True, True, True))
        self.board.place_card(0, 2, start2)

        self._deal_initial_cards()

    def _create_deck(self) -> List[TunnelCard]:
        deck = []
        # Простая генерация колоды для прототипа
        for _ in range(10):
            deck.append(TunnelCard("Vertical", CardOpenings(up=True, down=True)))
        for _ in range(10):
            deck.append(TunnelCard("Horizontal", CardOpenings(left=True, right=True)))
        for _ in range(10):
            deck.append(TunnelCard("Turn L-D", CardOpenings(left=True, down=True)))
        for _ in range(10):
            deck.append(TunnelCard("Turn U-R", CardOpenings(up=True, right=True)))
        for _ in range(5):
            deck.append(TunnelCard("Cross", CardOpenings(True, True, True, True)))

        random.shuffle(deck)
        return deck

    def _deal_initial_cards(self):
#        [cite_start] [cite: 42] Раздайте по 6 карточек
        for p in self.players:
            for _ in range(6):
                if self.deck:
                    self.hands[p].append(self.deck.pop())

    def play_turn(self, card_idx: int, x: int, y: int):
        hand = self.hands[self.current_player]
        if card_idx < 0 or card_idx >= len(hand):
            print("Неверный номер карты.")
            return

        card_to_play = hand[card_idx]
        print(f"\nИгрок {self.current_player} ставит {card_to_play.name} на ({x}, {y})...")

        if self.board.is_move_valid(x, y, card_to_play):
            self.board.place_card(x, y, card_to_play)
            hand.pop(card_idx)

            #[cite_start]  [cite: 50] Добрать 1 карту после хода
            if self.deck:
                hand.append(self.deck.pop())

            self.current_player = 1 - self.current_player
            print("Ход успешен.")
        else:
            print("Ход недопустим (не стыкуются туннели или занято).")

    def check_possible_moves_at(self, x: int, y: int):
        hand = self.hands[self.current_player]
        available_cards = []

        print(f"\n--- Анализ клетки ({x}, {y}) для Игрока {self.current_player} ---")
        for i, card in enumerate(hand):
            if self.board.is_move_valid(x, y, card):
                available_cards.append((i, card))
                print(f"  [{i}] Можно сыграть: {card.name} {card}")

        if not available_cards:
            print("  Нет подходящих карт для этой клетки.")
        return available_cards

    def print_state(self):
        if not self.board.grid:
            return

        xs = [k[0] for k in self.board.grid.keys()]
        ys = [k[1] for k in self.board.grid.keys()]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        print("\nПоле:")
        header = "    " + " ".join([f"{x:2}" for x in range(min_x - 1, max_x + 2)])
        print(header)

        for y in range(min_y - 1, max_y + 2):
            line = f"{y:2} "
            for x in range(min_x - 1, max_x + 2):
                card = self.board.get_card(x, y)
                line += f"[ {str(card).strip()} ]" if card else "[ . ]"
            print(line)