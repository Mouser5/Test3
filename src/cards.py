from pydantic import BaseModel, ConfigDict, Field
from enum import Enum
from typing import List, Optional, FrozenSet, Dict


class Direction(Enum):
    UP = (0, 1)
    DOWN = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)


class CardOpenings(BaseModel):
    model_config = ConfigDict(frozen=True)

    up: bool = False
    down: bool = False
    left: bool = False
    right: bool = False

    def get_opening(self, direction: Direction) -> bool:
        if direction == Direction.UP:
            return self.up
        if direction == Direction.DOWN:
            return self.down
        if direction == Direction.LEFT:
            return self.left
        if direction == Direction.RIGHT:
            return self.right
        return False


# --- БАЗОВЫЙ ШАБЛОН ---


class CardTemplate(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str  # Уникальный ID шаблона, например "tunnel_cross" или "action_boom"
    name: str


# --- ШАБЛОНЫ ПУТЕЙ ---


class PathCardTemplate(CardTemplate):
    openings: CardOpenings = Field(default_factory=CardOpenings)
    # Используем FrozenSet вместо Set для полной иммутабельности
    subnetworks: Optional[List[FrozenSet[Direction]]] = None

    # ✅ ИСПРАВЛЕНИЕ ШАГ 4: Кэш для get_exits
    # Используем class переменную (безопасно для frozen dataclass)
    exits_cache: Dict = Field(default_factory=dict, init=False, exclude=True)

    def model_post_init(self, __context):
        """Инициализация кэша после создания объекта."""
        object.__setattr__(self, 'exits_cache', {})

    def get_exits(self, entry_from: Optional[Direction]) -> FrozenSet[Direction]:
        """Возвращает выходы из карты. Результаты кэшируются."""
        # ✅ ИСПРАВЛЕНИЕ ШАГ 4: Проверить кэш перед вычислением
        cache = object.__getattribute__(self, 'exits_cache')
        if entry_from in cache:
            return cache[entry_from]

        # Вычислить все открытые выходы
        all_open = frozenset(d for d in Direction if self.openings.get_opening(d))

        # Если нет подсетей, просто вернуть открытые выходы
        if self.subnetworks is None:
            result = all_open
        elif entry_from is None:
            # Если нет входа, объединить все подсети
            result = frozenset(set().union(*self.subnetworks) & set(all_open))
        else:
            # Найти подсеть, содержащую вход
            result = frozenset()
            for net in self.subnetworks:
                if entry_from in net:
                    result = frozenset(net & set(all_open))
                    break

        # ✅ ИСПРАВЛЕНИЕ ШАГ 4: Сохранить в кэш
        cache[entry_from] = result
        return result


class TunnelCardTemplate(PathCardTemplate):
    pass


class StartCardTemplate(PathCardTemplate):
    pass


class DoorCardTemplate(PathCardTemplate):
    door_owner_id: int = 0


class LadderCardTemplate(PathCardTemplate):
    pass


class GoldCardTemplate(PathCardTemplate):
    gold_value: int = 0


# --- ШАБЛОНЫ ДЕЙСТВИЙ ---


class EquipmentType(Enum):
    LAMP = "Лампа"
    CART = "Вагонетка"
    PICKAXE = "Кирка"


class ActionType(Enum):
    KEY = "key"
    ROCKFALL = "rockfall"
    SABOTAGE = "sabotage"
    REPAIR = "repair"
    MAP = "map"


class ActionCardTemplate(CardTemplate):
    action_type: ActionType
    equipment_type: Optional[EquipmentType] = None