import random
from typing import List, Dict, Tuple
from cards import TunnelCard, CardOpenings
from board import GameBoard


class Game:
    def __init__(self):
        self.board = GameBoard()
        self.players = [0, 1]
        self.current_player = 0
        self.deck = self._create_deck()
        self.hands: Dict[int, List[TunnelCard]] = {0: [], 1: []}

        start1 = TunnelCard("Start1", CardOpenings(True, True, True, True))
        self.board.place_card(0, 0, start1)
        start2 = TunnelCard("Start2", CardOpenings(True, True, True, True))
        self.board.place_card(0, 2, start2)

        self._deal_initial_cards()

    def _create_deck(self) -> List[TunnelCard]:
        deck = []
        for _ in range(10): deck.append(TunnelCard("Vertical", CardOpenings(up=True, down=True)))
        for _ in range(10): deck.append(TunnelCard("Horizontal", CardOpenings(left=True, right=True)))
        for _ in range(10): deck.append(TunnelCard("Turn L-D", CardOpenings(left=True, down=True)))
        for _ in range(10): deck.append(TunnelCard("Turn U-R", CardOpenings(up=True, right=True)))
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
            print(f"Карта была повернута!")

        if self.board.is_move_valid(x, y, card_to_play):
            self.board.place_card(x, y, card_to_play)
            hand.pop(card_idx)  # Удаляем из руки

            print(f"Игрок {self.current_player} поставил {card_to_play.name} на ({x}, {y})")

            if self.deck:
                hand.append(self.deck.pop())

            self.current_player = 1 - self.current_player
        else:
            print("Ошибка: Ход стал недопустимым (возможно, состояние изменилось).")
            if rotate_before_playing:
                card_to_play.rotate()

    def get_possible_moves_at(self, x: int, y: int) -> List[Tuple[int, TunnelCard, bool]]:
        hand = self.hands[self.current_player]
        possible_moves = []

        for idx, card in enumerate(hand):
            if self.board.is_move_valid(x, y, card):
                possible_moves.append((idx, card, False))

            rotated_copy = card.get_rotated_copy()

            if rotated_copy.openings != card.openings:
                if self.board.is_move_valid(x, y, rotated_copy):
                    possible_moves.append((idx, rotated_copy, True))

        return possible_moves

    def print_state(self):
        if not self.board.grid: return
        xs = [k[0] for k in self.board.grid.keys()]
        ys = [k[1] for k in self.board.grid.keys()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        print("\nПоле:")
        print("    " + " ".join([f"{x:2}  " for x in range(min_x - 1, max_x + 2)]))
        for y in range(min_y - 1, max_y + 2):
            line = f"{y:2} "
            for x in range(min_x - 1, max_x + 2):
                card = self.board.get_card(x, y)
                line += f"[ {str(card).strip()} ]" if card else "[ . ]"
            print(line)