import sys
import os
from loguru import logger
from pathlib import Path

LOG_DIR = Path(os.getenv("LOG_DIR", "/app/logs"))
LOG_DIR.mkdir(exist_ok=True)

logger.remove()

logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)

logger.add(
    LOG_DIR / "game_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
)

logger.add(
    LOG_DIR / "error_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR",
)


def log_game_start(game_id: str, bot1_name: str, bot2_name: str):
    logger.info(
        f"🎮 Игра началась | game_id={game_id} | bot1={bot1_name} vs bot2={bot2_name}"
    )


def log_game_end(game_id: str, winner: str, scores: dict, turns: int):
    logger.info(
        f"🏁 Игра завершена | game_id={game_id} | winner={winner} | scores={scores} | turns={turns}"
    )


def log_game_error(game_id: str, error: str):
    logger.error(f"❌ Ошибка игры | game_id={game_id} | error={error}")


def log_bot_upload(user_id: int, bot_name: str, bot_id: int):
    logger.info(
        f"📤 Бот загружен | user_id={user_id} | bot_name={bot_name} | bot_id={bot_id}"
    )


def log_bot_load_for_game(bot_id: int, bot_name: str):
    logger.info(f"🤖 Загрузка бота для игры | bot_id={bot_id} | bot_name={bot_name}")


def log_bot_loaded(bot_id: int, bot_name: str, success: bool):
    if success:
        logger.success(
            f"✅ Бот загружен успешно | bot_id={bot_id} | bot_name={bot_name}"
        )
    else:
        logger.error(f"❌ Ошибка загрузки бота | bot_id={bot_id} | bot_name={bot_name}")


def log_player_turn(game_id: str, player_id: int, player_name: str, action_type: str):
    logger.debug(
        f"👤 Ход игрока | game_id={game_id} | player_id={player_id} | player={player_name} | action={action_type}"
    )


def log_action_result(game_id: str, player_id: int, success: bool, message: str):
    if success:
        logger.debug(
            f"✓ Действие выполнено | game_id={game_id} | player_id={player_id} | {message}"
        )
    else:
        logger.warning(
            f"✗ Действие отклонено | game_id={game_id} | player_id={player_id} | {message}"
        )


def log_container_start(container_id: str, bot_code: str = None):
    logger.info(
        f"🐳 Запуск контейнера бота | container_id={container_id} | код={'получен' if bot_code else 'не получен'}"
    )


def log_container_stop(container_id: str, reason: str = "завершение"):
    logger.info(
        f"🛑 Остановка контейнера бота | container_id={container_id} | причина={reason}"
    )


def log_container_error(container_id: str, error: str):
    logger.error(
        f"❌ Ошибка контейнера бота | container_id={container_id} | error={error}"
    )
