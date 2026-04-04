from typing import Dict, List, Optional, Set, Tuple
from cards import EquipmentType


# ✅ ПОЛНОСТЬЮ КОПИРУЕМ ИЗ ВАШЕГО КОДА (с добавлениями)
class PlacedCard:
    """Карта, помещённая на доску."""
    __slots__ = ['template_id', 'owner_id', 'is_rotated_180', 'is_locked', 'is_revealed']

    def __init__(self, template_id: str, owner_id: Optional[int] = None,
                 is_rotated_180: bool = False, is_locked: bool = False, is_revealed: bool = False):
        self.template_id = template_id
        self.owner_id = owner_id
        self.is_rotated_180 = is_rotated_180
        self.is_locked = is_locked
        self.is_revealed = is_revealed

    def clone(self) -> 'PlacedCard':
        """Создаёт независимую копию карты."""
        return PlacedCard(
            self.template_id, self.owner_id,
            self.is_rotated_180, self.is_locked, self.is_revealed
        )


class PlayerState:
    """Состояние одного игрока."""
    __slots__ = ['player_id', 'hand', 'broken_equipments', 'known_secrets', 'ladders']

    def __init__(self, player_id: int):
        self.player_id = player_id
        self.hand: List[str] = []  # ID карт в руке
        self.broken_equipments: Set[EquipmentType] = set()  # Сломанные инструменты
        self.known_secrets: Set[Tuple[int, int]] = set()  # ⚠️ КОРТЕЖИ, не строки!
        self.ladders: Set[Tuple[int, int]] = set()  # ⚠️ КОРТЕЖИ, не строки!

    def clone(self) -> 'PlayerState':
        """Создаёт независимую копию состояния игрока."""
        new_p = PlayerState(self.player_id)
        new_p.hand = self.hand.copy()
        new_p.broken_equipments = self.broken_equipments.copy()
        new_p.known_secrets = self.known_secrets.copy()  # Копируем сет кортежей
        new_p.ladders = self.ladders.copy()  # Копируем сет кортежей
        return new_p


class MatchState:
    """Полное состояние игры."""
    __slots__ = ['board', 'players', 'current_player_id', 'deck', 'gold_deck',
                 'is_game_over', 'turn_number',
                 # ⬇️ ДОБАВЛЕНЫ ПОЛЯ VKRTEMP:
                 'round_number', 'first_player_in_round', 'total_scores', 'round_scores',
                 # ⬇️ ДОБАВЛЕНЫ ПОЛЯ ИЗ ВАШЕГО КОДА:
                 'board_update_count', 'cached_frontiers']

    def __init__(self):
        # Доска: координаты как КОРТЕЖИ (не строки!)
        self.board: Dict[Tuple[int, int], PlacedCard] = {}

        # Игроки
        self.players: Dict[int, PlayerState] = {0: PlayerState(0), 1: PlayerState(1)}

        # Общее состояние
        self.current_player_id: int = 0
        self.deck: List[str] = []  # Основная колода (ID карт)
        self.gold_deck: List[str] = []  # Колода золота (ID карт)
        self.is_game_over: bool = False
        self.turn_number: int = 1

        # ⬇️ ПОЛЯ VKRTEMP для многораундовой игры:
        self.round_number: int = 1
        self.first_player_in_round: int = 0  # Кто ходит первым в раунде
        self.total_scores: Dict[int, int] = {0: 0, 1: 0}  # Сумма очков за все раунды
        self.round_scores: Dict[int, int] = {0: 0, 1: 0}  # Очки текущего раунда

        # ⬇️ ПОЛЯ ИЗ ВАШЕГО КОДА для оптимизации:
        self.board_update_count: int = 0  # Счётчик изменений доски
        self.cached_frontiers: Dict[int, Tuple[int, Set[Tuple[int, int]]]] = {
            0: (-1, set()),
            1: (-1, set())
        }  # Кэш: {player_id: (версия, множество фронтира)}

    def clone(self) -> 'MatchState':
        """Создаёт независимую копию полного состояния игры."""
        new_state = MatchState()

        # Копируем доску (кортежи как ключи)
        new_state.board = {coord: card.clone() for coord, card in self.board.items()}

        # Копируем игроков
        new_state.players = {0: self.players[0].clone(), 1: self.players[1].clone()}

        # Копируем основные поля
        new_state.current_player_id = self.current_player_id
        new_state.deck = self.deck.copy()
        new_state.gold_deck = self.gold_deck.copy()
        new_state.is_game_over = self.is_game_over
        new_state.turn_number = self.turn_number

        # Копируем раунды и очки
        new_state.round_number = self.round_number
        new_state.first_player_in_round = self.first_player_in_round
        new_state.total_scores = self.total_scores.copy()
        new_state.round_scores = self.round_scores.copy()

        # Копируем кэш
        new_state.board_update_count = self.board_update_count
        new_state.cached_frontiers = {
            k: (v[0], v[1].copy()) for k, v in self.cached_frontiers.items()
        }

        return new_state


# ⬇️ КЛАССЫ ДЛЯ НАБЛЮДАТЕЛЯ (скрытие информации)
class ObservablePlayerState:
    """Состояние игрока, видимое для другого игрока (без скрытия руки)."""
    __slots__ = ['player_id', 'hand_size', 'broken_equipments', 'hand']

    def __init__(self, player_id: int, hand_size: int, broken_equipments: Set[EquipmentType],
                 hand: Optional[List[str]] = None):
        self.player_id = player_id
        self.hand_size = hand_size
        self.broken_equipments = broken_equipments
        self.hand = hand  # None для противника, список для нас


class ObservableMatchState:
    """Состояние игры для конкретного игрока (с маскировкой скрытого золота)."""
    __slots__ = ['board', 'players', 'current_player_id', 'deck_size', 'gold_deck_size',
                 'is_game_over', 'turn_number', 'round_number', 'total_scores']

    def __init__(self, board: Dict[Tuple[int, int], PlacedCard],
                 players: Dict[int, ObservablePlayerState],
                 current_player_id: int, deck_size: int, gold_deck_size: int,
                 is_game_over: bool, turn_number: int,
                 round_number: int = 1, total_scores: Optional[Dict[int, int]] = None):
        self.board = board
        self.players = players
        self.current_player_id = current_player_id
        self.deck_size = deck_size
        self.gold_deck_size = gold_deck_size
        self.is_game_over = is_game_over
        self.turn_number = turn_number
        self.round_number = round_number
        self.total_scores = total_scores or {0: 0, 1: 0}