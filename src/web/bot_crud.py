from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict

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


def get_latest_bots_from_all_users(db: Session) -> List[Bot]:
    """Получить последний бот от каждого пользователя"""
    subquery = (
        db.query(Bot.user_id, func.max(Bot.created_at).label("max_date"))
        .group_by(Bot.user_id)
        .subquery()
    )

    return (
        db.query(Bot)
        .join(
            subquery,
            (Bot.user_id == subquery.c.user_id)
            & (Bot.created_at == subquery.c.max_date),
        )
        .order_by(Bot.user_id)
        .all()
    )


def get_all_bots_grouped_by_user(db: Session) -> Dict[int, List[Bot]]:
    """Получить все боты, сгруппированные по user_id"""
    bots = db.query(Bot).order_by(Bot.user_id, Bot.created_at.desc()).all()

    grouped: Dict[int, List[Bot]] = {}
    for bot in bots:
        if bot.user_id not in grouped:
            grouped[bot.user_id] = []
        grouped[bot.user_id].append(bot)

    return grouped


def get_all_game_history(
    db: Session, skip: int = 0, limit: int = 100
) -> List[GameResult]:
    """Получить все игры (для админа)"""
    return (
        db.query(GameResult)
        .order_by(GameResult.played_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
