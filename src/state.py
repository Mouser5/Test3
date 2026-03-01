from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Set
from cards import EquipmentType


# --- МОДЕЛИ СОСТОЯНИЯ КАРТ НА ПОЛЕ ---

class PlacedCard(BaseModel):
    """
    Представляет карту, которая лежит на поле или в руке.
    Хранит только ссылку на неизменяемый шаблон и свое текущее состояние.
    """
    template_id: str  # Ссылка на ID из CardTemplate (например, "tunnel_cross")
    owner_id: Optional[int] = None  # Кто сыграл карту (0 или 1)

    # Изменяемое состояние карты
    is_rotated_180: bool = False  # Повернута ли карта
    is_locked: bool = False  # Только для дверей (DoorCardTemplate)
    is_revealed: bool = False  # Только для золота (GoldCardTemplate)


# --- МОДЕЛИ СОСТОЯНИЯ ИГРОКОВ И МАТЧА ---

class PlayerState(BaseModel):
    """
    Состояние конкретного игрока в текущий момент.
    """
    player_id: int
    hand: List[str] = Field(default_factory=list)  # Список template_id карт в руке
    broken_equipments: Set[EquipmentType] = Field(default_factory=set)  # Сломанные предметы


class MatchState(BaseModel):
    """
    Полный слепок состояния всей игры.
    Именно этот объект мы будем передавать ботам для принятия решений.
    """
    # Для максимальной совместимости с JSON API координаты ключей храним как строку "x,y"
    # (Pydantic и JSON плохо переваривают Tuple[int, int] в качестве ключей словаря)
    board: Dict[str, PlacedCard] = Field(default_factory=dict)

    players: Dict[int, PlayerState] = Field(default_factory=dict)
    current_player_id: int = 0

    # Колоды (хранят template_id)
    deck: List[str] = Field(default_factory=list)
    gold_deck: List[str] = Field(default_factory=list)

    # Глобальные статусы
    is_game_over: bool = False
    turn_number: int = 1