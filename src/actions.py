from dataclasses import dataclass
from typing import Optional, Union, Tuple
from cards import EquipmentType

# Используем slots=True для ускорения доступа и экономии памяти,
# и frozen=True, чтобы действия были неизменяемыми (полезно для словарей/кеширования в MCTS).

@dataclass(slots=True, frozen=True)
class ActionBuild:
    """Действие: Построить туннель, лестницу или дверь."""
    template_id: str
    x: int
    y: int
    is_rotated_180: bool = False
    type: str = "build"

@dataclass(slots=True, frozen=True)
class ActionPlayBoardUtility:
    """Действие: Сыграть карту на поле (Обвал, Ключ, Карта сокровищ)."""
    template_id: str
    x: int
    y: int
    type: str = "play_board_utility"

@dataclass(slots=True, frozen=True)
class ActionPlayPlayerUtility:
    """Действие: Сыграть карту на игрока (Поломка, Починка)."""
    template_id: str
    target_player_id: int
    type: str = "play_player_utility"

@dataclass(slots=True, frozen=True)
class ActionDiscard:
    """Действие: Сбросить карты (обычный сброс 1-2 карт ИЛИ экстренная починка за 2 карты)."""
    # В dataclass валидации "на лету" нет, поэтому мы просто храним tuple/list
    # Рекомендуется передавать tuple для сохранения иммутабельности
    templates: Tuple[str, ...]
    repair_equipment: Optional[EquipmentType] = None
    type: str = "discard"

@dataclass(slots=True, frozen=True)
class ActionPass:
    """Действие: Пропустить ход (доступно ТОЛЬКО если рука пуста)."""
    type: str = "pass"

AgentAction = Union[
    ActionBuild,
    ActionPlayBoardUtility,
    ActionPlayPlayerUtility,
    ActionDiscard,
    ActionPass
]