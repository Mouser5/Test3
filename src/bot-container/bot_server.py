import os
import sys

sys.path.insert(0, "/app/src")
import importlib.util
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import uvicorn
import requests

GAME_API_URL = os.getenv("GAME_API_URL", "http://game-api:8000")

app = FastAPI()

AGENT_CLASS = None
AGENT_INSTANCE = None
REDIS_LISTENER = None


def load_agent_from_code(code: str):
    global AGENT_CLASS, AGENT_INSTANCE

    module_name = "bot_agent"
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(module_name, loader=None)
    )
    sys.modules[module_name] = module

    exec(compile(code, "<bot_code>", "exec"), module.__dict__)

    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, type) and hasattr(obj, "choose_action"):
            AGENT_CLASS = obj
            break

    if AGENT_CLASS:
        AGENT_INSTANCE = AGENT_CLASS(player_id=0)
        return True
    return False


class InitRequest(BaseModel):
    code: str
    player_id: int = 0


class InitRedisRequest(BaseModel):
    code: str
    player_id: int = 0
    redis_url: str = "redis://redis:6379/0"
    game_id: str = ""


class ActionRequest(BaseModel):
    game_id: str
    action: Dict[str, Any]


class ChooseRequest(BaseModel):
    game_state: Dict[str, Any]


@app.get("/health")
def health():
    return {
        "status": "ok",
        "agent_loaded": AGENT_CLASS is not None,
        "redis_listener_active": REDIS_LISTENER is not None,
    }


@app.post("/init")
def init(req: InitRequest):
    if not req.code:
        raise HTTPException(status_code=400, detail="No code provided")

    if load_agent_from_code(req.code):
        global AGENT_INSTANCE
        AGENT_INSTANCE = AGENT_CLASS(player_id=req.player_id)
        return {"status": "initialized", "player_id": req.player_id}

    raise HTTPException(status_code=400, detail="Failed to load agent")


@app.post("/init_redis")
def init_redis(req: InitRedisRequest):
    global AGENT_INSTANCE, REDIS_LISTENER

    if not req.code:
        raise HTTPException(status_code=400, detail="No code provided")
    if not req.game_id:
        raise HTTPException(status_code=400, detail="No game_id provided")

    if not load_agent_from_code(req.code):
        raise HTTPException(status_code=400, detail="Failed to load agent")

    AGENT_INSTANCE = AGENT_CLASS(player_id=req.player_id)

    from bot_redis import start_listener_thread

    REDIS_LISTENER = start_listener_thread(
        redis_url=req.redis_url,
        game_id=req.game_id,
        agent_instance=AGENT_INSTANCE,
        player_id=req.player_id,
    )

    return {
        "status": "initialized",
        "player_id": req.player_id,
        "game_id": req.game_id,
        "redis_url": req.redis_url,
    }


@app.get("/game/state")
def get_game_state(game_id: str):
    if not game_id:
        raise HTTPException(status_code=400, detail="No game_id provided")

    try:
        resp = requests.get(f"{GAME_API_URL}/games/{game_id}/state", timeout=5)
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/game/action")
def submit_action(req: ActionRequest):
    if not req.game_id or not req.action:
        raise HTTPException(status_code=400, detail="Missing game_id or action")

    try:
        resp = requests.post(
            f"{GAME_API_URL}/games/{req.game_id}/action",
            json={"player_id": 0, "action": req.action},
            timeout=10,
        )
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/choose")
def choose_action(req: ChooseRequest):
    if not AGENT_INSTANCE:
        raise HTTPException(status_code=400, detail="Agent not initialized")

    if not req.game_state:
        raise HTTPException(status_code=400, detail="No game_state provided")

    try:
        sys.path.insert(0, "/app/src")
        from web.game_proxy import GameProxy

        game = GameProxy.from_state(req.game_state)
        action = AGENT_INSTANCE.choose_action(game)

        if action is None:
            return {"action": None, "reason": "no_legal_actions"}

        result = {
            "type": type(action).__name__,
            "template_id": getattr(action, "template_id", None),
            "x": getattr(action, "x", None),
            "y": getattr(action, "y", None),
            "is_rotated_180": getattr(action, "is_rotated_180", False),
            "templates": getattr(action, "templates", None),
            "repair_equipment": getattr(action, "repair_equipment", None),
        }
        return {"action": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
