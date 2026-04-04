from typing import Dict, List, Optional, Set, Tuple
from cards import EquipmentType


class PlacedCard:
    __slots__ = ['template_id', 'owner_id', 'is_rotated_180', 'is_locked', 'is_revealed']

    def __init__(self, template_id: str, owner_id: Optional[int] = None,
                 is_rotated_180: bool = False, is_locked: bool = False, is_revealed: bool = False):
        self.template_id = template_id
        self.owner_id = owner_id
        self.is_rotated_180 = is_rotated_180
        self.is_locked = is_locked
        self.is_revealed = is_revealed

    def clone(self) -> 'PlacedCard':
        return PlacedCard(
            self.template_id, self.owner_id,
            self.is_rotated_180, self.is_locked, self.is_revealed
        )


class PlayerState:
    __slots__ = ['player_id', 'hand', 'broken_equipments', 'known_secrets', 'ladders']

    def __init__(self, player_id: int):
        self.player_id = player_id
        self.hand: List[str] = []
        self.broken_equipments: Set[EquipmentType] = set()
        self.known_secrets: Set[str] = set()
        self.ladders: Set[Tuple[int, int]] = set()

    def clone(self) -> 'PlayerState':
        new_p = PlayerState(self.player_id)
        new_p.hand = self.hand.copy()
        new_p.broken_equipments = self.broken_equipments.copy()
        new_p.known_secrets = self.known_secrets.copy()
        new_p.ladders = self.ladders.copy()
        return new_p


class MatchState:
    __slots__ = ['board', 'players', 'current_player_id', 'deck', 'gold_deck', 'is_game_over', 'turn_number',
                 'board_update_count', 'cached_frontiers']

    def __init__(self):
        self.board: Dict[Tuple[int, int], PlacedCard] = {}
        self.players: Dict[int, PlayerState] = {0: PlayerState(0), 1: PlayerState(1)}
        self.current_player_id: int = 0
        self.deck: List[str] = []
        self.gold_deck: List[str] = []
        self.is_game_over: bool = False
        self.turn_number: int = 1

        # НОВЫЕ ПОЛЯ ДЛЯ КЭШИРОВАНИЯ
        self.board_update_count: int = 0
        # Формат: {player_id: (board_version, set_of_frontier_coords)}
        self.cached_frontiers: Dict[int, Tuple[int, Set[Tuple[int, int]]]] = {
            0: (-1, set()),
            1: (-1, set())
        }

    def clone(self) -> 'MatchState':
        new_state = MatchState()
        new_state.board = {coord: card.clone() for coord, card in self.board.items()}
        new_state.players = {0: self.players[0].clone(), 1: self.players[1].clone()}
        new_state.current_player_id = self.current_player_id
        new_state.deck = self.deck.copy()
        new_state.gold_deck = self.gold_deck.copy()
        new_state.is_game_over = self.is_game_over
        new_state.turn_number = self.turn_number

        # КОПИРУЕМ КЭШ
        new_state.board_update_count = self.board_update_count
        # Поверхностное копирование сетов фронтира, чтобы независимые ветки MCTS не ломали кэш друг друга
        new_state.cached_frontiers = {k: (v[0], v[1].copy()) for k, v in self.cached_frontiers.items()}
        return new_state


class ObservablePlayerState:
    __slots__ = ['player_id', 'hand_size', 'broken_equipments', 'hand']

    def __init__(self, player_id: int, hand_size: int, broken_equipments: Set[EquipmentType],
                 hand: Optional[List[str]] = None):
        self.player_id = player_id
        self.hand_size = hand_size
        self.broken_equipments = broken_equipments
        self.hand = hand


class ObservableMatchState:
    __slots__ = ['board', 'players', 'current_player_id', 'deck_size', 'gold_deck_size', 'is_game_over', 'turn_number']

    def __init__(self, board: Dict[Tuple[int, int], PlacedCard], players: Dict[int, ObservablePlayerState],
                 current_player_id: int, deck_size: int, gold_deck_size: int, is_game_over: bool, turn_number: int):
        self.board = board
        self.players = players
        self.current_player_id = current_player_id
        self.deck_size = deck_size
        self.gold_deck_size = gold_deck_size
        self.is_game_over = is_game_over
        self.turn_number = turn_number