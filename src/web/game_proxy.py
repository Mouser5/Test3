from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class ActionBuild:
    type: str = "build"
    template_id: str = ""
    x: int = 0
    y: int = 0
    is_rotated_180: bool = False


@dataclass
class ActionPlayBoardUtility:
    type: str = "play_board"
    template_id: str = ""
    x: int = 0
    y: int = 0


@dataclass
class ActionPlayPlayerUtility:
    type: str = "play_player"
    template_id: str = ""
    target_player_id: int = 0


@dataclass
class ActionDiscard:
    type: str = "discard"
    templates: List[str] = None
    repair_equipment: Optional[str] = None

    def __post_init__(self):
        if self.templates is None:
            self.templates = []


class GameProxy:
    """
    Proxy object for bot to interact with the game.
    Provides minimal interface needed for choose_action without
    exposing the full game state.
    """

    def __init__(self, game_state: Dict[str, Any], legal_actions: List[Dict]):
        self._game_state = game_state
        self._legal_actions = legal_actions
        self.player_id = game_state.get("player_id", 0)

    @classmethod
    def from_state(cls, state_json: Dict[str, Any]) -> "GameProxy":
        legal_actions = state_json.get("legal_actions", [])
        return cls(state_json, legal_actions)

    def get_legal_actions(self) -> List[Any]:
        actions = []

        for action_dict in self._legal_actions:
            action_type = action_dict.get("type", "")

            if action_type == "build":
                actions.append(
                    ActionBuild(
                        template_id=action_dict.get("template_id", ""),
                        x=action_dict.get("x", 0),
                        y=action_dict.get("y", 0),
                        is_rotated_180=action_dict.get("is_rotated_180", False),
                    )
                )
            elif action_type == "play_board":
                actions.append(
                    ActionPlayBoardUtility(
                        template_id=action_dict.get("template_id", ""),
                        x=action_dict.get("x", 0),
                        y=action_dict.get("y", 0),
                    )
                )
            elif action_type == "play_player":
                actions.append(
                    ActionPlayPlayerUtility(
                        template_id=action_dict.get("template_id", ""),
                        target_player_id=action_dict.get("target_player_id", 0),
                    )
                )
            elif action_type == "discard":
                actions.append(
                    ActionDiscard(
                        templates=action_dict.get("templates", []),
                        repair_equipment=action_dict.get("repair_equipment"),
                    )
                )

        return actions

    def get_hand(self) -> List[str]:
        return self._game_state.get("hand", [])

    def get_board(self) -> Dict[str, Dict]:
        return self._game_state.get("board", {})

    def get_broken_equipments(self, player_id: int) -> List[str]:
        return self._game_state.get("players_broken", {}).get(player_id, [])

    def get_scores(self) -> Dict[int, int]:
        return self._game_state.get("scores", {0: 0, 1: 0})

    def get_current_player(self) -> int:
        return self._game_state.get("current_player", 0)

    def is_game_over(self) -> bool:
        return self._game_state.get("is_game_over", False)
