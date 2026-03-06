from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Set
from cards import EquipmentType

class PlacedCard(BaseModel):
    template_id: str
    owner_id: Optional[int] = None
    is_rotated_180: bool = False
    is_locked: bool = False
    is_revealed: bool = False

class PlayerState(BaseModel):
    player_id: int
    hand: List[str] = Field(default_factory=list)
    broken_equipments: Set[EquipmentType] = Field(default_factory=set)
    known_secrets: Set[str] = Field(default_factory=set)
    ladders: Set[str] = Field(default_factory=set) # ИСПРАВЛЕНИЕ: O(1) доступ к лестницам

class MatchState(BaseModel):
    board: Dict[str, PlacedCard] = Field(default_factory=dict)
    players: Dict[int, PlayerState] = Field(default_factory=dict)
    current_player_id: int = 0
    deck: List[str] = Field(default_factory=list)
    gold_deck: List[str] = Field(default_factory=list)
    is_game_over: bool = False
    turn_number: int = 1

class ObservablePlayerState(BaseModel):
    player_id: int
    hand: Optional[List[str]] = None
    hand_size: int
    broken_equipments: Set[EquipmentType]

class ObservableMatchState(BaseModel):
    board: Dict[str, PlacedCard]
    players: Dict[int, ObservablePlayerState]
    current_player_id: int
    deck_size: int
    gold_deck_size: int
    is_game_over: bool
    turn_number: int