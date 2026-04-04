from dataclasses import dataclass
from typing import Literal, Optional, Tuple, Union
from cards import EquipmentType


@dataclass(frozen=True)  # ✅ Неизменяемые действия для безопасности
class ActionBuild:
    """Действие: Построить туннель, лестницу или дверь."""
    type: Literal["build"] = "build"
    template_id: str = ""
    x: int = 0
    y: int = 0
    is_rotated_180: bool = False


@dataclass(frozen=True)
class ActionPlayBoardUtility:
    """Действие: Сыграть карту на поле (Обвал, Ключ, Карта сокровищ)."""
    type: Literal["play_board_utility"] = "play_board_utility"
    template_id: str = ""
    x: int = 0
    y: int = 0


@dataclass(frozen=True)
class ActionPlayPlayerUtility:
    """Действие: Сыграть карту на игрока (Поломка, Починка)."""
    type: Literal["play_player_utility"] = "play_player_utility"
    template_id: str = ""
    target_player_id: int = 0


@dataclass(frozen=True)
class ActionDiscard:
    """Действие: Сбросить карты (обычный сброс 1-2 карт ИЛИ экстренная починка за 2 карты)."""
    type: Literal["discard"] = "discard"
    templates: Tuple[str, ...] = ()              # ⚠️ КОРТЕЖ вместо List для неизменяемости
    repair_equipment: Optional[EquipmentType] = None

    def __post_init__(self):
        # Валидация: 1-2 карты
        if not (1 <= len(self.templates) <= 2):
            raise ValueError("Нужно 1-2 карты для сброса")


@dataclass(frozen=True)
class ActionPass:  # ⬇️ НОВОЕ ДЕЙСТВИЕ
    """Действие: Пропустить ход (когда в руке нет карт)."""
    type: Literal["pass"] = "pass"


# Union всех возможных действий
AgentAction = Union[
    ActionBuild,
    ActionPlayBoardUtility,
    ActionPlayPlayerUtility,
    ActionDiscard,
    ActionPass  # ⬇️ ДОБАВЛЕНО
]