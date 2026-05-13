from pydantic import BaseModel, Field
from typing import Literal, List, Optional, Union

from gnomes_dsl.cards import EquipmentType


class ActionBuild(BaseModel):
    type: Literal["build"] = "build"
    template_id: int
    x: int
    y: int
    is_rotated_180: bool = False


class ActionPlayBoardUtility(BaseModel):
    type: Literal["play_board_utility"] = "play_board_utility"
    template_id: int
    x: int
    y: int


class ActionPlayPlayerUtility(BaseModel):
    type: Literal["play_player_utility"] = "play_player_utility"
    template_id: int
    target_player_id: int


class ActionDiscard(BaseModel):
    type: Literal["discard"] = "discard"
    templates: List[int] = Field(..., min_length=1, max_length=2)
    repair_equipment: Optional[EquipmentType] = None


AgentAction = Union[
    ActionBuild, ActionPlayBoardUtility, ActionPlayPlayerUtility, ActionDiscard
]
