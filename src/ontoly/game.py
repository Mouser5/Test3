import random
from typing import List, Tuple
from ontol import GameState, PlayerState, TunnelCard, CardOpenings, GameMove, Direction, \
    Coordinates  # Импорт из онтологии


class Game:
    deck = []
    def __init__(self):
        # Создаем начальные карты (как в онтологии)
        start_openings = CardOpenings(up=True, down=True, left=True, right=True)
        start1 = TunnelCard(name="Start1", openings=start_openings)
        start2 = TunnelCard(name="Start2", openings=start_openings)

        initial_grid = {
            (0, 0): start1,
            (0, 2): start2
        }

        # Создаем колоду (как раньше, но с immutable картами)
        deck = self._create_deck()

        # Инициализируем состояние из онтологии
        player_0 = PlayerState(id=0, hand=tuple(deck.pop() for _ in range(6)))
        player_1 = PlayerState(id=1, hand=tuple(deck.pop() for _ in range(6)))

        self.state = GameState(
            grid=initial_grid,
            players={0: player_0, 1: player_1},
            current_player_id=0,
            deck_count=len(deck),
            _deck=deck  # Скрытая колода для симуляции
        )
        self.deck=deck

    def _create_deck(self) -> List[TunnelCard]:
        deck = []
        for _ in range(10): deck.append(TunnelCard(name="Vertical", openings=CardOpenings(up=True, down=True)))
        for _ in range(10): deck.append(TunnelCard(name="Horizontal", openings=CardOpenings(left=True, right=True)))
        for _ in range(10): deck.append(TunnelCard(name="Turn L-D", openings=CardOpenings(left=True, down=True)))
        for _ in range(10): deck.append(TunnelCard(name="Turn L-U", openings=CardOpenings(left=True, up=True)))
        for _ in range(5): deck.append(
            TunnelCard(name="Cross", openings=CardOpenings(up=True, down=True, left=True, right=True)))
        random.shuffle(deck)

        return deck

    def play_turn(self, card_idx: int, x: int, y: int, rotate_before_playing: bool = False):
        move = GameMove(x=x, y=y, card_idx=card_idx, rotate=rotate_before_playing)

        if self.state.is_move_valid(move):
            # Применяем ход — получаем новое состояние
            new_state = self.state.apply_move(move)

            # Обновляем текущее состояние (immutable, так что просто присваиваем)
            self.state = new_state

            # Если колода не пуста, добавляем карту (мутируем _deck, но не публичное состояние)
            if self.state.deck_count > 0 and self.deck:
                new_hand = list(self.state.current_player.hand)
                new_hand.append(self.deck.pop())
                new_player = self.state.current_player.model_copy(update={"hand": tuple(new_hand)})
                new_players = self.state.players.copy()
                new_players[self.state.current_player_id] = new_player
                self.state = self.state.model_copy(update={
                    "players": new_players,
                    "deck_count": len(self.deck)
                })

            print(f"Игрок {self.state.current_player_id} поставил карту на ({x}, {y})")
        else:
            print("Ошибка: Ход недопустим.")

    def get_possible_moves_at(self, x: int, y: int) -> List[Tuple[int, TunnelCard, bool]]:
        possible_moves = []
        hand = self.state.current_player.hand

        for idx, card in enumerate(hand):
            move = GameMove(x=x, y=y, card_idx=idx, rotate=False)
            if self.state.is_move_valid(move):
                possible_moves.append((idx, card, False))

            rotated_card = card.rotate()
            if rotated_card.openings != card.openings:  # Проверяем, изменилось ли
                move_rot = GameMove(x=x, y=y, card_idx=idx, rotate=True)
                if self.state.is_move_valid(move_rot):
                    possible_moves.append((idx, rotated_card, True))

        return possible_moves

    def print_state(self):
        if not self.state.grid: return
        xs = [k[0] for k in self.state.grid.keys()]
        ys = [k[1] for k in self.state.grid.keys()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        print("\nПоле:")
        print("    " + " ".join([f"{x:2}  " for x in range(min_x - 1, max_x + 2)]))
        for y in range(min_y - 1, max_y + 2):
            line = f"{y:2} "
            for x in range(min_x - 1, max_x + 2):
                card = self.state.get_card(x, y)
                line += f"[ {str(card).strip()} ]" if card else "[ . ]"
            print(line)