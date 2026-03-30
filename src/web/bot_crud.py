from sqlalchemy.orm import Session
from typing import List, Optional

from web.models import Bot, GameResult
from web.schemas import BotCreate, GameResultCreate


def create_bot(db: Session, user_id: int, bot_data: BotCreate) -> Bot:
    db_bot = Bot(user_id=user_id, name=bot_data.name, code=bot_data.code)
    db.add(db_bot)
    db.commit()
    db.refresh(db_bot)
    return db_bot


def get_user_bots(
    db: Session, user_id: int, skip: int = 0, limit: int = 100
) -> List[Bot]:
    return (
        db.query(Bot)
        .filter(Bot.user_id == user_id)
        .order_by(Bot.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_bot_by_id(db: Session, bot_id: int) -> Optional[Bot]:
    return db.query(Bot).filter(Bot.id == bot_id).first()


def delete_bot(db: Session, bot_id: int, user_id: int) -> bool:
    bot = db.query(Bot).filter(Bot.id == bot_id, Bot.user_id == user_id).first()
    if not bot:
        return False
    db.delete(bot)
    db.commit()
    return True


def save_game_result(
    db: Session, user_id: int, result_data: GameResultCreate
) -> GameResult:
    db_result = GameResult(
        user_id=user_id,
        bot_id=result_data.bot_id,
        opponent_type=result_data.opponent_type,
        opponent_id=result_data.opponent_id,
        result=result_data.result,
        user_score=result_data.user_score,
        opponent_score=result_data.opponent_score,
        turns=result_data.turns,
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result


def get_user_game_history(
    db: Session, user_id: int, skip: int = 0, limit: int = 50
) -> List[GameResult]:
    return (
        db.query(GameResult)
        .filter(GameResult.user_id == user_id)
        .order_by(GameResult.played_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_bot_stats(db: Session, bot_id: int) -> dict:
    results = db.query(GameResult).filter(GameResult.bot_id == bot_id).all()

    if not results:
        return {"total": 0, "wins": 0, "losses": 0, "draws": 0, "win_rate": 0.0}

    wins = sum(1 for r in results if r.result == "win")
    losses = sum(1 for r in results if r.result == "loss")
    draws = sum(1 for r in results if r.result == "draw")

    return {
        "total": len(results),
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate": wins / len(results) * 100 if results else 0.0,
    }
