import sys
from pathlib import Path
from typing import Dict, Any, Optional
import uuid

src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import requests
import uvicorn

sys.path.insert(0, str(src_path))

from game import Game
from actions import (
    AgentAction,
    ActionBuild,
    ActionPlayBoardUtility,
    ActionPlayPlayerUtility,
    ActionDiscard,
)


app = FastAPI(
    title="Гномы-вредители: API",
    description="""
# API для игры "Гномы-вредители: Дуэль"

## Описание
REST API для проведения игр между ботами. Поддерживает:
- Создание новых игр
- Получение состояния игры
- Выполнение ходов
- Управление ботами через webhook

## Архитектура
- Бот получает информацию о состоянии игры через API
- Бот отправляет выбранное действие через API
- Сервер валидирует и выполняет ходы
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ACTIVE_GAMES: Dict[str, Dict[str, Any]] = {}


class GameStartRequest(BaseModel):
    """Запрос на создание новой игры"""

    bot1_code: str = Field(..., description="Python код первого бота")
    bot2_code: str = Field(..., description="Python код второго бота")
    bot1_url: Optional[str] = Field(None, description="URL webhook первого бота")
    bot2_url: Optional[str] = Field(None, description="URL webhook второго бота")


class ActionRequest(BaseModel):
    """Запрос на выполнение хода"""

    player_id: int = Field(..., description="ID игрока (0 или 1)")
    action: Dict[str, Any] = Field(..., description="Действие в JSON формате")


def game_to_json(game: Game, player_id: int) -> Dict[str, Any]:
    legal_actions = game.get_legal_actions()

    actions_json = []
    for action in legal_actions:
        action_dict = {"type": action.type}

        if isinstance(action, ActionBuild):
            action_dict.update(
                {
                    "template_id": action.template_id,
                    "x": action.x,
                    "y": action.y,
                    "is_rotated_180": action.is_rotated_180,
                }
            )
        elif isinstance(action, ActionPlayBoardUtility):
            action_dict.update(
                {
                    "template_id": action.template_id,
                    "x": action.x,
                    "y": action.y,
                }
            )
        elif isinstance(action, ActionPlayPlayerUtility):
            action_dict.update(
                {
                    "template_id": action.template_id,
                    "target_player_id": action.target_player_id,
                }
            )
        elif isinstance(action, ActionDiscard):
            action_dict.update(
                {
                    "templates": action.templates,
                    "repair_equipment": action.repair_equipment.value
                    if action.repair_equipment
                    else None,
                }
            )

        actions_json.append(action_dict)

    player_state = game.state.players[player_id]

    return {
        "game_id": "",
        "player_id": player_id,
        "round": game.state.round_number,
        "turn": game.state.turn_number,
        "current_player": game.state.current_player_id,
        "scores": game.state.total_scores,
        "hand": player_state.hand,
        "broken_equipments": [e.value for e in player_state.broken_equipments],
        "known_secrets": list(player_state.known_secrets),
        "legal_actions": actions_json,
        "is_game_over": game.is_game_over(),
    }


def action_from_json(action_dict: Dict[str, Any]) -> AgentAction:
    action_type = action_dict.get("type", "")

    if action_type == "build":
        return ActionBuild(
            template_id=action_dict["template_id"],
            x=action_dict["x"],
            y=action_dict["y"],
            is_rotated_180=action_dict.get("is_rotated_180", False),
        )
    elif action_type == "play_board":
        return ActionPlayBoardUtility(
            template_id=action_dict["template_id"],
            x=action_dict["x"],
            y=action_dict["y"],
        )
    elif action_type == "play_player":
        return ActionPlayPlayerUtility(
            template_id=action_dict["template_id"],
            target_player_id=action_dict["target_player_id"],
        )
    elif action_type == "discard":
        from cards import EquipmentType

        repair_eq = None
        if action_dict.get("repair_equipment"):
            repair_eq = EquipmentType(action_dict["repair_equipment"])
        return ActionDiscard(
            templates=action_dict["templates"],
            repair_equipment=repair_eq,
        )

    raise ValueError(f"Unknown action type: {action_type}")


def notify_bot(url: str, game_id: str, game_state: Dict) -> Optional[Dict]:
    try:
        resp = requests.post(
            f"{url}/choose", json={"game_state": game_state}, timeout=30
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Failed to notify bot: {e}")
    return None


@app.get("/health")
def health():
    """
    Проверка здоровья API.
    Возвращает статус сервера и количество активных игр.
    """
    return {"status": "ok", "games": len(ACTIVE_GAMES)}


@app.post(
    "/games",
    summary="Создать новую игру",
    description="Запускает новую игру между двумя ботами",
)
def start_game(req: GameStartRequest):
    """
    Создать новую игру.

    **Параметры:**
    - `bot1_code` - код Python для первого бота
    - `bot2_code` - код Python для второго бота
    - `bot1_url` - (опционально) URL webhook для первого бота
    - `bot2_url` - (опционально) URL webhook для второго бота

    **Возвращает:**
    - `game_id` - ID созданной игры
    - `state` - начальное состояние игры
    """
    game_id = str(uuid.uuid4())

    game = Game()
    game_id_holder = {"id": game_id}
    game.state.metadata = game_id_holder

    if req.bot1_url:
        try:
            requests.post(
                f"{req.bot1_url}/init",
                json={"code": req.bot1_code, "player_id": 0},
                timeout=10,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to init bot1: {e}")

    if req.bot2_url:
        try:
            requests.post(
                f"{req.bot2_url}/init",
                json={"code": req.bot2_code, "player_id": 1},
                timeout=10,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to init bot2: {e}")

    ACTIVE_GAMES[game_id] = {
        "game": game,
        "bot1_code": req.bot1_code,
        "bot2_code": req.bot2_code,
        "bot1_url": req.bot1_url,
        "bot2_url": req.bot2_url,
    }

    state = game_to_json(game, game.state.current_player_id)
    state["game_id"] = game_id

    if game.state.current_player_id == 0 and req.bot1_url:
        notify_bot(req.bot1_url, game_id, state)
    elif game.state.current_player_id == 1 and req.bot2_url:
        notify_bot(req.bot2_url, game_id, state)

    return {"game_id": game_id, "state": state}


@app.get(
    "/games/{game_id}",
    summary="Получить состояние игры",
    description="Возвращает состояние игры для текущего игрока",
)
def get_game(game_id: str):
    """
    Получить состояние игры для текущего игрока.

    **Параметры:**
    - `game_id` - ID игры

    **Возвращает:**
    - Состояние игры для текущего игрока (рука, легальные ходы и т.д.)
    """
    if game_id not in ACTIVE_GAMES:
        raise HTTPException(status_code=404, detail="Game not found")

    game = ACTIVE_GAMES[game_id]["game"]
    player_id = game.state.current_player_id

    state = game_to_json(game, player_id)
    state["game_id"] = game_id

    return state


@app.get(
    "/games/{game_id}/state",
    summary="Получить полное состояние",
    description="Возвращает состояние игры для обоих игроков",
)
def get_game_state(game_id: str):
    """
    Получить полное состояние игры для обоих игроков.

    **Параметры:**
    - `game_id` - ID игры

    **Возвращает:**
    - Состояние для игрока 0 и игрока 1
    """
    if game_id not in ACTIVE_GAMES:
        raise HTTPException(status_code=404, detail="Game not found")

    game = ACTIVE_GAMES[game_id]["game"]

    states = {}
    for pid in [0, 1]:
        states[pid] = game_to_json(game, pid)

    return {
        "game_id": game_id,
        "current_player": game.state.current_player_id,
        "states": states,
    }


@app.get(
    "/games/{game_id}/legal-actions",
    summary="Получить легальные ходы",
    description="Возвращает список возможных ходов для текущего игрока",
)
def get_legal_actions(game_id: str):
    """
    Получить легальные ходы для текущего игрока.

    **Параметры:**
    - `game_id` - ID игры

    **Возвращает:**
    - Список легальных ходов
    """
    if game_id not in ACTIVE_GAMES:
        raise HTTPException(status_code=404, detail="Game not found")

    game = ACTIVE_GAMES[game_id]["game"]
    player_id = game.state.current_player_id

    return {
        "game_id": game_id,
        "player_id": player_id,
        "legal_actions": game_to_json(game, player_id)["legal_actions"],
    }


@app.post(
    "/games/{game_id}/action",
    summary="Совершить ход",
    description="Выполняет ход игрока",
)
def submit_action(game_id: str, req: ActionRequest):
    """
    Совершить ход в игре.

    **Параметры:**
    - `game_id` - ID игры
    - `player_id` - ID игрока (0 или 1)
    - `action` - действие в формате JSON

    **Типы действий:**
    ```json
    // Постройка
    {"type": "build", "template_id": "tunnel_corner", "x": 0, "y": -1, "is_rotated_180": false}

    // Утилита на поле
    {"type": "play_board", "template_id": "act_key", "x": 0, "y": -1}

    // Утилита на игрока
    {"type": "play_player", "template_id": "act_sabotage", "target_player_id": 1}

    // Сброс карт
    {"type": "discard", "templates": ["tunnel_corner"]}
    ```
    """
    if game_id not in ACTIVE_GAMES:
        raise HTTPException(status_code=404, detail="Game not found")

    game_data = ACTIVE_GAMES[game_id]
    game = game_data["game"]

    if req.player_id != game.state.current_player_id:
        raise HTTPException(status_code=400, detail="Not your turn")

    try:
        action = action_from_json(req.action)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid action: {e}")

    success, msg, gold = game.step(action)

    if not success:
        raise HTTPException(status_code=400, detail=msg)

    state = game_to_json(game, game.state.current_player_id)
    state["game_id"] = game_id
    state["last_action"] = {"success": True, "message": msg, "gold_found": gold}

    if game.is_game_over():
        return {
            "game_over": True,
            "winner": game.state.total_scores[0] > game.state.total_scores[1],
            "scores": game.state.total_scores,
            "state": state,
        }

    next_player = game.state.current_player
    if next_player == 0 and game_data["bot1_url"]:
        notify_bot(game_data["bot1_url"], game_id, state)
    elif next_player == 1 and game_data["bot2_url"]:
        notify_bot(game_data["bot2_url"], game_id, state)

    return state


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
