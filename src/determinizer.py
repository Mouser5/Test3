"""
Детерминизатор для работы с частичной информацией в MCTS.
ОПТИМИЗИРОВАННАЯ ВЕРСИЯ: Использует кэширование базовой колоды.
"""

import random
from typing import Dict, List, Tuple, Optional, Set
from state import MatchState, PlayerState, PlacedCard
from cards import GoldCardTemplate
from registry import REGISTRY


class Determinizer:
    """Генерирует и управляет возможными скрытыми состояниями для MCTS."""

    _BASE_DECK_CACHE: Optional[List[str]] = None

    @classmethod
    def _get_base_deck(cls) -> List[str]:
        if cls._BASE_DECK_CACHE is None:
            deck_composition = {
                "tunnel_cross": 10, "tunnel_t": 10, "tunnel_straight": 8,
                "tunnel_corner": 10, "tunnel_deadend": 4,
                "tunnel_bridge": 4, "tunnel_double_corner": 4,
                "tunnel_split_t_up": 4, "tunnel_split_t_l": 4,
                "door_blue": 3, "door_green": 3, "ladder": 4,
                "act_boom": 3, "act_key": 3, "act_map": 4
            }
            for eq_name in ["LAMP", "CART", "PICKAXE"]:
                deck_composition[f"brk_{eq_name}"] = 3
                deck_composition[f"rep_{eq_name}"] = 3

            cards = []
            for card_id, count in deck_composition.items():
                cards.extend([card_id] * count)
            cls._BASE_DECK_CACHE = cards

        return cls._BASE_DECK_CACHE.copy()

    @staticmethod
    def create_hypothetical_state(
        observed_state: MatchState,
        known_player_id: int,
        unknown_opponent_hand_size: int,
        unknown_gold_cards: List[Tuple[Tuple[int, int], str]]
    ) -> MatchState:

        state = observed_state.clone()
        opponent_id = 1 - known_player_id

        # O(1) получение базовой колоды
        available_cards = Determinizer._get_base_deck()

        # O(N) Быстрое удаление известных карт (через флаги/счетчики лучше, но remove терпимо для 74 карт)
        for card_id in state.players[known_player_id].hand:
            if card_id in available_cards:
                available_cards.remove(card_id)

        for placed in state.board.values():
            if placed.template_id != "hidden_gold":
                tpl = REGISTRY.get(placed.template_id)
                if not isinstance(tpl, GoldCardTemplate):
                    if placed.template_id in available_cards:
                        available_cards.remove(placed.template_id)

        random.shuffle(available_cards)

        opponent_hand = available_cards[:unknown_opponent_hand_size]
        state.players[opponent_id].hand = opponent_hand

        for coord, gold_id in unknown_gold_cards:
            state.board[coord] = PlacedCard(template_id=gold_id, owner_id=None, is_revealed=False)

        return state

    @staticmethod
    def infer_opponent_hand_size(observed_state: MatchState, known_player_id: int) -> int:
        opponent_id = 1 - known_player_id
        opponent = observed_state.players[opponent_id]
        return len(opponent.hand) if opponent.hand else 0

    @staticmethod
    def infer_hidden_gold(observed_state: MatchState) -> List[Tuple[Tuple[int, int], str]]:
        hidden_gold = []
        for coord, placed in observed_state.board.items():
            tpl = REGISTRY.get(placed.template_id)
            if isinstance(tpl, GoldCardTemplate) and not placed.is_revealed:
                hidden_gold.append((coord, placed.template_id))
        return hidden_gold

    @staticmethod
    def create_random_hypothesis(
        observed_state: MatchState,
        known_player_id: int
    ) -> MatchState:
        opponent_id = 1 - known_player_id
        opponent_hand_size = len(observed_state.players[opponent_id].hand)
        hidden_gold = Determinizer.infer_hidden_gold(observed_state)

        return Determinizer.create_hypothetical_state(
            observed_state, known_player_id, opponent_hand_size, hidden_gold
        )