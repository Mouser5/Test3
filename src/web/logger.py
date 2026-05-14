import sys
from config import LOG_DIR
from loguru import logger

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


def log_tournament_end(
    tournament_id: int,
    tournament_name: str,
    total_games: int,
    total_turns: int,
    results: dict,
    elapsed_time: float,
):
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sorted_results = sorted(results.items(), key=lambda x: x[1]["wins"], reverse=True)

    logger.info("=" * 60)
    logger.info(f"🏆 ТУРНИР ЗАВЕРШЕН | {timestamp}")
    logger.info(f"   ID: {tournament_id}")
    logger.info(f"   Название: {tournament_name}")
    logger.info(f"   Всего игр: {total_games}")
    logger.info(f"   Всего ходов: {total_turns}")
    logger.info(f"   Время: {elapsed_time:.2f} сек")
    logger.info("-" * 60)
    logger.info("📊 РЕЗУЛЬТАТЫ:")

    for bot_name, stats in sorted_results:
        win_rate = (stats["wins"] / stats["games"] * 100) if stats["games"] > 0 else 0
        logger.info(
            f"   {bot_name}: "
            f"{stats['wins']}W/{stats['losses']}L/{stats['draws']}D | "
            f"WR: {win_rate:.1f}% | "
            f"Очки: {stats['total_score']} | "
            f"Игр: {stats['games']}"
        )

    logger.info("=" * 60)


def log_tournament_game(
    tournament_id: int,
    game_num: int,
    bot1_name: str,
    bot2_name: str,
    bot1_score: int,
    bot2_score: int,
    winner: int,
    turns: int,
):
    from datetime import datetime

    winner_name = bot1_name if winner == 0 else (bot2_name if winner == 1 else "Ничья")
    timestamp = datetime.now().strftime("%H:%M:%S")

    logger.info(
        f"🎮 [t{tournament_id}] Игра {game_num}: "
        f"{bot1_name}({bot1_score}) vs {bot2_name}({bot2_score}) | "
        f"Победитель: {winner_name} | "
        f"Ходов: {turns} | {timestamp}"
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


def log_container_start(container_id: str, port: str, bot_code: str = None):
    logger.info(
        f"🐳 Контейнер запущен | container_id={container_id} | port={port} | код={'получен' if bot_code else 'не получен'}"
    )


def log_container_stop(container_id: str, reason: str = "завершение"):
    logger.info(
        f"🛑 Остановка контейнера бота | container_id={container_id} | причина={reason}"
    )


def log_container_error(container_id: str, error: str):
    logger.error(
        f"❌ Ошибка контейнера бота | container_id={container_id} | error={error}"
    )


def log_redis_connected(redis_url: str):
    logger.info(f"🔴 Redis подключён | url={redis_url}")


def log_redis_error(operation: str, error: str):
    logger.error(f"🔴 Redis ошибка | operation={operation} | error={error}")


def log_redis_operation(operation: str, game_id: str, details: str = ""):
    logger.debug(f"🔴 Redis | op={operation} | game_id={game_id} {details}")
